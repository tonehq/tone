from __future__ import annotations

from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.services.consolidated_transcript_service import ConsolidatedTranscriptService


def consolidate_call_transcript(call_id: str) -> None:
    """Build the per-turn consolidated transcript for a just-ended call.
    Runs inside the ``consolidate_call_transcript`` procrastinate task."""
    with get_db_context() as db:
        rows = ConsolidatedTranscriptService(db).build_and_store(UUID(call_id))
    logger.info(
        "[consolidated_transcript] call={} turns_written={}",
        call_id,
        len(rows) if rows is not None else 0,
    )
