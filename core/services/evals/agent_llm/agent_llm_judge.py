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

from core.services.evals.agent_llm.tool_selection_metric import (  # noqa: E402
    METRIC_NAME as _TOOL_SELECTION_METRIC,
    score_tool_selection,
)
from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.deepeval.metric_registry import (  # noqa: E402
    CONVERSATION_METRICS,
    build_metrics,
)
from core.services.evals.deepeval.runner import run_metrics  # noqa: E402
from core.services.evals.deepeval.scorecard import aggregate_scorecard  # noqa: E402
from core.services.evals.errors import EvalConfigurationError  # noqa: E402
from core.services.rag.errors import humanize_provider_error  # noqa: E402


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
        expected_tools: Optional[list] = None,
        actual_tools: Optional[list] = None,
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

        # Deterministic tool-selection metric (Phase 2). Runs BEFORE DeepEval
        # so a scenario with no DeepEval metrics enabled still gets scored
        # on tool intent. ``score_tool_selection`` returns ``None`` when
        # ``expected_tools`` is empty — text-only scenarios contribute
        # nothing to the scorecard here (unchanged from v1). The metric
        # never calls an LLM, so no API cost / no latency / deterministic.
        # Strip ``tool_selection`` out of the DeepEval-bound list so
        # ``build_metrics`` doesn't try to construct it as a DeepEval class.
        tool_scorecard_entry = score_tool_selection(expected_tools, actual_tools)
        deepeval_metrics = [m for m in metrics if m != _TOOL_SELECTION_METRIC]

        # Config error: requesting the tool_selection metric without
        # ``expected_tools`` was previously silent — score_tool_selection
        # returned None, DeepEval branch was skipped, scorecard stayed
        # empty, and the row persisted as FAIL 'no metrics scored'. Now
        # a mismatched config surfaces an actionable message to the caller.
        if _TOOL_SELECTION_METRIC in metrics and not expected_tools:
            raise EvalConfigurationError(
                f"Metric {_TOOL_SELECTION_METRIC!r} was enabled but the "
                "scenario has no expected_tools — either populate "
                "expected_tools on the scenario or drop tool_selection "
                "from the metrics list."
            )

        # Reject conversation-native metrics — they need a
        # ``ConversationalTestCase`` (turns + chatbot_role) which this
        # single-turn judge doesn't build. Without this guard,
        # ``build_metrics`` would happily construct e.g. ``RoleAdherenceMetric``
        # and the a_measure call would raise ``MissingTestCaseParamsError``
        # per-scenario, fake-FAILing every row instead of aborting cleanly.
        # Configure these via ``CALL_EVAL_METRICS_ENABLED`` — the post-call
        # transcript judge owns them.
        bad_conv = [m for m in deepeval_metrics if m in CONVERSATION_METRICS]
        if bad_conv:
            raise EvalConfigurationError(
                f"AGENT_LLM_EVAL_METRICS_ENABLED contains conversation-native "
                f"metric(s) {bad_conv!r}; those require a ConversationalTestCase "
                "the agent-LLM judge does not build. Configure them via "
                "CALL_EVAL_METRICS_ENABLED (post-call transcript flavor)."
            )

        # Empty-text guard (Phase 2). When the model emits only tool_calls
        # (no accompanying text) — a legitimate outcome for tool-triggering
        # scenarios — every text-based DeepEval metric (persona_adherence,
        # instruction_following, hallucination, answer_relevancy, ...)
        # would trivially fail against ``actual_output=""``, dragging the
        # aggregate verdict down for a scenario the agent handled
        # correctly. Skip those metrics with a DEBUG log; the deterministic
        # tool_selection metric still runs above and captures the real
        # signal. Fires ONLY when both conditions hold, so text-only
        # scenarios with an accidentally-empty answer still score against
        # the LLM metrics as they did in v1 (an operator would want to
        # know the model returned nothing in that case).
        if not (actual_output or "").strip() and actual_tools:
            if deepeval_metrics:
                logger.debug(
                    "[agent-llm-eval] skipping text-based DeepEval metrics — "
                    "model emitted only tool_calls (no text) — metrics={}",
                    deepeval_metrics,
                )
            deepeval_metrics = []

        # Skip the DeepEval async loop entirely when NO DeepEval metrics
        # are enabled — the deterministic tool metric may still contribute
        # a score row, and paying the async / SDK overhead for zero real
        # metrics would be waste (and would fail-noisily inside
        # ``build_metrics`` which requires at least one metric name).
        scorecard: dict = {}
        if deepeval_metrics:
            llm = ToneDeepEvalLLM(api_key=api_key, model=model)
            # Configuration errors are systemic — re-raise so the service
            # aborts the run once instead of persisting N identical
            # fake-FAIL rows.
            named_metrics: List[Tuple[str, BaseMetric]] = build_metrics(
                llm,
                deepeval_metrics,
                threshold,
                criteria=criteria,
            )

            # DeepEval's LLMTestCase uses ``input`` for the user turn and
            # ``actual_output`` for the model reply. The system prompt isn't
            # a first-class field, but persona/instruction GEval criteria
            # typically reference "the system prompt" — prepend it to the
            # input so the judge sees both turns. Retrieval / expected are
            # optional.
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
                # Agent-LLM measures every metric against the same test case.
                scorecard = asyncio.run(
                    run_metrics(
                        named_metrics,
                        lambda _name: test_case,
                        log_tag="[agent-llm-eval]",
                    )
                )
            except EvalConfigurationError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    "[agent-llm-eval] judge orchestrator failed model={}", model
                )
                return {
                    "verdict": "FAIL",
                    "reasoning": f"Judge error: {humanize_provider_error(e)}",
                    "metric_scores": {},
                }

        # Merge in the deterministic tool metric if it produced a row.
        # Placed AFTER DeepEval so the tool score is visible whether or not
        # the LLM-graded metrics succeeded.
        if tool_scorecard_entry is not None:
            scorecard[_TOOL_SELECTION_METRIC] = tool_scorecard_entry

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
