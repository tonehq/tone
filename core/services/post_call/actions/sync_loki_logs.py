from loguru import logger

from core.models.call import Call
from core.services.ingestion_queue import enqueue_loki_log_sync_sync
from core.services.post_call.actions.base import PostCallAction
from shared.config import settings


class SyncLokiLogsAction(PostCallAction):
    """Read the just-ended call's log lines back from Loki into ``pipeline_logs``.

    No enable/disable flag — always wired. Safe no-op when Loki read creds are
    absent (local dev) or the call never got a ``trace_id``, so nothing to fetch.
    The job is deferred by ``LOKI_SYNC_DELAY_SECONDS`` so Loki has ingested the
    call's teardown lines before we query them."""

    name = "sync_loki_logs"

    def enqueue(self, call: Call) -> None:
        if not call.trace_id or not settings.loki_read_configured():
            logger.debug(
                "[loki_sync] call={} not enqueued (trace_id={}, configured={})",
                call.id, bool(call.trace_id), settings.loki_read_configured(),
            )
            return
        enqueue_loki_log_sync_sync(call.id, delay_seconds=settings.LOKI_SYNC_DELAY_SECONDS)
