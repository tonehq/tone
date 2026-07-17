from core.models.call import Call
from core.services.ingestion_queue import (
    enqueue_compute_call_metrics_aggregates_sync,
)
from core.services.post_call.actions.base import PostCallAction


class ComputeCallAggregatesAction(PostCallAction):
    """Enqueues the per-call series-stat compute job.

    Runs on the ``call_metrics`` queue (peer to ``ConsolidateTranscriptAction``,
    which runs on ``call_transcripts``) so it lands after the raw metrics row
    is already persisted by ``CallLogService.complete_call``.
    """

    name = "compute_call_aggregates"

    def enqueue(self, call: Call) -> None:
        enqueue_compute_call_metrics_aggregates_sync(call.id)
