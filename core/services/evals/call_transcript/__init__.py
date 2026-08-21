"""Post-call transcript eval harness — DeepEval scoring of what actually
happened on a completed call (as opposed to the RAG flow, which scores
retrieval, and the agent-LLM flow, which scores controlled scenarios).

Transport-agnostic: :class:`CallTranscriptEvalService` takes a SQLAlchemy
session + plain args and returns a dataclass summary. It's invoked by the
:class:`~core.services.post_call.actions.eval_call_transcript.EvalCallTranscriptAction`
post-call action (via the ``score_call_transcript`` Procrastinate task) and
is also usable directly by a future manual re-run endpoint.

Reuses ``core/services/evals/deepeval/`` (telemetry, ``ToneDeepEvalLLM``
adapter, ``metric_registry`` — including the conversation-native metrics
registered for this flavor) so all three eval flows share one DeepEval
foundation.
"""

from core.services.evals.call_transcript.service import (
    CallTranscriptEvalService,
    CallTranscriptEvalSummary,
)

__all__ = ["CallTranscriptEvalService", "CallTranscriptEvalSummary"]
