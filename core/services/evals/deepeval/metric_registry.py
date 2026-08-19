"""Single source of truth for the DeepEval metrics Tone knows how to run.

``SUPPORTED_METRICS`` maps a stable, lower-snake-case name (also the JSON
key stored on ``eval_results.metric_scores``) to a builder that constructs
the configured DeepEval metric. The judge never instantiates metrics
directly — it calls :func:`build_metrics` with the operator-selected
names + threshold and receives ready-to-run metric objects.

Unknown names raise ``EvalConfigurationError`` at construction time (not
mid-eval) so misconfiguration fails loudly before any expensive work.
"""

from __future__ import annotations

# Fire the DeepEval telemetry opt-out BEFORE any ``deepeval`` import in this
# module — direct submodule imports (bypassing the package ``__init__``)
# would otherwise let PostHog/Sentry beacons fire and the nest_asyncio
# monkey-patch install before opt-out is set. ``opt_out`` is idempotent.
from core.services.evals.deepeval.telemetry import opt_out as _opt_out

_opt_out()

from typing import Callable, List, Tuple  # noqa: E402

from deepeval.metrics import (  # noqa: E402
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
)
from deepeval.metrics.base_metric import BaseMetric  # noqa: E402
from deepeval.test_case import LLMTestCaseParams  # noqa: E402

from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.errors import EvalConfigurationError  # noqa: E402


MetricBuilder = Callable[[ToneDeepEvalLLM, float], BaseMetric]


def _faithfulness(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return FaithfulnessMetric(threshold=threshold, model=llm, async_mode=True)


def _answer_relevancy(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return AnswerRelevancyMetric(threshold=threshold, model=llm, async_mode=True)


def _contextual_precision(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return ContextualPrecisionMetric(threshold=threshold, model=llm, async_mode=True)


def _contextual_recall(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return ContextualRecallMetric(threshold=threshold, model=llm, async_mode=True)


def _contextual_relevancy(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return ContextualRelevancyMetric(threshold=threshold, model=llm, async_mode=True)


def _hallucination(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return HallucinationMetric(threshold=threshold, model=llm, async_mode=True)


def _correctness(llm: ToneDeepEvalLLM, threshold: float) -> BaseMetric:
    return GEval(
        name="correctness",
        criteria=(
            "Determine whether the 'actual output' is factually correct "
            "based on the 'expected output'. Judge purely on factual "
            "alignment — style, wording, and length differences do not "
            "count as errors."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
        model=llm,
        async_mode=True,
    )


SUPPORTED_METRICS: dict[str, MetricBuilder] = {
    "faithfulness": _faithfulness,
    "answer_relevancy": _answer_relevancy,
    "contextual_precision": _contextual_precision,
    "contextual_recall": _contextual_recall,
    "contextual_relevancy": _contextual_relevancy,
    "hallucination": _hallucination,
    "correctness": _correctness,
}


def build_metrics(
    llm: ToneDeepEvalLLM,
    enabled: List[str],
    threshold: float,
) -> List[Tuple[str, BaseMetric]]:
    """Return ``(name, metric)`` pairs for every UNIQUE name in ``enabled``
    (order preserved by first occurrence).

    The returned name is the registry key — NOT a value derived from the
    metric class name — so the scorecard key is stable across DeepEval SDK
    class renames and never collides via substring matching.

    Unknown names raise ``EvalConfigurationError`` naming the bad key + the
    list of supported names so the operator can fix ``EVAL_METRICS_ENABLED``
    without reading source. Duplicates are dropped silently — running the
    same LLM-scored metric twice doubles cost and the scorecard would only
    keep the last write anyway, so early dedupe is the safe default.
    """
    if not enabled:
        raise EvalConfigurationError(
            "EVAL_METRICS_ENABLED is empty — configure at least one metric "
            f"(supported: {sorted(SUPPORTED_METRICS)})"
        )
    if not (0.0 < threshold <= 1.0):
        raise EvalConfigurationError(
            f"EVAL_METRIC_THRESHOLD must be in (0.0, 1.0]; got {threshold!r}"
        )
    unique_enabled = list(dict.fromkeys(enabled))
    built: List[Tuple[str, BaseMetric]] = []
    for name in unique_enabled:
        builder = SUPPORTED_METRICS.get(name)
        if builder is None:
            raise EvalConfigurationError(
                f"Unknown DeepEval metric {name!r} in EVAL_METRICS_ENABLED "
                f"(supported: {sorted(SUPPORTED_METRICS)})"
            )
        built.append((name, builder(llm, threshold)))
    return built
