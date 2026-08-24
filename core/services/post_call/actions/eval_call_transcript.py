from loguru import logger

from core.models.call import Call
from core.services.ingestion_queue import enqueue_call_transcript_eval_sync
from core.services.post_call.actions.base import PostCallAction


class EvalCallTranscriptAction(PostCallAction):
    """Score the call's consolidated transcript with DeepEval and persist
    one ``call_transcript_eval_results`` row.

    The org-level ``eval_settings.call_evals.auto_run_enabled`` gate is
    checked at eval time inside :class:`CallTranscriptEvalService`, NOT
    here — so a redelivered job for an org that opted out AFTER the call
    still respects the toggle and a re-enqueue path (future manual re-run)
    doesn't need to duplicate the check. This action just enqueues.

    Ordering: registered AFTER
    :class:`~core.services.post_call.actions.consolidate_transcript.ConsolidateTranscriptAction`
    in ``PostCallHandler._default_actions``, but consolidation runs on its
    OWN Procrastinate queue and may not have finished by the time this task
    picks up. The service load-checks ``consolidated_transcript`` and skips
    cleanly with ``skip_reason='no_transcript'`` on the race, so ordering
    here is best-effort rather than a hard sync.

    Fast-path skip: ``PostCallHandler.post_call`` fires from BOTH
    ``complete_call`` and ``fail_call``. Failed dials (no-answer,
    media-connect failures, timeouts) never produce transcript turns —
    ``call.metadata_["transcript"]`` is empty, and the eventual
    ``consolidated_transcript`` will be too. Skip the defer entirely in
    that case instead of paying a Procrastinate round-trip + service
    session load only to hit ``skip_reason='no_transcript'``. The service
    still guards for the race (consolidator hasn't run yet), so this is a
    performance short-circuit — not a correctness fix.
    """

    name = "eval_call_transcript"

    def enqueue(self, call: Call) -> None:
        if not _call_has_transcript(call):
            logger.debug(
                "[eval-call-transcript] skip enqueue call={} — no transcript "
                "turns yet (fail_call path or consolidator race)", call.id,
            )
            return
        enqueue_call_transcript_eval_sync(call.id, call.organization_id)


def _call_has_transcript(call: Call) -> bool:
    """Cheap in-process check for whether a call carries any conversation
    turns. Reads whichever source has been populated at post-call time:
    the consolidated view (if the consolidator has already run) OR the
    raw transcript entries under ``call.metadata_["transcript"]``.

    Returns True on ANY hit — we prefer a false-positive enqueue (worker
    picks up and skips with ``no_transcript``) over a false-negative that
    silently drops scoring for a call that DID have turns.
    """
    consolidated = getattr(call, "consolidated_transcript", None)
    if isinstance(consolidated, list) and consolidated:
        return True
    metadata = getattr(call, "metadata_", None) or {}
    raw = metadata.get("transcript") if isinstance(metadata, dict) else None
    return bool(raw)
