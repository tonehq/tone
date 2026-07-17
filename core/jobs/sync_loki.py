from __future__ import annotations

from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.call import Call
from core.services.pipeline_log_sync_service import PipelineLogSyncService


def sync_call_logs(call_id: str) -> None:
    """Read a finished call's log lines from Loki into ``pipeline_logs``.

    Runs inside the ``sync_loki_logs`` procrastinate task, deferred with a delay
    after the call ends so Loki has ingested the call's teardown lines. Idempotent
    (fingerprint dedup), so task-level retries are safe. A missing call is a no-op
    (it may have been deleted between defer and run)."""
    with get_db_context() as db:
        call = db.query(Call).filter(Call.id == UUID(call_id)).first()
        if call is None:
            logger.warning("[loki_sync] call={} not found; skipping", call_id)
            return
        result = PipelineLogSyncService(db, org_id=call.organization_id).sync_call(call)
    logger.info(
        "[loki_sync] job done call={} inserted={} skipped_dup={} fetched={}",
        call_id, result.inserted, result.skipped, result.fetched,
    )
