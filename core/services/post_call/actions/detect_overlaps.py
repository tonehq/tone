from core.models.call import Call
from core.services.ingestion_queue import enqueue_call_overlap_detection_sync
from core.services.post_call.actions.base import PostCallAction


class OverlapDetectionAction(PostCallAction):
    name = "detect_overlaps"

    def enqueue(self, call: Call) -> None:
        enqueue_call_overlap_detection_sync(call.id)
