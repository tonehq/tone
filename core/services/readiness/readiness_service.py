"""ReadinessService — the single class routers depend on.

Composes the pieces of the readiness domain:

- ``ContextBuilder``       — assembles a ``CheckContext`` from the DB
- ``Runner``               — executes applicable checks and aggregates
- ``DeepCheckCache``       — reuses recent Deep results & coalesces concurrent runs
- ``RateLimiter``          — caps Deep runs at 1/minute per (org, agent)
- ``ReadinessPersistence`` — writes snapshots + events to Postgres

The cache and rate limiter are module-level singletons because they hold
process-wide state; everything else is instantiated per request.

Read path also has an **edit-based fast-path**: we compute the pipeline's
existing ``dependency_stamp`` and, if a stored snapshot has the same stamp,
return it directly — never re-running the runner when nothing has changed.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Union
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger

from sqlalchemy import func, select

from core.models.agent import Agent
from core.models.agent_readiness_event import AgentReadinessEvent
from core.models.agent_readiness_snapshot import AgentReadinessSnapshot
from core.models.phone_number import PhoneNumber
from core.services.base import BaseService
from core.services.pipeline.service_resolver import (
    compute_agent_cache_version,
    get_active_agent_config,
)
from core.services.readiness.cache import DeepCheckCache
from core.services.readiness.context import ContextBuilder
from core.services.readiness.persistence import ReadinessPersistence
from core.services.readiness.rate_limiter import RateLimiter
from core.services.readiness.runner import Runner
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    Depth,
    OverallStatus,
    ReadinessReport,
    ReadinessRunList,
    ReadinessRunListItem,
    ReadinessSummary,
)


# Process-wide singletons — see docstring above.
_deep_cache = DeepCheckCache(ttl_seconds=300)
_rate_limiter = RateLimiter(max_per_window=1, window_seconds=60)

# Wall-clock TTL for the persisted Deep-snapshot fast-path.
#
# The ``dependency_stamp`` invalidates a stored snapshot on every DB edit
# tracked by ``compute_agent_cache_version``, but it has no way to notice
# *out-of-band* drift — an OAuth token silently expiring, a provider
# revoking an API key, a telephony account running out of credit. Without
# a time cap, the last passing Deep snapshot can be replayed for weeks
# while the agent is actually broken.
#
# 300s matches the in-memory ``DeepCheckCache`` TTL above so both cache
# layers share a single freshness window: within 5 minutes of any external
# drift the runner re-executes live, bringing the failure into the report.
_DEEP_SNAPSHOT_TTL_SECONDS = 300


# Canonical trigger strings. Free-form so callers can pass anything, but
# keeping the set here documents intent and makes analytics comparable.
TRIGGER_API = "api"
TRIGGER_PUBLISH_GATE = "publish_gate"


class ReadinessService(BaseService):
    """Public facade over the readiness subsystem."""

    async def check(
        self,
        agent_id: str,
        depth: Depth = Depth.SHALLOW,
        config_id: Optional[str] = None,
        *,
        trigger: str = TRIGGER_API,
        deep_categories: Optional[Set[Category]] = None,
        force: bool = False,
    ) -> ReadinessReport:
        """Run a readiness check for one agent + (optionally explicit) config.

        Order of operations:
        1. Load the agent + compute the dependency stamp (single-round-trip).
        2. If a stored snapshot exists with a matching stamp → return it.
        3. Shallow: run + persist + return.
        4. Deep: rate-limit, coalesce, cache-in-memory, run + persist + return.

        ``deep_categories`` is only meaningful when ``depth=DEEP`` and switches
        the runner to a **targeted deep** — only the listed categories are
        actually probed live; other deep checks return SKIPPED. Targeted deep
        deliberately bypasses the snapshot fast-path AND the persistence write
        so a partial-scan result never masquerades as a full deep for the
        publish gate. It also skips the rate limiter / coalesce cache because
        each targeted run has a different "shape" — those safeguards protect
        full-deep runs, not user-driven save-time probes.

        ``force`` is for an **explicit, user-initiated run** (the "Run deep
        test" button). It skips the read-through snapshot fast-path AND the
        in-memory coalesce cache so the run actually executes and appends a
        fresh ``agent_readiness_events`` row — otherwise a repeat deep test on
        an unchanged agent returns the stored snapshot and the run-history list
        never grows. The rate limiter still applies (1/min).
        """
        agent = self._require_agent(agent_id)
        stamp, resolved_config = self._compute_stamp(agent)
        effective_config_id = self._effective_config_id(config_id, resolved_config)

        # Targeted deep bypasses all caches + persistence — see docstring.
        if depth == Depth.DEEP and deep_categories is not None:
            return await self._run(
                agent, config_id, Depth.DEEP, deep_categories=deep_categories
            )

        # A forced run skips the read-through fast-path so it always executes
        # and records a new event (see docstring).
        if not force:
            fresh = self._read_fresh_snapshot(agent.id, effective_config_id, depth, stamp)
            if fresh is not None:
                return fresh

        if depth == Depth.SHALLOW:
            return await self._run_and_persist(
                agent=agent,
                config_id=config_id,
                depth=Depth.SHALLOW,
                trigger=trigger,
                dependency_stamp=stamp,
            )

        # Deep path: rate-limit + in-memory coalesce (a second belt over
        # the DB fast-path for the "click Test agent twice fast" case).
        cache_key = DeepCheckCache.key(self.org_id, agent.id, effective_config_id)

        async def _compute() -> ReadinessReport:
            allowed = await _rate_limiter.try_acquire(
                RateLimiter.key(self.org_id, agent.id)
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Deep readiness check rate-limited. "
                        "Please wait a minute and try again."
                    ),
                )
            return await self._run_and_persist(
                agent=agent,
                config_id=config_id,
                depth=Depth.DEEP,
                trigger=trigger,
                dependency_stamp=stamp,
            )

        # A forced deep run bypasses the in-memory coalesce cache too, so it
        # truly re-probes and appends a new event instead of returning a report
        # cached from a run in the last 300s. Still rate-limited via _compute.
        if force:
            return await _compute()
        return await _deep_cache.get_or_compute(cache_key, _compute)

    async def summary(
        self,
        agent_id: str,
        config_id: Optional[str] = None,
        *,
        trigger: str = TRIGGER_API,
    ) -> ReadinessSummary:
        """Small badge shape (Shallow only) — for the agent list page."""
        report = await self.check(
            agent_id, Depth.SHALLOW, config_id, trigger=trigger
        )
        return report.to_summary()

    def latest_for_agents(self, agent_ids: List[UUID]) -> Dict[UUID, Dict]:
        """Batch-fetch the latest readiness snapshot per agent for the list badge.

        Read-only: returns the most recently computed stored snapshot (any
        config / depth) verbatim — no recompute, no dependency-stamp
        re-validation. Powers the agent-list badge in a single query instead of
        one live readiness call per row (the old N+1); the editor drawer still
        recomputes accurately when opened. An agent with no stored run yet is
        simply absent from the map (badge renders "unavailable").

        Org-scoped by ``self.org_id``. Projects only the badge columns (skips the
        heavy ``checks`` blob) and reuses ``_counts_from_mapping`` so the count
        fallback set stays single-sourced with the row mappers.

        Returns ``{agent_id: {overall_status, blocker_count, warning_count,
        info_count, run_number, computed_at}}``.
        """
        if not agent_ids:
            return {}
        rows = (
            self.db.query(
                AgentReadinessSnapshot.agent_id,
                AgentReadinessSnapshot.overall_status,
                AgentReadinessSnapshot.counts,
                AgentReadinessSnapshot.run_number,
                AgentReadinessSnapshot.computed_at,
            )
            .filter(
                AgentReadinessSnapshot.organization_id == self.org_id,
                AgentReadinessSnapshot.agent_id.in_(agent_ids),
            )
            .order_by(AgentReadinessSnapshot.computed_at.desc())
            .all()
        )
        latest: Dict[UUID, Dict] = {}
        for agent_id, overall_status, counts, run_number, computed_at in rows:
            # Rows arrive newest-first; keep only the first (latest) per agent.
            if agent_id in latest:
                continue
            tallies = _counts_from_mapping(counts)
            latest[agent_id] = {
                "overall_status": overall_status,
                "blocker_count": tallies["blockers"],
                "warning_count": tallies["warnings"],
                "info_count": tallies["info"],
                "run_number": run_number,
                "computed_at": computed_at.isoformat() if computed_at else None,
            }
        return latest

    # Cap the history scan so a pathological agent can't force a huge read.
    _MAX_RUNS_LIMIT = 100

    def list_runs(self, agent_id: str, *, limit: int = 20) -> ReadinessRunList:
        """List past **deep** readiness runs for one agent, newest first.

        Only deep runs (Test agent + publish gate) are surfaced — background
        shallow snapshots (editor loads, list-page impressions) are noise the
        user never asked to run and would swamp the dropdown. History spans all
        configs/versions of the agent; the UI badges cross-version rows.

        Metadata only — the heavy ``checks`` list is fetched per-run via
        ``get_run``. Org-scoped via ``_require_agent`` (404 for other orgs).
        """
        agent = self._require_agent(agent_id)
        capped = max(1, min(limit, self._MAX_RUNS_LIMIT))
        rows = (
            self.db.query(AgentReadinessEvent)
            .filter(
                AgentReadinessEvent.organization_id == self.org_id,
                AgentReadinessEvent.agent_id == agent.id,
                AgentReadinessEvent.depth == Depth.DEEP.value,
            )
            .order_by(AgentReadinessEvent.run_number.desc())
            .limit(capped)
            .all()
        )
        items: List[ReadinessRunListItem] = []
        for row in rows:
            try:
                items.append(_event_to_list_item(row))
            except (ValueError, KeyError):
                # One legacy/partial row with an out-of-enum status/counts must
                # not 500 the whole history list — skip it (with a traceback).
                logger.exception(
                    "[readiness] skipping unmappable run event run_number={}",
                    getattr(row, "run_number", None),
                )
        return ReadinessRunList(items=items)

    def get_run(self, agent_id: str, run_number: int) -> ReadinessReport:
        """Return the full stored report for one past run.

        Reuses ``_row_to_report`` — an event row carries the same
        ``ReadinessRowMixin`` columns as a snapshot, so the mapping is
        identical. Org-scoped; raises 404 for an unknown agent or run.
        """
        agent = self._require_agent(agent_id)
        row = (
            self.db.query(AgentReadinessEvent)
            .filter(
                AgentReadinessEvent.organization_id == self.org_id,
                AgentReadinessEvent.agent_id == agent.id,
                # Deep-only, mirroring ``list_runs`` — a shallow run_number that
                # never appears in the dropdown must 404, not return a report.
                AgentReadinessEvent.depth == Depth.DEEP.value,
                AgentReadinessEvent.run_number == run_number,
            )
            # Defensive: run_number is monotonic + concurrency-guarded so it's
            # effectively unique per agent, but there's no DB uniqueness
            # constraint — take the most recent row if two ever collide.
            .order_by(AgentReadinessEvent.computed_at.desc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Readiness run not found")
        try:
            return _row_to_report(row)
        except (ValueError, KeyError):
            # A stored row with an out-of-enum value can't be rendered — treat it
            # as unavailable rather than 500-ing (mirrors list_runs' skip). Log
            # the traceback so the corrupt row stays diagnosable.
            logger.exception(
                "[readiness] run {} unmappable for agent {}", run_number, agent_id
            )
            raise HTTPException(status_code=404, detail="Readiness run not found")

    async def gate_publish(
        self,
        agent_id: str,
        config_id: str,
        *,
        force_warnings: bool = False,
    ) -> None:
        """Publish gate: raise if the target config isn't safe to promote.

        Runs Deep (structural + live probes). BLOCKERs hard-fail; if only
        WARNINGs are present the caller must explicitly opt in with
        ``force_warnings=True``. Invalidates the in-memory Deep cache on
        success so the next readiness read reflects the freshly-published
        state (edit-based DB fast-path is naturally invalidated by the
        publish-time stamp change).
        """
        report = await self.check(
            agent_id,
            Depth.DEEP,
            config_id,
            trigger=TRIGGER_PUBLISH_GATE,
        )

        if report.overall_status == OverallStatus.NOT_READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "reason": "readiness_blocked",
                    "message": (
                        f"{report.summary.get('blockers', 0)} blocker(s) prevent "
                        "publishing this version."
                    ),
                    "report": report.model_dump(),
                },
            )
        if (
            report.overall_status == OverallStatus.READY_WITH_WARNINGS
            and not force_warnings
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "reason": "readiness_warnings",
                    "message": (
                        f"{report.summary.get('warnings', 0)} warning(s) present. "
                        "Re-submit with force_warnings=true to publish anyway."
                    ),
                    "report": report.model_dump(),
                },
            )

        _deep_cache.invalidate(
            DeepCheckCache.key(self.org_id, agent_id, config_id)
        )

    # ── internals ──────────────────────────────────────────────────────────

    def _require_agent(self, agent_id: str) -> Agent:
        """Fetch an org-scoped agent or raise 404. Excludes soft-deleted rows."""
        try:
            aid = UUID(str(agent_id))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid agent id")
        agent = (
            self.db.query(Agent)
            .filter(
                Agent.id == aid,
                Agent.organization_id == self.org_id,
                Agent.deleted_at.is_(None),
            )
            .first()
        )
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    def _compute_stamp(self, agent: Agent):
        """Build the freshness key used by the snapshot fast-path.

        Combines the pipeline resolver's ``compute_agent_cache_version`` (which
        covers config + all provider/model/key/tool/KB/MCP/workflow deps) with
        readiness-only inputs the pipeline stamp ignores — currently just phone
        assignments, which live on the agent row rather than on any config.

        The pipeline helper is left untouched so runtime call caching stays
        unaffected; only readiness sees the augmented stamp. Never raises —
        any failure returns a ``None`` stamp so the fast-path misses cleanly
        and we recompute.
        """
        try:
            base_stamp, config = compute_agent_cache_version(
                self.db, agent, org_id=self.org_id
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "[readiness] dependency stamp computation failed for agent {}",
                agent.id,
            )
            return None, get_active_agent_config(self.db, agent)

        # A None base means the pipeline helper couldn't produce a stamp (agent
        # with no config); the fast-path must then miss — don't fabricate a
        # partial stamp that could accidentally match a stored one.
        if base_stamp is None:
            return None, config

        phone_stamp = self._phone_stamp(agent.id)
        return f"{base_stamp}|{phone_stamp}", config

    def _phone_stamp(self, agent_id: UUID) -> str:
        """Fingerprint the agent's phone assignments for the freshness key.

        Cheap single scalar-select — one round trip, no ORM materialisation.
        Format mirrors the other segments in ``compute_agent_cache_version``:
        ``phones:<count>:<max_updated_at_iso>`` (or ``:none`` when empty).
        """
        try:
            row = self.db.execute(
                select(
                    func.count(PhoneNumber.id),
                    func.max(PhoneNumber.updated_at),
                ).where(
                    PhoneNumber.agent_id == agent_id,
                    PhoneNumber.organization_id == self.org_id,
                )
            ).one()
            count, max_ts = row
            ts = max_ts.isoformat() if max_ts is not None else "none"
            return f"phones:{count or 0}:{ts}"
        except Exception:  # noqa: BLE001
            logger.exception(
                "[readiness] phone stamp computation failed for agent {}",
                agent_id,
            )
            # Deterministic sentinel — different from any real stamp so the
            # fast-path misses when we can't confidently reproduce state.
            return "phones:error"

    @staticmethod
    def _effective_config_id(
        requested_config_id: Optional[str], resolved_config
    ) -> Optional[UUID]:
        """The config id we actually check against: caller-supplied wins, else
        we resolve the active config (published or default)."""
        if requested_config_id:
            try:
                return UUID(str(requested_config_id))
            except (ValueError, TypeError):
                return None
        return resolved_config.id if resolved_config is not None else None

    def _read_fresh_snapshot(
        self,
        agent_id: UUID,
        config_id: Optional[UUID],
        depth: Depth,
        stamp: Optional[str],
    ) -> Optional[ReadinessReport]:
        """Return a stored snapshot iff its ``dependency_stamp`` matches the
        currently-live stamp. Missing stamp (either side) always misses.

        A **SHALLOW** request also accepts a **DEEP** snapshot: a deep run is a
        superset of shallow (all shallow checks + live provider probes), so for
        an unchanged config the most RECENT run governs the badge regardless of
        depth. Without this, reloading the page fires a shallow summary read
        that returns the stale shallow snapshot and resets the badge to "ready",
        discarding a "Run deep test" result (e.g. a live-probe blocker) the user
        just saw. A **DEEP** request (publish gate) still requires an actual deep
        snapshot. When both depths match the stamp, the newest by ``computed_at``
        wins — so a later shallow "Refresh" correctly supersedes an earlier deep
        run, and vice-versa."""
        if not stamp:
            return None
        q = self.db.query(AgentReadinessSnapshot).filter(
            AgentReadinessSnapshot.organization_id == self.org_id,
            AgentReadinessSnapshot.agent_id == agent_id,
            AgentReadinessSnapshot.dependency_stamp == stamp,
        )
        # Deep reads must not be satisfied by a shallow snapshot; shallow reads
        # accept either depth (see docstring).
        if depth == Depth.DEEP:
            q = q.filter(AgentReadinessSnapshot.depth == Depth.DEEP.value)
        # SQLAlchemy translates ``== None`` to ``IS NULL`` — needed so a
        # brand-new-agent snapshot (config_id NULL) can still fast-path.
        if config_id is None:
            q = q.filter(AgentReadinessSnapshot.config_id.is_(None))
        else:
            q = q.filter(AgentReadinessSnapshot.config_id == config_id)
        row = q.order_by(AgentReadinessSnapshot.computed_at.desc()).first()
        if row is None:
            return None
        if depth == Depth.DEEP and _deep_snapshot_expired(row):
            return None
        return _row_to_report(row)

    async def _run_and_persist(
        self,
        *,
        agent: Agent,
        config_id: Optional[str],
        depth: Depth,
        trigger: str,
        dependency_stamp: Optional[str],
    ) -> ReadinessReport:
        """Compute a fresh report, persist it, and return it. Timing is
        captured for the ``duration_ms`` column, and ``started_at`` /
        ``run_number`` are stamped at persist time so both snapshot and event
        rows carry identical provenance."""
        started_wall = datetime.now(timezone.utc)
        started = time.monotonic()
        report = await self._run(agent, config_id, depth)
        duration_ms = int((time.monotonic() - started) * 1000)

        # Stamp provenance on the in-memory report so the API response carries
        # the same fields the stored row will, without a follow-up DB read.
        run_number = self._next_run_number(agent.id)
        report.started_at = started_wall.isoformat()
        report.run_number = run_number

        # Persistence is fire-and-forget from the caller's perspective — a
        # persistence failure logs a warning inside ``.record()`` but never
        # raises. We still guard the stamp being None (fast-path miss reason).
        if dependency_stamp:
            ReadinessPersistence(self.db, self.org_id).record(
                report,
                trigger=trigger,
                triggered_by_user_id=self.user_id,
                dependency_stamp=dependency_stamp,
                duration_ms=duration_ms,
                started_at=started_wall,
                run_number=run_number,
            )
        return report

    def _next_run_number(self, agent_id: UUID) -> int:
        """Return the next run-number for this agent.

        Reads the highest ``run_number`` stored in the append-only event log
        and adds one. Rate limiter + coalesce cache prevent concurrent
        readiness runs for the same agent, so ``MAX + 1`` is race-free in
        practice. Falls back to 1 for the very first run.
        """
        current = self.db.execute(
            select(func.max(AgentReadinessEvent.run_number))
            .where(AgentReadinessEvent.agent_id == agent_id)
        ).scalar()
        return (current or 0) + 1

    async def _run(
        self,
        agent: Agent,
        config_id: Optional[str],
        depth: Depth,
        *,
        deep_categories: Optional[Set[Category]] = None,
    ) -> ReadinessReport:
        builder = ContextBuilder(self.db, self.org_id)
        config = builder.resolve_config(agent, config_id=config_id)
        ctx = builder.build(agent, config, depth)
        return await Runner().run(ctx, deep_categories=deep_categories)


# ── module-private helpers ─────────────────────────────────────────────────


def _deep_snapshot_expired(row: AgentReadinessSnapshot) -> bool:
    """True when a stored Deep snapshot is older than the wall-clock TTL.

    A missing ``computed_at`` is defensively treated as expired — that would
    only happen for hand-inserted rows, and we'd rather re-run than serve a
    snapshot with no provenance.
    """
    if row.computed_at is None:
        return True
    age = datetime.now(timezone.utc) - row.computed_at
    return age > timedelta(seconds=_DEEP_SNAPSHOT_TTL_SECONDS)


def _counts_from_mapping(stored: Optional[Dict]) -> Dict[str, int]:
    """Extract the five severity/status tallies from a raw ``counts`` mapping,
    defaulting any missing key to 0 so a row predating a new count key still
    renders. The single source of truth for the fallback set — used by the row
    mappers (via ``_counts_from_row``) and by the batch list-badge lookup
    (``latest_for_agents``), which projects the ``counts`` column directly."""
    stored = stored or {}
    return {
        "blockers": int(stored.get("blockers", 0)),
        "warnings": int(stored.get("warnings", 0)),
        "info": int(stored.get("info", 0)),
        "passed": int(stored.get("passed", 0)),
        "skipped": int(stored.get("skipped", 0)),
    }


def _counts_from_row(row: Union[AgentReadinessSnapshot, AgentReadinessEvent]) -> Dict[str, int]:
    """Tallies for a full row — delegates to ``_counts_from_mapping``."""
    return _counts_from_mapping(row.counts)


def _row_to_report(row: Union[AgentReadinessSnapshot, AgentReadinessEvent]) -> ReadinessReport:
    """Turn a stored readiness row back into a ``ReadinessReport``.

    Accepts either an ``AgentReadinessSnapshot`` (latest state) or an
    ``AgentReadinessEvent`` (history) — both carry the identical
    ``ReadinessRowMixin`` columns, so one mapper serves both. Both JSONB
    columns (``counts`` and ``checks``) already carry the exact wire shape so
    there's no field-by-field mapping — just hand them to the Pydantic
    models. Any missing count key falls back to 0 so an older row predating a
    new severity level still renders."""
    checks: List[CheckResult] = [
        CheckResult.model_validate(c) for c in (row.checks or [])
    ]
    return ReadinessReport(
        agent_id=str(row.agent_id),
        config_id=str(row.config_id) if row.config_id else None,
        depth=Depth(row.depth),
        overall_status=OverallStatus(row.overall_status),
        summary=_counts_from_row(row),
        checks=checks,
        generated_at=row.computed_at.isoformat() if row.computed_at else "",
        started_at=row.started_at.isoformat() if row.started_at else None,
        run_number=row.run_number,
    )


def _event_to_list_item(row: AgentReadinessEvent) -> ReadinessRunListItem:
    """Flatten a history event row into a lightweight dropdown item.

    Reuses ``_counts_from_row`` for the same defensive tallies as
    ``_row_to_report`` but drops the heavy ``checks`` list — the dropdown only
    needs summary tallies and provenance; full checks load lazily via
    ``get_run``."""
    counts = _counts_from_row(row)
    return ReadinessRunListItem(
        run_number=row.run_number,
        depth=Depth(row.depth),
        overall_status=OverallStatus(row.overall_status),
        config_id=str(row.config_id) if row.config_id else None,
        trigger=row.trigger,
        blocker_count=counts["blockers"],
        warning_count=counts["warnings"],
        info_count=counts["info"],
        passed_count=counts["passed"],
        skipped_count=counts["skipped"],
        started_at=row.started_at.isoformat() if row.started_at else None,
        computed_at=row.computed_at.isoformat() if row.computed_at else "",
        duration_ms=row.duration_ms,
    )
