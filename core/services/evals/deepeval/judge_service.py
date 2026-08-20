"""``DeepEvalJudgeService`` — drop-in replacement for the legacy
``JudgeService`` that runs a full RAG scorecard via DeepEval.

Duck-typed against ``JudgeService.judge(...)`` — same kwargs, same shape of
return dict (legacy keys ``verdict``/``correctness``/``groundedness``/
``relevance``/``reasoning``) with one extra key ``metric_scores`` that
carries the full per-metric breakdown. ``EvalService`` picks between the
two engines via ``core.services.evals.judge_factory.build_judge_service``.

Design guarantees:

- **Fail-soft per metric.** One metric raising doesn't kill the eval —
  the offending metric is stamped ``verdict=fail`` with the exception
  reason and the others still contribute to the aggregate verdict.
- **Fail-loud on config.** ``EvalConfigurationError`` (bad
  ``EVAL_METRICS_ENABLED`` / ``EVAL_METRIC_THRESHOLD``) is re-raised so
  the run aborts once instead of persisting N identical fake-FAIL rows.
- **Concurrent execution.** Every metric runs via ``a_measure`` inside a
  single ``asyncio.gather`` so total latency stays close to the slowest
  single metric instead of scaling linearly with metric count.
- **Legacy column mapping.** ``faithfulness → groundedness``,
  ``answer_relevancy → relevance``, ``correctness (GEval) → correctness``.
  Metrics not mapped to a legacy column still land in ``metric_scores``.

**Hallucination is inverted** — DeepEval's ``HallucinationMetric`` scores
higher = worse (more hallucinated). We store the score verbatim in the
scorecard (so it stays interpretable against DeepEval docs) but the
"pass" verdict comes from the metric's own ``.success`` (score < threshold),
never from a `>=` fallback.
"""

from __future__ import annotations

# Fire the DeepEval telemetry opt-out BEFORE any ``deepeval`` import in this
# module so direct submodule imports don't leak PostHog/Sentry beacons or
# install ``nest_asyncio`` before opt-out. ``opt_out`` is idempotent.
from core.services.evals.deepeval.telemetry import opt_out as _opt_out

_opt_out()

import asyncio  # noqa: E402
from typing import Iterable, List, Tuple  # noqa: E402

from deepeval.metrics.base_metric import BaseMetric  # noqa: E402
from deepeval.test_case import LLMTestCase  # noqa: E402
from loguru import logger  # noqa: E402

from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.deepeval.metric_registry import (  # noqa: E402
    AGENT_CONTEXT_METRICS,
    build_metrics,
)
from core.services.evals.deepeval.scorecard import aggregate_scorecard  # noqa: E402
from core.services.evals.errors import EvalConfigurationError  # noqa: E402
from shared.config import settings  # noqa: E402


# metric key on ``metric_scores`` → legacy ``EvalResult`` column filled from it.
_LEGACY_COLUMN_FROM_METRIC = {
    "faithfulness": "groundedness",
    "answer_relevancy": "relevance",
    "correctness": "correctness",
}

# Metrics where a HIGHER score is WORSE (DeepEval's ``HallucinationMetric``
# returns the hallucination fraction). Fallback verdict logic uses the
# opposite comparator (`score < threshold` = pass) for these, and callers
# summarising trends should keep in mind the inversion.
_INVERTED_METRICS: frozenset[str] = frozenset({"hallucination"})

# Aggregate verdict + reason clipping live in
# ``core.services.evals.deepeval.scorecard.aggregate_scorecard`` so the RAG
# judge and the per-agent LLM judge share ONE implementation.


class DeepEvalJudgeService:
    """DeepEval-backed judge. Signature-compatible with ``JudgeService``.

    Instances may be constructed with an explicit ``metrics_enabled`` list
    and ``metric_threshold`` (the resolved per-org overrides). When omitted
    the judge falls back to ``settings.EVAL_METRICS_ENABLED`` /
    ``settings.EVAL_METRIC_THRESHOLD`` so ad-hoc CLI callers keep working
    without threading the resolver."""

    def __init__(
        self,
        *,
        metrics_enabled: list[str] | None = None,
        metric_threshold: float | None = None,
    ) -> None:
        # None → fall through to env at judge() time (preserves the pre-org
        # -settings behavior for callers that don't pass overrides).
        self._metrics_enabled = metrics_enabled
        self._metric_threshold = metric_threshold

    def judge(
        self,
        *,
        question: str,
        expected_answer: str,
        actual_answer: str,
        retrieved_chunks: Iterable[dict],
        api_key: str,
        model: str,
    ) -> dict:
        chunks_list = list(retrieved_chunks)
        retrieval_context = [c.get("text", "") for c in chunks_list]

        # Resolve overrides once per question — cheap dict/list reads, no
        # further env access after this point in the method.
        active_metrics = (
            self._metrics_enabled
            if self._metrics_enabled is not None
            else settings.EVAL_METRICS_ENABLED
        )
        active_threshold = (
            self._metric_threshold
            if self._metric_threshold is not None
            else settings.EVAL_METRIC_THRESHOLD
        )

        logger.debug(
            "[eval] deepeval judge start model={} answer_chars={} chunks={} metrics={}",
            model,
            len(actual_answer or ""),
            len(chunks_list),
            active_metrics,
        )

        # Configuration errors are systemic — one bad setting breaks EVERY
        # question the same way. Re-raise so the caller aborts the whole
        # run once instead of persisting N identical fake-FAIL rows.
        # Reject metrics whose default GEval criterion references an agent
        # system prompt — the RAG flow carries none, so the score would be
        # noise. The per-agent LLM judge is where those belong.
        bad = [m for m in active_metrics if m in AGENT_CONTEXT_METRICS]
        if bad:
            raise EvalConfigurationError(
                f"metrics_enabled contains agent-context metric(s) "
                f"{bad!r}; those require a system prompt the RAG judge "
                "does not carry. Configure them via AGENT_LLM_EVAL_METRICS_ENABLED."
            )
        llm = ToneDeepEvalLLM(api_key=api_key, model=model)
        named_metrics: List[Tuple[str, BaseMetric]] = build_metrics(
            llm,
            active_metrics,
            active_threshold,
        )

        test_case = LLMTestCase(
            input=question,
            actual_output=actual_answer or "",
            expected_output=expected_answer,
            retrieval_context=retrieval_context,
            # DeepEval's ``HallucinationMetric`` treats ``context`` as
            # ground truth. The labeled ``expected_answer`` is the closest
            # ground-truth signal we have per question — much better than
            # the retriever's own output (which may itself be wrong /
            # incomplete). Faithfulness continues to score
            # answer-vs-retrieved-context via ``retrieval_context``.
            context=[expected_answer] if expected_answer else retrieval_context,
        )

        try:
            scorecard = asyncio.run(_run_all(named_metrics, test_case))
        except EvalConfigurationError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[eval] deepeval judge orchestrator failed model={}", model
            )
            return _fail_shape(f"judge error: {type(e).__name__}: {e}")

        return _map_to_legacy(scorecard)


def _fail_shape(reason: str) -> dict:
    """Legacy fail-shape returned when the judge orchestrator can't run at
    all — matches ``JudgeService`` on catastrophic errors so downstream
    persistence and frontend rendering never see a novel shape."""
    return {
        "verdict": "FAIL",
        "correctness": 0.0,
        "groundedness": 0.0,
        "relevance": 0.0,
        "reasoning": reason,
        "metric_scores": {},
    }


async def _run_all(
    named_metrics: List[Tuple[str, BaseMetric]],
    tc: LLMTestCase,
) -> dict:
    """Fire every metric concurrently; one failing metric is captured, not
    raised, so the others still contribute to the aggregate verdict."""
    results = await asyncio.gather(
        *[_safe_measure(name, metric, tc) for name, metric in named_metrics],
        return_exceptions=False,
    )
    scorecard: dict = {}
    for name, score, verdict, reason in results:
        scorecard[name] = {
            "score": score,
            "verdict": verdict,
            "reason": reason,
        }
    return scorecard


async def _safe_measure(name: str, metric: BaseMetric, tc: LLMTestCase):
    """Run one metric, capture any exception as a FAIL entry so peers keep
    contributing. ``name`` is the registry key (authoritative) — never
    derived from the DeepEval class name so scorecard keys stay stable
    across SDK class renames."""
    try:
        await metric.a_measure(tc)
        score = _to_float(getattr(metric, "score", None))
        verdict = _verdict_for(name, metric, score)
        reason = getattr(metric, "reason", None) or ""
        return name, score, verdict, reason
    except Exception as e:  # noqa: BLE001
        logger.exception("[eval] deepeval metric {} raised", name)
        return name, 0.0, "fail", f"{type(e).__name__}: {e}"


def _verdict_for(name: str, metric: BaseMetric, score: float) -> str:
    """Trust the metric's own ``.success`` when it's set (DeepEval's
    implementations handle the score-direction correctly for each metric,
    including hallucination-where-higher-is-worse). Fall back to a
    direction-aware comparison against ``.threshold`` only when
    ``.success`` is genuinely absent."""
    success = getattr(metric, "success", None)
    if success is not None:
        return "pass" if bool(success) else "fail"
    threshold = getattr(metric, "threshold", None)
    if threshold is None:
        return "fail"
    if name in _INVERTED_METRICS:
        return "pass" if score < float(threshold) else "fail"
    return "pass" if score >= float(threshold) else "fail"


def _to_float(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


def _map_to_legacy(scorecard: dict) -> dict:
    """Fold the full per-metric scorecard into the legacy judge dict shape
    ``EvalService._persist_result_batch`` already understands."""
    if not scorecard:
        # Distinguishable from a real all-metrics-fail — the drawer/CLI
        # would otherwise show FAIL with no signal that no metrics ran.
        return _fail_shape("no metrics scored")

    legacy = {"correctness": 0.0, "groundedness": 0.0, "relevance": 0.0}
    for metric_key, column in _LEGACY_COLUMN_FROM_METRIC.items():
        entry = scorecard.get(metric_key)
        if entry:
            legacy[column] = _to_float(entry.get("score"))

    verdict, reasoning, scores = aggregate_scorecard(scorecard)

    return {
        "verdict": verdict,
        "correctness": legacy["correctness"],
        "groundedness": legacy["groundedness"],
        "relevance": legacy["relevance"],
        "reasoning": reasoning,
        "metric_scores": scores,
    }
