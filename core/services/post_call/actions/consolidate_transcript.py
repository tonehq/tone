from core.models.call import Call
from core.services.ingestion_queue import enqueue_consolidate_call_transcript_sync
from core.services.post_call.actions.base import PostCallAction


class ConsolidateTranscriptAction(PostCallAction):
    name = "consolidate_transcript"

    def enqueue(self, call: Call) -> None:
        enqueue_consolidate_call_transcript_sync(call.id)
