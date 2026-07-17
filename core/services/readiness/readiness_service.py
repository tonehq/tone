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
from typing import List, Optional, Set
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger

from sqlalchemy import func, select

from core.models.agent import Agent
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
    ReadinessSummary,
)


# Process-wide singletons — see docstring above.
_deep_cache = DeepCheckCache(ttl_seconds=300)
_rate_limiter = RateLimiter(max_per_window=1, window_seconds=60)


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
        """
        agent = self._require_agent(agent_id)
        stamp, resolved_config = self._compute_stamp(agent)
        effective_config_id = self._effective_config_id(config_id, resolved_config)

        # Targeted deep bypasses all caches + persistence — see docstring.
        if depth == Depth.DEEP and deep_categories is not None:
            return await self._run(
                agent, config_id, Depth.DEEP, deep_categories=deep_categories
            )

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
        currently-live stamp. Missing stamp (either side) always misses."""
        if not stamp:
            return None
        q = (
            self.db.query(AgentReadinessSnapshot)
            .filter(
                AgentReadinessSnapshot.organization_id == self.org_id,
                AgentReadinessSnapshot.agent_id == agent_id,
                AgentReadinessSnapshot.depth == depth.value,
                AgentReadinessSnapshot.dependency_stamp == stamp,
            )
        )
        # SQLAlchemy translates ``== None`` to ``IS NULL`` — needed so a
        # brand-new-agent snapshot (config_id NULL) can still fast-path.
        if config_id is None:
            q = q.filter(AgentReadinessSnapshot.config_id.is_(None))
        else:
            q = q.filter(AgentReadinessSnapshot.config_id == config_id)
        row = q.first()
        if row is None:
            return None
        return _snapshot_to_report(row)

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
        captured for the ``duration_ms`` column."""
        started = time.monotonic()
        report = await self._run(agent, config_id, depth)
        duration_ms = int((time.monotonic() - started) * 1000)

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
            )
        return report

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


def _snapshot_to_report(row: AgentReadinessSnapshot) -> ReadinessReport:
    """Turn a stored snapshot row back into a ``ReadinessReport``. Both JSONB
    columns (``counts`` and ``checks``) already carry the exact wire shape so
    there's no field-by-field mapping — just hand them to the Pydantic
    models. Any missing count key falls back to 0 so an older snapshot
    predating a new severity level still renders."""
    checks: List[CheckResult] = [
        CheckResult.model_validate(c) for c in (row.checks or [])
    ]
    stored_counts = row.counts or {}
    return ReadinessReport(
        agent_id=str(row.agent_id),
        config_id=str(row.config_id) if row.config_id else None,
        depth=Depth(row.depth),
        overall_status=OverallStatus(row.overall_status),
        summary={
            "blockers": int(stored_counts.get("blockers", 0)),
            "warnings": int(stored_counts.get("warnings", 0)),
            "info": int(stored_counts.get("info", 0)),
            "passed": int(stored_counts.get("passed", 0)),
            "skipped": int(stored_counts.get("skipped", 0)),
        },
        checks=checks,
        generated_at=row.computed_at.isoformat() if row.computed_at else "",
    )
