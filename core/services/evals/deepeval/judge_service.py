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
from core.services.evals.deepeval.metric_registry import build_metrics  # noqa: E402
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

# Aggregate verdict thresholds — ratio of PASSING metrics in the scorecard.
_PASS_RATIO = 1.0
_PARTIAL_RATIO = 0.5

# Per-metric reason cap so one wordy metric doesn't crowd out the others
# in the 2000-char ``judge_reasoning`` field. Chosen to fit ~6 reasons.
_PER_METRIC_REASON_CHARS = 300
_REASONING_TOTAL_CHARS = 2000


class DeepEvalJudgeService:
    """DeepEval-backed judge. Signature-compatible with ``JudgeService``."""

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

        logger.debug(
            "[eval] deepeval judge start model={} answer_chars={} chunks={} metrics={}",
            model,
            len(actual_answer or ""),
            len(chunks_list),
            settings.EVAL_METRICS_ENABLED,
        )

        # Configuration errors are systemic — one bad env var breaks EVERY
        # question the same way. Re-raise so the caller aborts the whole
        # run once instead of persisting N identical fake-FAIL rows.
        llm = ToneDeepEvalLLM(api_key=api_key, model=model)
        named_metrics: List[Tuple[str, BaseMetric]] = build_metrics(
            llm,
            settings.EVAL_METRICS_ENABLED,
            settings.EVAL_METRIC_THRESHOLD,
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

    total = len(scorecard)
    passes = sum(1 for e in scorecard.values() if e.get("verdict") == "pass")
    ratio = passes / total
    if ratio >= _PASS_RATIO:
        verdict = "PASS"
    elif ratio >= _PARTIAL_RATIO:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    # Cap each metric's reason BEFORE joining so a single verbose metric
    # can't crowd out the others under the 2000-char field limit.
    fail_reasons: list[str] = []
    for name, entry in scorecard.items():
        if entry.get("verdict") != "fail":
            continue
        raw_reason = (entry.get("reason") or "").strip()
        if not raw_reason:
            continue
        clipped = raw_reason[:_PER_METRIC_REASON_CHARS]
        fail_reasons.append(f"{name}: {clipped}")
    reasoning = " | ".join(fail_reasons)[:_REASONING_TOTAL_CHARS] if fail_reasons else ""

    return {
        "verdict": verdict,
        "correctness": legacy["correctness"],
        "groundedness": legacy["groundedness"],
        "relevance": legacy["relevance"],
        "reasoning": reasoning,
        "metric_scores": scorecard,
    }
