"""``AgentLlmJudgeService`` — DeepEval-backed judge for per-agent LLM output.

Same seam pattern as ``DeepEvalJudgeService`` (see
``core/services/evals/deepeval/judge_service.py``): a single ``.judge(...)``
entry point that runs every enabled metric via ``asyncio.gather``, folds one
metric's exception into a per-metric fail entry (peers keep contributing),
and re-raises ``EvalConfigurationError`` so a systemic config bug aborts the
run instead of persisting N identical fake-FAIL rows.

Uses the shared ``aggregate_scorecard`` helper so this judge and the RAG
judge can't drift on verdict / reasoning aggregation.

Kwargs differ from the RAG judge:
- No ``retrieved_chunks`` (nothing was retrieved — this scores the raw LLM).
- ``system_prompt`` gets prepended so the LLM produces the same message it
  would on a real call.
- ``persona_criteria`` / ``instruction_criteria`` feed the two GEval metrics
  (``persona_adherence`` / ``instruction_following``) via
  ``metric_registry.build_metrics``'s ``criteria=`` kwarg.
"""

from __future__ import annotations

# Fire the DeepEval telemetry opt-out BEFORE any ``deepeval`` import in this
# module (matches the RAG judge). ``opt_out`` is idempotent.
from core.services.evals.deepeval.telemetry import opt_out as _opt_out

_opt_out()

import asyncio  # noqa: E402
from typing import List, Optional, Tuple  # noqa: E402

from deepeval.metrics.base_metric import BaseMetric  # noqa: E402
from deepeval.test_case import LLMTestCase  # noqa: E402
from loguru import logger  # noqa: E402

from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.deepeval.metric_registry import (  # noqa: E402
    CONVERSATION_METRICS,
    build_metrics,
)
from core.services.evals.deepeval.scorecard import aggregate_scorecard  # noqa: E402
from core.services.evals.errors import EvalConfigurationError  # noqa: E402


# Metrics where a HIGHER score is WORSE (bias/toxicity/hallucination all
# report the offending fraction). DeepEval's ``.success`` handles the
# direction correctly for the metric itself; this set is used ONLY by the
# fallback verdict path when the metric didn't set ``.success``.
_INVERTED_METRICS: frozenset[str] = frozenset({"hallucination", "bias", "toxicity"})


class AgentLlmJudgeService:
    """DeepEval-backed judge for per-agent LLM output. Kept transport-agnostic:
    takes plain kwargs, returns a plain dict — the service layer stamps the
    result onto the DB rows."""

    def judge(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str],
        actual_output: str,
        api_key: str,
        model: str,
        metrics: List[str],
        threshold: float,
        expected_output: Optional[str] = None,
        persona_criteria: Optional[str] = None,
        instruction_criteria: Optional[str] = None,
    ) -> dict:
        """Run every enabled metric on ``(prompt, system_prompt, actual_output)``.

        Returns::

            {
                "verdict": "PASS" | "PARTIAL" | "FAIL",
                "reasoning": str,       # joined failure reasons, clipped
                "metric_scores": {name: {"score", "verdict", "reason"}},
            }

        On catastrophic orchestrator failure (non-configuration), returns a
        fail-shape with an empty scorecard + the exception in ``reasoning``.
        """
        logger.debug(
            "[agent-llm-eval] judge start model={} answer_chars={} metrics={} "
            "persona_criterion={} instruction_criterion={}",
            model,
            len(actual_output or ""),
            metrics,
            bool(persona_criteria),
            bool(instruction_criteria),
        )

        # Per-scenario GEval criteria — only fill the keys we actually have.
        # Unknown / non-GEval metric names are silently ignored by the
        # registry, so this map is safe to build unconditionally.
        criteria: dict[str, str] = {}
        if persona_criteria:
            criteria["persona_adherence"] = persona_criteria
        if instruction_criteria:
            criteria["instruction_following"] = instruction_criteria

        # Reject conversation-native metrics — they need a
        # ``ConversationalTestCase`` (turns + chatbot_role) which this
        # single-turn judge doesn't build. Without this guard,
        # ``build_metrics`` would happily construct e.g. ``RoleAdherenceMetric``
        # and the a_measure call would raise ``MissingTestCaseParamsError``
        # per-scenario, fake-FAILing every row instead of aborting cleanly.
        # Configure these via ``CALL_EVAL_METRICS_ENABLED`` — the post-call
        # transcript judge owns them.
        bad_conv = [m for m in metrics if m in CONVERSATION_METRICS]
        if bad_conv:
            raise EvalConfigurationError(
                f"AGENT_LLM_EVAL_METRICS_ENABLED contains conversation-native "
                f"metric(s) {bad_conv!r}; those require a ConversationalTestCase "
                "the agent-LLM judge does not build. Configure them via "
                "CALL_EVAL_METRICS_ENABLED (post-call transcript flavor)."
            )

        llm = ToneDeepEvalLLM(api_key=api_key, model=model)
        # Configuration errors are systemic — re-raise so the service aborts
        # the run once instead of persisting N identical fake-FAIL rows.
        named_metrics: List[Tuple[str, BaseMetric]] = build_metrics(
            llm,
            metrics,
            threshold,
            criteria=criteria,
        )

        # DeepEval's LLMTestCase uses ``input`` for the user turn and
        # ``actual_output`` for the model reply. The system prompt isn't a
        # first-class field, but persona/instruction GEval criteria typically
        # reference "the system prompt" — prepend it to the input so the
        # judge sees both turns. Retrieval / expected are optional.
        composite_input = (
            f"SYSTEM PROMPT:\n{system_prompt}\n\nUSER:\n{prompt}"
            if system_prompt
            else prompt
        )
        test_case = LLMTestCase(
            input=composite_input,
            actual_output=actual_output or "",
            expected_output=expected_output,
        )

        try:
            scorecard = asyncio.run(_run_all(named_metrics, test_case))
        except EvalConfigurationError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[agent-llm-eval] judge orchestrator failed model={}", model
            )
            return {
                "verdict": "FAIL",
                "reasoning": f"judge error: {type(e).__name__}: {e}",
                "metric_scores": {},
            }

        verdict, reasoning, scores = aggregate_scorecard(scorecard)
        if not scores:
            # Distinguishable from "every metric ran and failed" — otherwise
            # a UI/CLI just shows FAIL with no signal that nothing ran.
            return {
                "verdict": "FAIL",
                "reasoning": "no metrics scored",
                "metric_scores": {},
            }
        return {
            "verdict": verdict,
            "reasoning": reasoning,
            "metric_scores": scores,
        }


async def _run_all(
    named_metrics: List[Tuple[str, BaseMetric]],
    tc: LLMTestCase,
) -> dict:
    """Fire every metric concurrently; capture per-metric exceptions as FAIL
    entries so peers still contribute."""
    results = await asyncio.gather(
        *[_safe_measure(name, metric, tc) for name, metric in named_metrics],
        return_exceptions=False,
    )
    scorecard: dict = {}
    for name, score, verdict, reason in results:
        scorecard[name] = {"score": score, "verdict": verdict, "reason": reason}
    return scorecard


async def _safe_measure(name: str, metric: BaseMetric, tc: LLMTestCase):
    try:
        await metric.a_measure(tc)
        score = _to_float(getattr(metric, "score", None))
        verdict = _verdict_for(name, metric, score)
        reason = getattr(metric, "reason", None) or ""
        return name, score, verdict, reason
    except Exception as e:  # noqa: BLE001
        logger.exception("[agent-llm-eval] metric {} raised", name)
        return name, 0.0, "fail", f"{type(e).__name__}: {e}"


def _verdict_for(name: str, metric: BaseMetric, score: float) -> str:
    """Trust the metric's own ``.success`` (DeepEval sets it with the
    right score direction for each metric, including bias/toxicity/
    hallucination where higher = worse). Fall back to a direction-aware
    threshold comparison only when ``.success`` is genuinely absent."""
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
