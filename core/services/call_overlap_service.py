from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import or_

from core.models.call import Call
from core.services.base import BaseService


class CallOverlapService(BaseService):
    """Detects and records other calls whose active time window overlapped
    with a given call. No infrastructure/tenant scoping — a pure time-window
    intersection across all calls."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_and_record(self, call_id: UUID) -> List[UUID]:
        """End-to-end: load the call, find overlaps, persist bidirectionally.
        Returns the list of ids added to this call's ``overlapped_calls``."""
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            logger.warning("[call_overlap] call {} not found; skipping", call_id)
            return []

        overlaps = self.find_overlapping_calls(call)
        if not overlaps:
            return []

        self.record_overlaps(call, overlaps)
        return overlaps

    def find_overlapping_calls(self, call: Call) -> List[UUID]:
        """Return ids of other calls whose active window overlaps ``call``.
        Includes still-in-progress calls."""
        rows = (
            self.db.query(Call.id)
            .filter(
                Call.id != call.id,
                *self._time_overlap_clauses(call.started_at, call.ended_at),
            )
            .all()
        )
        return [row[0] for row in rows]

    def record_overlaps(self, call: Call, overlap_ids: List[UUID]) -> None:
        """Bidirectionally append ``overlap_ids`` to ``call.overlapped_calls``
        and append ``call.id`` to each overlapping call's list.
        De-duplicates, so re-running the job is safe."""
        if not overlap_ids:
            return

        self._append_ids(call, overlap_ids)

        others = self.db.query(Call).filter(Call.id.in_(overlap_ids)).all()
        for other in others:
            self._append_ids(other, [call.id])

        self.db.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _append_ids(call: Call, ids_to_add: List[UUID]) -> None:
        existing = list(call.overlapped_calls or [])
        seen = {str(x) for x in existing}
        for cid in ids_to_add:
            s = str(cid)
            if s == str(call.id) or s in seen:
                continue
            existing.append(s)
            seen.add(s)
        # Reassign (rather than mutate) so SQLAlchemy tracks the JSONB change.
        call.overlapped_calls = existing

    @staticmethod
    def _time_overlap_clauses(started_at: datetime, ended_at: Optional[datetime]) -> list:
        """SQL clauses for "other call's window intersects [started_at, ended_at]".
        Treats ``ended_at=None`` (still running) as "now" for the comparison."""
        window_end = ended_at or datetime.now(timezone.utc)
        return [
            Call.started_at <= window_end,
            or_(Call.ended_at.is_(None), Call.ended_at >= started_at),
        ]
