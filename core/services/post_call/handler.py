from typing import List, Optional

from loguru import logger

from core.models.call import Call
from core.services.post_call.actions import (
    ComputeCallAggregatesAction,
    ConsolidateTranscriptAction,
    EvalCallTranscriptAction,
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
        # Order matters only where an action reads state written by a
        # prior one. ``EvalCallTranscriptAction`` runs AFTER
        # ``ConsolidateTranscriptAction`` because it reads
        # ``call.consolidated_transcript``, but each action enqueues its
        # own Procrastinate job on its own queue — so the eval job may
        # actually execute before consolidation finishes. The eval
        # service handles that race by skipping with
        # ``skip_reason='no_transcript'``; ordering here is best-effort
        # scheduling hint, not a hard sync.
        return [
            OverlapDetectionAction(),
            ConsolidateTranscriptAction(),
            EvalCallTranscriptAction(),
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
