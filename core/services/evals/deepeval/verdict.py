"""Shared DeepEval verdict helpers — the ONE place that turns a measured
metric + score into a pass/fail verdict, plus the ONE inverted-metrics set and
score-coercion helper.

Previously ``_verdict_for`` / ``_to_float`` / ``_INVERTED_METRICS`` were
copy-pasted in all three DeepEval judges (RAG ``deepeval/judge_service.py``,
agent-LLM ``agent_llm/agent_llm_judge.py``, call-transcript
``call_transcript/judge.py``). The verdict + coercion bodies were byte-identical,
but the RAG copy's ``_INVERTED_METRICS`` had drifted to only
``{"hallucination"}`` while the other two also included ``bias`` and
``toxicity`` — a latent scoring bug: if the RAG judge ran ``bias``/``toxicity``
(both are in ``SUPPORTED_METRICS`` and reachable via ``EVAL_METRICS_ENABLED``)
AND the metric didn't set ``.success``, the fallback would grade them in the
WRONG direction. Centralising here removes the duplication and fixes the drift
with the correct superset. The normal path (``.success`` present) is unaffected
for every judge, so no existing score changes.
"""

from __future__ import annotations

from typing import Any

# Metrics where a HIGHER score is WORSE (DeepEval: hallucination, bias,
# toxicity). Consulted ONLY in the fallback in :func:`verdict_for` when a metric
# didn't set ``.success``; in the normal path DeepEval's ``.success`` already
# encodes the correct direction, so this set never flips a score there.
INVERTED_METRICS: frozenset[str] = frozenset({"hallucination", "bias", "toxicity"})


def verdict_for(name: str, metric: Any, score: float) -> str:
    """Trust the metric's own ``.success`` when set (DeepEval encodes the right
    score direction for each metric, including the inverted ones). Fall back to
    a direction-aware threshold comparison only when ``.success`` is genuinely
    absent."""
    success = getattr(metric, "success", None)
    if success is not None:
        return "pass" if bool(success) else "fail"
    threshold = getattr(metric, "threshold", None)
    if threshold is None:
        return "fail"
    if name in INVERTED_METRICS:
        return "pass" if score < float(threshold) else "fail"
    return "pass" if score >= float(threshold) else "fail"


def to_float(v: Any) -> float:
    """Coerce a metric score to a clamped ``[0.0, 1.0]`` float; ``0.0`` on a
    non-numeric value."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))
