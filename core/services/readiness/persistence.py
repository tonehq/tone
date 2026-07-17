"""Persist readiness reports to Postgres.

One narrow class with one public method — writes ARE this module's sole
responsibility (SRP). Kept out of ``ReadinessService`` so the service stays
focused on orchestration.

Two rows written per call, in one transaction:
- UPSERT the ``agent_readiness_snapshots`` row for ``(agent, config, depth)``
- INSERT a fresh ``agent_readiness_events`` row (append-only history)

If either write fails, the whole persistence step is rolled back and the
caller receives no exception — the primary readiness flow must never break
because storage misbehaved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from core.models.agent_readiness_event import AgentReadinessEvent
from core.models.agent_readiness_snapshot import AgentReadinessSnapshot
from core.services.readiness.schemas import ReadinessReport


class ReadinessPersistence:
    """Writes readiness reports to snapshot + event tables."""

    def __init__(self, db: Session, org_id: UUID):
        self.db = db
        self.org_id = org_id

    def record(
        self,
        report: ReadinessReport,
        *,
        trigger: str,
        triggered_by_user_id: Optional[UUID],
        dependency_stamp: str,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Persist ``report`` to both tables. Swallows failures with a warning
        log — never raises to the caller."""
        try:
            self._write(
                report=report,
                trigger=trigger,
                triggered_by_user_id=triggered_by_user_id,
                dependency_stamp=dependency_stamp,
                duration_ms=duration_ms,
                error=error,
            )
        except Exception:  # noqa: BLE001
            # Storage is best-effort. Rollback our writes so any wider
            # transaction (e.g. the request-scoped session) stays clean.
            logger.exception("[readiness] persistence failed")
            try:
                self.db.rollback()
            except Exception:  # noqa: BLE001
                logger.exception("[readiness] rollback after failed persist also failed")

    # ── internals ──────────────────────────────────────────────────────────

    def _write(
        self,
        *,
        report: ReadinessReport,
        trigger: str,
        triggered_by_user_id: Optional[UUID],
        dependency_stamp: str,
        duration_ms: Optional[int],
        error: Optional[str],
    ) -> None:
        row = self._row_from_report(
            report=report,
            trigger=trigger,
            triggered_by_user_id=triggered_by_user_id,
            dependency_stamp=dependency_stamp,
            duration_ms=duration_ms,
            error=error,
        )

        # UPSERT the snapshot on (agent_id, config_id, depth). Every field
        # from the fresh run overwrites the stored one — a snapshot only
        # ever describes the latest state.
        stmt = pg_insert(AgentReadinessSnapshot).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["agent_id", "config_id", "depth"],
            set_={
                k: getattr(stmt.excluded, k)
                for k in row
                # Preserve the row's PK + created_at across upserts; every
                # other column is refreshed from the incoming report.
                if k not in ("id", "created_at", "organization_id",
                             "agent_id", "config_id", "depth")
            },
        )
        self.db.execute(stmt)

        # Always append a fresh event row — history is append-only.
        event = AgentReadinessEvent(**row)
        self.db.add(event)

        self.db.commit()

    def _row_from_report(
        self,
        *,
        report: ReadinessReport,
        trigger: str,
        triggered_by_user_id: Optional[UUID],
        dependency_stamp: str,
        duration_ms: Optional[int],
        error: Optional[str],
    ) -> Dict[str, Any]:
        """Flatten a ``ReadinessReport`` into a dict of row values, ready for
        both the UPSERT and the INSERT. Kept as pure data so tests can assert
        on the shape without touching the DB."""
        # `summary` from the API layer already carries the exact key set the
        # `counts` column stores — pass it through verbatim so this stays a
        # single source of truth. Defensive dict() copy so a caller that
        # mutates `report.summary` later can't retroactively corrupt the row.
        return {
            "organization_id": self.org_id,
            "agent_id": _as_uuid(report.agent_id),
            "config_id": _as_uuid(report.config_id) if report.config_id else None,
            "depth": report.depth.value,
            "overall_status": report.overall_status.value,
            "counts": dict(report.summary or {}),
            "checks": [c.model_dump(mode="json") for c in report.checks],
            "trigger": trigger,
            "triggered_by_user_id": triggered_by_user_id,
            "duration_ms": duration_ms,
            "computed_at": _parse_iso(report.generated_at),
            "dependency_stamp": dependency_stamp,
            "error": error,
        }


# ── module-private helpers ─────────────────────────────────────────────────


def _as_uuid(value: Optional[Any]) -> Optional[UUID]:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _parse_iso(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
