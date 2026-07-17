"""Read one finished call's log lines back from Loki into ``call_pipeline_logs``.

The service behind both the ``sync_loki_logs`` post-call action and the manual
``POST /call-log/{call_id}/sync-logs`` endpoint. Scoped to a single call, so the
time window is bounded and known up front. All of the call's lines are stored as
a single ``logs`` JSON array on ONE row keyed by ``call_id``; every re-run
re-reads the same bounded window, rebuilds the same de-duplicated, time-ordered
array and upserts it (``on_conflict(call_id) do update``), so the post-call
action, a manual re-sync, task retries and concurrent runs all converge on one
row with the same contents.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.models.call import Call
from core.models.log_entry import CallPipelineLog
from core.services.base import BaseService
from core.services.loki_client import LokiClient
from core.services.log_parser import extract_trace_id, fingerprint, parse_line
from shared.config import settings


@dataclass
class SyncResult:
    """Outcome of a per-call sync — returned by the endpoint and logged by the job."""

    fetched: int = 0          # total lines returned by Loki (incl. page overlap)
    stored: int = 0           # unique lines in the stored array after this run
    pages: int = 0
    truncated: bool = False   # hit MAX_PAGES with more lines likely remaining
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    configured: bool = True
    message: str = ""


class PipelineLogSyncService(BaseService):
    def sync_call_by_id(self, call_id: uuid.UUID) -> Optional[SyncResult]:
        """Load the org-scoped call and sync it. Returns None when the call isn't
        in the caller's org (endpoint maps that to 404 — no cross-org IDOR)."""
        call = self.query(Call).filter(Call.id == call_id).first()
        if call is None:
            return None
        return self.sync_call(call)

    def list_for_call(
        self,
        call_id: uuid.UUID,
        *,
        limit: int = 1000,
        offset: int = 0,
        level: Optional[str] = None,
    ) -> dict:
        """Return stored log lines for a call, oldest first, for the viewer.

        Reads the single ``call_pipeline_logs`` row and slices its ``logs`` array.
        Org-scoped via ``BaseService.query`` so a cross-org ``call_id`` returns an
        empty page rather than leaking another tenant's logs."""
        row = self.query(CallPipelineLog).filter(CallPipelineLog.call_id == call_id).first()
        entries: List[dict] = list(row.logs) if row and row.logs else []
        if level:
            lvl = level.upper()
            entries = [e for e in entries if (e.get("level") or "").upper() == lvl]
        total = len(entries)
        lo = max(offset, 0)
        hi = lo + max(min(limit, 5000), 1)
        return {
            "call_id": str(call_id),
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [_entry_payload(e) for e in entries[lo:hi]],
        }

    def sync_call(self, call: Call) -> SyncResult:
        """Fetch ``call``'s Loki lines within its (buffered) time window and store them
        as a single time-ordered array on one row.

        Safe no-op (returns zeros, never raises) when Loki read creds are absent
        or the call never got a ``trace_id``. Loki transport errors DO propagate
        as :class:`LokiError` so the worker can retry and the endpoint can report."""
        if not settings.loki_read_configured():
            logger.debug("[loki_sync] call={} skipped — Loki read not configured", call.id)
            return SyncResult(configured=False, message="Loki read not configured")

        if not call.trace_id:
            logger.debug("[loki_sync] call={} skipped — no trace_id", call.id)
            return SyncResult(message="Call has no trace_id; nothing to sync")

        window = self._window(call)
        if window is None:
            logger.debug("[loki_sync] call={} skipped — no time anchor", call.id)
            return SyncResult(message="Call has no time anchor; nothing to sync")
        start_dt, end_dt = window
        start_ns, end_ns = _to_ns(start_dt), _to_ns(end_dt)

        # trace_id is "{short_uuid}-{agent_id}-{call_id}". The short-uuid prefix is
        # present on EVERY line (including early ones logged before the agent/call
        # id are known), so it's the fetch key — filtering on the full trace_id
        # would drop those setup lines. The prefix is only 8 hex chars, so a
        # different call can share it; _entries_for_page disambiguates client-side
        # by the fully-rendered trace_id before storing, so foreign lines aren't
        # misattributed to this call.
        call_uuid = call.trace_id.split("-", 1)[0]
        selector = (
            f'{{app="{settings.LOKI_SYNC_APP_LABEL}"}}'
            if settings.LOKI_SYNC_APP_LABEL
            else '{component=~"call|api"}'
        )
        query = f'{selector} |= "trace_id={call_uuid}"'

        client = LokiClient()
        result = SyncResult(window_start=start_dt, window_end=end_dt)
        seen_fingerprints: set[str] = set()
        entries: List[dict] = []
        cursor = start_ns

        for page in range(settings.LOKI_SYNC_MAX_PAGES):
            lines = client.query_range(
                query, cursor, end_ns, limit=settings.LOKI_SYNC_PAGE_LIMIT, direction="forward"
            )
            result.pages = page + 1
            if not lines:
                break
            result.fetched += len(lines)

            page_entries, max_ts = self._entries_for_page(call, lines, seen_fingerprints)
            entries.extend(page_entries)

            # Last (partial) page → done.
            if len(lines) < settings.LOKI_SYNC_PAGE_LIMIT:
                break
            # Full page but the cursor can't advance (every line shares one ns):
            # can't paginate further without risking a loop.
            if max_ts <= cursor:
                result.truncated = True
                break
            # Overlap the boundary ns; the seen-set dedups the repeat.
            cursor = max_ts
        else:
            # Exhausted MAX_PAGES with full pages throughout — more may remain.
            result.truncated = True

        # Oldest first — pages come forward-ordered but sort defensively so a
        # boundary overlap or out-of-order stream can't scramble the viewer.
        entries.sort(key=lambda e: e["ts_ns"])
        result.stored = self._upsert_call(call, entries)

        logger.info(
            "[loki_sync] call={} window=[{} → {}] pages={} fetched={} stored={} truncated={}",
            call.id, start_dt.isoformat(), end_dt.isoformat(),
            result.pages, result.fetched, result.stored, result.truncated,
        )
        return result

    # ── internals ──────────────────────────────────────────────────────────

    def _window(self, call: Call) -> Optional[tuple[datetime, datetime]]:
        """Buffered [start, end] for the call, or None if there's no anchor.

        Falls back to ``created_at`` when ``started_at`` is missing (aborted call)
        and to ``now`` when ``ended_at`` is missing (still-open/failed call), and
        clamps the end to ``now`` to absorb future timestamps / clock skew."""
        now = datetime.now(timezone.utc)
        start_anchor = call.started_at or call.created_at
        if start_anchor is None:
            return None
        end_anchor = call.ended_at or now
        start_dt = start_anchor - timedelta(seconds=settings.LOKI_SYNC_PRE_BUFFER_SECONDS)
        end_dt = min(end_anchor, now) + timedelta(seconds=settings.LOKI_SYNC_POST_BUFFER_SECONDS)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(seconds=settings.LOKI_SYNC_POST_BUFFER_SECONDS)
        return start_dt, end_dt

    def _entries_for_page(self, call: Call, lines, seen: set) -> tuple[List[dict], int]:
        """Build JSON-safe log entries for a page, deduping within-run by fingerprint.

        Returns the entries plus the max ts_ns seen (the pagination cursor). Each
        entry is ``{ts, ts_ns, level, logger_name, message, raw_line}`` — identity
        (call/org/agent/trace) is not repeated per line; it lives on the row."""
        entries: List[dict] = []
        max_ts = 0
        for ln in lines:
            # max_ts advances over every fetched line (incl. dropped foreign ones)
            # so pagination still makes progress.
            if ln.ts_ns > max_ts:
                max_ts = ln.ts_ns
            # The prefix filter can match a different call that shares our 8-char
            # short-uuid prefix; drop those instead of attributing them to this
            # call. Lines with no parseable token are kept (never dropped).
            if not _trace_belongs(extract_trace_id(ln.line), call.trace_id):
                continue
            fp = fingerprint(ln.ts_ns, ln.labels, ln.line)
            if fp in seen:
                continue
            seen.add(fp)
            parsed = parse_line(ln.line)
            entries.append(
                {
                    "ts": _from_ns(ln.ts_ns).isoformat(),
                    "ts_ns": ln.ts_ns,
                    "level": parsed["level"],
                    "logger_name": parsed["logger_name"],
                    "message": parsed["message"],
                    "raw_line": ln.line,
                }
            )
        return entries, max_ts

    def _upsert_call(self, call: Call, entries: List[dict]) -> int:
        """Replace the call's stored log array in one idempotent upsert.

        One row per call (``call_id`` UNIQUE): insert it or overwrite ``logs``
        wholesale. Because ``entries`` is the full, deduped window every run, a
        re-sync / retry / concurrent run converges on the same array — last write
        wins with an equivalent value. Returns the stored line count."""
        now = datetime.now(timezone.utc)
        values = {
            "id": uuid.uuid4(),
            "organization_id": call.organization_id,
            "call_id": call.id,
            "agent_id": call.agent_id,
            "trace_id": call.trace_id,
            "logs": entries,
            "synced_at": now,
        }
        stmt = pg_insert(CallPipelineLog).values(**values).on_conflict_do_update(
            index_elements=["call_id"],
            set_={
                "logs": entries,
                "agent_id": call.agent_id,
                "trace_id": call.trace_id,
                "synced_at": now,
                "updated_at": now,
            },
        )
        self.db.execute(stmt)
        self.db.commit()
        return len(entries)


def _trace_belongs(token: Optional[str], full_trace_id: str) -> bool:
    """Does a line whose rendered trace token is ``token`` belong to this call?

    The trace_id renders progressively ("{cu}" → "{cu}-{agent}" →
    "{cu}-{agent}-{call}"), so a line of this call carries a *prefix* of the
    final trace_id, or the full value. A different call sharing our short-uuid
    prefix diverges at the agent_id segment, so it satisfies neither direction
    and is rejected. A ``None`` token (unparseable / continuation line) is kept —
    we never drop a line we can't disambiguate. Residual: a foreign call's
    earliest pre-agent lines (token == the bare short-uuid) still match; that's
    unavoidable without a longer prefix and is vanishingly rare."""
    if not token:
        return True
    return full_trace_id.startswith(token) or token.startswith(full_trace_id)


def _to_ns(dt: datetime) -> int:
    return int(dt.timestamp() * 1_000_000_000)


def _from_ns(ts_ns: int) -> datetime:
    return datetime.fromtimestamp(ts_ns / 1_000_000_000, tz=timezone.utc)


def sync_result_payload(result: SyncResult) -> dict:
    """JSON-safe payload for the manual sync endpoint."""
    return {
        "fetched": result.fetched,
        "stored": result.stored,
        "pages": result.pages,
        "truncated": result.truncated,
        "configured": result.configured,
        "window_start": result.window_start.isoformat() if result.window_start else None,
        "window_end": result.window_end.isoformat() if result.window_end else None,
        "message": result.message,
    }


def _entry_payload(entry: dict) -> dict:
    """Viewer-facing shape for one stored log entry."""
    return {
        "ts": entry.get("ts"),
        "level": entry.get("level"),
        "logger_name": entry.get("logger_name"),
        "message": entry.get("message"),
        "raw_line": entry.get("raw_line"),
    }
