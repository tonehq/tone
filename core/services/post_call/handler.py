from typing import List, Optional

from loguru import logger

from core.models.call import Call
from core.services.post_call.actions import (
    ComputeCallAggregatesAction,
    ConsolidateTranscriptAction,
    OverlapDetectionAction,
    PostCallAction,
    SyncLokiLogsAction,
)


class PostCallHandler:
    """Runs the registered post-call actions for a completed/failed call.

    Adding a new post-call action = one new ``PostCallAction`` subclass +
    one entry in :meth:`_default_actions`. ``CallLogService`` does not change.
    """

    def __init__(self, actions: Optional[List[PostCallAction]] = None):
        self._actions = actions if actions is not None else self._default_actions()

    @staticmethod
    def _default_actions() -> List[PostCallAction]:
        return [
            OverlapDetectionAction(),
            ConsolidateTranscriptAction(),
            ComputeCallAggregatesAction(),
            SyncLokiLogsAction(),
        ]

    def post_call(self, call: Call) -> None:
        for action in self._actions:
            try:
                action.enqueue(call)
            except Exception as e:
                logger.error(
                    "Post-call action '{}' failed for call {}: {}",
                    action.name,
                    call.id,
                    e,
                )
