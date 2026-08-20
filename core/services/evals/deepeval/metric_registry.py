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
    BiasMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
    ToxicityMetric,
)
from deepeval.metrics.base_metric import BaseMetric  # noqa: E402
from deepeval.test_case import LLMTestCaseParams  # noqa: E402

from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.errors import EvalConfigurationError  # noqa: E402


# Builders accept an optional ``criterion`` string used by GEval-style metrics
# whose evaluation prompt is driven by the scenario (persona / instruction
# following). Non-GEval builders ignore it.
MetricBuilder = Callable[..., BaseMetric]

# Default GEval criteria — used when a scenario doesn't supply one. Keeping
# them here (not in the scenario file) means an operator running an ad-hoc
# scenario without a criterion still gets a sensible baseline metric.
_DEFAULT_PERSONA_CRITERION = (
    "Determine whether the 'actual output' matches the tone, style, and role "
    "described in the agent's system prompt. Judge on persona fidelity — a "
    "response that is factually fine but breaks character is a fail."
)
_DEFAULT_INSTRUCTION_CRITERION = (
    "Determine whether the 'actual output' follows the explicit instructions "
    "and constraints in the agent's system prompt (things it must do, things "
    "it must not do, output format). Ignore stylistic differences."
)


def _faithfulness(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return FaithfulnessMetric(threshold=threshold, model=llm, async_mode=True)


def _answer_relevancy(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return AnswerRelevancyMetric(threshold=threshold, model=llm, async_mode=True)


def _contextual_precision(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return ContextualPrecisionMetric(threshold=threshold, model=llm, async_mode=True)


def _contextual_recall(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return ContextualRecallMetric(threshold=threshold, model=llm, async_mode=True)


def _contextual_relevancy(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return ContextualRelevancyMetric(threshold=threshold, model=llm, async_mode=True)


def _hallucination(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return HallucinationMetric(threshold=threshold, model=llm, async_mode=True)


def _correctness(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
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


def _bias(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return BiasMetric(threshold=threshold, model=llm, async_mode=True)


def _toxicity(llm: ToneDeepEvalLLM, threshold: float, **_: object) -> BaseMetric:
    return ToxicityMetric(threshold=threshold, model=llm, async_mode=True)


def _persona_adherence(
    llm: ToneDeepEvalLLM,
    threshold: float,
    *,
    criterion: str | None = None,
    **_: object,
) -> BaseMetric:
    return GEval(
        name="persona_adherence",
        criteria=criterion or _DEFAULT_PERSONA_CRITERION,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
        model=llm,
        async_mode=True,
    )


def _instruction_following(
    llm: ToneDeepEvalLLM,
    threshold: float,
    *,
    criterion: str | None = None,
    **_: object,
) -> BaseMetric:
    return GEval(
        name="instruction_following",
        criteria=criterion or _DEFAULT_INSTRUCTION_CRITERION,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
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
    "bias": _bias,
    "toxicity": _toxicity,
    "persona_adherence": _persona_adherence,
    "instruction_following": _instruction_following,
}

# Metrics whose default GEval criterion references an AGENT system prompt —
# meaningless (and misleading) for the RAG judge which never carries one.
# The RAG judge rejects these names at build time via ``EvalConfigurationError``
# so an operator can't silently persist noise scores by adding them to
# ``EVAL_METRICS_ENABLED``. The per-agent judge is free to use them.
AGENT_CONTEXT_METRICS: frozenset[str] = frozenset({
    "persona_adherence",
    "instruction_following",
})


def build_metrics(
    llm: ToneDeepEvalLLM,
    enabled: List[str],
    threshold: float,
    *,
    criteria: dict[str, str] | None = None,
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

    ``criteria`` (optional) maps a metric name to a GEval criterion string —
    the per-scenario override for ``persona_adherence`` /
    ``instruction_following``. Non-GEval builders ignore it. Missing keys fall
    back to the built-in default criterion for that metric.
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
    criteria = criteria or {}
    unique_enabled = list(dict.fromkeys(enabled))
    built: List[Tuple[str, BaseMetric]] = []
    for name in unique_enabled:
        builder = SUPPORTED_METRICS.get(name)
        if builder is None:
            raise EvalConfigurationError(
                f"Unknown DeepEval metric {name!r} in EVAL_METRICS_ENABLED "
                f"(supported: {sorted(SUPPORTED_METRICS)})"
            )
        built.append((name, builder(llm, threshold, criterion=criteria.get(name))))
    return built
