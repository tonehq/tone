from __future__ import annotations

from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.services.call_overlap_service import CallOverlapService


def detect_call_overlaps(call_id: str) -> None:
    """Populate ``overlapped_calls`` for the just-ended call.
    Runs inside the ``detect_call_overlaps`` procrastinate task."""
    with get_db_context() as db:
        overlaps = CallOverlapService(db).detect_and_record(UUID(call_id))
    logger.info("[call_overlap] call={} recorded {} overlap(s)", call_id, len(overlaps))
