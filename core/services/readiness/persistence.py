"""Persist readiness reports to Postgres.

One narrow class with one public method — writes ARE this module's sole
responsibility (SRP). Kept out of ``ReadinessService`` so the service stays
focused on orchestration.

One append-only ``agent_readiness_runs`` row is written per call. The table
holds both the latest state (most recent row per agent/config/depth) and the
full history, so there is no separate snapshot to keep in sync.

If the write fails, the persistence step is rolled back and the caller receives
no exception — the primary readiness flow must never break because storage
misbehaved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent_readiness_run import AgentReadinessRun
from core.services.readiness.schemas import ReadinessReport


class ReadinessPersistence:
    """Appends readiness reports to the ``agent_readiness_runs`` table."""

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
        started_at: Optional[datetime] = None,
        run_number: int = 1,
    ) -> None:
        """Append ``report`` as one ``agent_readiness_runs`` row. Swallows
        failures with a warning log — never raises to the caller.

        ``started_at`` and ``run_number`` are stamped by the caller so the
        stored row carries the same provenance as the returned report.
        """
        try:
            self._write(
                report=report,
                trigger=trigger,
                triggered_by_user_id=triggered_by_user_id,
                dependency_stamp=dependency_stamp,
                duration_ms=duration_ms,
                error=error,
                started_at=started_at or datetime.now(timezone.utc),
                run_number=run_number,
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
        started_at: datetime,
        run_number: int,
    ) -> None:
        row = self._row_from_report(
            report=report,
            trigger=trigger,
            triggered_by_user_id=triggered_by_user_id,
            dependency_stamp=dependency_stamp,
            duration_ms=duration_ms,
            error=error,
            started_at=started_at,
            run_number=run_number,
        )

        # Append one run row — the table is append-only, so "latest" is just the
        # most recent row and there is no snapshot to keep in sync.
        self.db.add(AgentReadinessRun(**row))
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
        started_at: datetime,
        run_number: int,
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
            "started_at": started_at,
            "computed_at": _parse_iso(report.generated_at),
            "run_number": run_number,
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
