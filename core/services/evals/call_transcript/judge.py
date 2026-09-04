"""``CallTranscriptJudgeService`` — DeepEval-backed judge for a completed
call's consolidated transcript.

Same seam pattern as :class:`AgentLlmJudgeService`
(``core/services/evals/agent_llm/agent_llm_judge.py``): one ``.judge(...)``
entry point that runs every enabled metric via ``asyncio.gather``, folds one
metric's exception into a per-metric fail entry (peers keep contributing),
and re-raises :class:`EvalConfigurationError` so a systemic config bug aborts
the run instead of persisting a fake-FAIL row. Delegates verdict / reasoning
rollup to the shared :func:`aggregate_scorecard`.

The one real diff from the agent-LLM judge: this judge builds TWO test cases
and dispatches each metric by the flavor it consumes.

- **Conversation-native** (``role_adherence`` /
  ``conversation_completeness`` / ``conversation_relevancy`` /
  ``knowledge_retention``): measured against a ``ConversationalTestCase``
  built from ``consolidated_transcript`` turns + the agent's
  ``chatbot_role``. Only these names see the full multi-turn structure.
- **Single-turn** (``toxicity`` / ``bias`` / ``instruction_following`` /
  ``persona_adherence`` / everything else in ``SUPPORTED_METRICS``): measured
  against an ``LLMTestCase`` where user/assistant turns are joined
  end-to-end. Joining is a documented v1 tradeoff — per-turn scoring for
  these moves to v2 alongside the per-turn mode.

The registry's ``CONVERSATION_METRICS`` set is the single source of truth for
that dispatch — no per-metric ``isinstance`` guessing here.
"""

from __future__ import annotations

# Fire the DeepEval telemetry opt-out BEFORE any ``deepeval`` import in this
# module (matches every other DeepEval-touching module). ``opt_out`` is
# idempotent.
from core.services.evals.deepeval.telemetry import opt_out as _opt_out

_opt_out()

from typing import List, Optional, Tuple  # noqa: E402

from deepeval.metrics.base_metric import BaseMetric  # noqa: E402
from deepeval.test_case import (  # noqa: E402
    ConversationalTestCase,
    LLMTestCase,
    Turn,
)
from loguru import logger  # noqa: E402

from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.deepeval.metric_registry import (  # noqa: E402
    CONVERSATION_METRICS,
    build_metrics,
)
from core.services.evals.deepeval.runner import (  # noqa: E402
    JudgeOrchestratorError,
    run_scorecard,
)
from core.services.evals.deepeval.scorecard import aggregate_scorecard  # noqa: E402


class CallTranscriptJudgeService:
    """DeepEval-backed judge for a completed call. Kept transport-agnostic:
    takes plain kwargs, returns a plain dict — the service layer stamps the
    result onto the DB row."""

    def judge(
        self,
        *,
        transcript: List[dict],
        system_prompt: Optional[str],
        chatbot_role: Optional[str],
        api_key: str,
        model: str,
        metrics: List[str],
        threshold: float,
    ) -> dict:
        """Score one call's transcript.

        Returns::

            {
                "verdict": "PASS" | "PARTIAL" | "FAIL",
                "reasoning": str,       # joined failure reasons, clipped
                "metric_scores": {name: {"score", "verdict", "reason"}},
            }

        On catastrophic orchestrator failure (non-configuration), returns a
        fail-shape with an empty scorecard + the exception in ``reasoning``.
        """
        turns = _transcript_to_turns(transcript)
        logger.debug(
            "[call-transcript-eval] judge start model={} turns={} metrics={} "
            "chatbot_role_chars={}",
            model,
            len(turns),
            metrics,
            len(chatbot_role or ""),
        )

        # DeepEval's ``RoleAdherenceMetric.a_measure`` raises
        # ``MissingTestCaseParamsError`` when ``ConversationalTestCase.chatbot_role``
        # is empty. That would fake-FAIL every call for an agent with no
        # system_prompt (older seed data, unpublished configs) with an
        # opaque error string — indistinguishable from a real role-adherence
        # failure. Filter the metric out here BEFORE ``build_metrics`` and
        # record it as an explicit ``skipped`` scorecard entry so the FE
        # knows why the metric didn't contribute.
        skipped: dict = {}
        effective_metrics: List[str] = list(metrics)
        if not (chatbot_role and chatbot_role.strip()):
            filtered: List[str] = []
            for m in effective_metrics:
                if m == "role_adherence":
                    skipped[m] = {
                        "score": None,
                        "verdict": "skipped",
                        "reason": (
                            "role_adherence requires chatbot_role — the "
                            "agent's system prompt was empty on this call."
                        ),
                    }
                    continue
                filtered.append(m)
            effective_metrics = filtered

        # Edge case: every enabled metric was pre-filtered as ``skipped``
        # (e.g., an org that enabled only ``role_adherence`` running a call
        # with no system prompt). ``build_metrics`` would otherwise raise
        # ``EvalConfigurationError`` on an empty list; instead, short-circuit
        # to a scored-nothing verdict that preserves the skip trail so the
        # FE / operator sees why nothing scored.
        if not effective_metrics:
            logger.info(
                "[call-transcript-eval] all metrics skipped model={} skipped={}",
                model, list(skipped),
            )
            return {
                "verdict": "FAIL",
                "reasoning": "no metrics scored (all pre-filtered as skipped)",
                "metric_scores": dict(skipped),
            }

        llm = ToneDeepEvalLLM(api_key=api_key, model=model)
        # Config errors are systemic — re-raise so the service aborts the
        # run instead of persisting a fake-FAIL row.
        named_metrics: List[Tuple[str, BaseMetric]] = build_metrics(
            llm,
            effective_metrics,
            threshold,
        )

        conv_case = ConversationalTestCase(
            turns=turns,
            chatbot_role=chatbot_role or None,
        )

        # The joined LLMTestCase feeds every non-conversation-native metric
        # (toxicity/bias — genuinely single-turn — plus the GEval prompt
        # checks, which apply meaningfully over the whole conversation).
        # ``input`` is joined user turns; ``actual_output`` is joined
        # assistant turns; ``system_prompt`` is prepended to ``input`` so the
        # GEval prompts that reference "the system prompt" still see it.
        user_joined = _join_role(turns, "user")
        assistant_joined = _join_role(turns, "assistant")
        composite_input = (
            f"SYSTEM PROMPT:\n{system_prompt}\n\nUSER:\n{user_joined}"
            if system_prompt
            else user_joined
        )
        llm_case = LLMTestCase(
            input=composite_input,
            actual_output=assistant_joined,
        )

        try:
            # The ONE real diff from the other judges: each metric measures
            # against the flavor it consumes — conversation-native metrics see
            # the ``ConversationalTestCase``, everything else the joined
            # ``LLMTestCase``. ``CONVERSATION_METRICS`` is the single source of
            # truth for that dispatch. The asyncio.run + orchestrator-error
            # policy is shared via run_scorecard.
            scorecard = run_scorecard(
                named_metrics,
                lambda name: (
                    conv_case if name in CONVERSATION_METRICS else llm_case
                ),
                log_tag="[call-transcript-eval]",
                model=model,
            )
        except JudgeOrchestratorError as e:
            # Preserve any pre-run skipped entries even on catastrophic
            # orchestrator failure so the FE can still see "role_adherence
            # was skipped because the agent had no system prompt".
            return {
                "verdict": "FAIL",
                "reasoning": f"Judge error: {e}",
                "metric_scores": dict(skipped),
            }

        verdict, reasoning, scores = aggregate_scorecard(scorecard)
        # Fold skipped entries into the scorecard AFTER aggregation so they
        # surface on the persisted row (visible to the FE / analytics)
        # without inflating ``total`` and dragging the pass ratio down.
        # A skip is neither pass nor fail — it's absent from the verdict math.
        if skipped:
            scores = {**scores, **skipped}
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


def _transcript_to_turns(consolidated: List[dict]) -> List[Turn]:
    """Convert ``call.consolidated_transcript`` (per-turn dicts written by
    :class:`ConsolidatedTranscriptService`) into DeepEval ``Turn`` objects.

    For each turn, emit ``Turn(role='user', ...)`` first (if user_speech is
    non-empty) then ``Turn(role='assistant', ...)`` (if bot_speech is
    non-empty). Ordering follows ``turn_number`` because the consolidator
    already sorts by it, but we defensively re-sort so a hand-edited or
    partially-rebuilt column still yields a well-ordered conversation.

    Turns where both sides are empty are dropped — they carry no signal for
    any metric.
    """
    ordered = sorted(
        (t for t in (consolidated or []) if isinstance(t, dict)),
        key=lambda t: (t.get("turn_number") is None, t.get("turn_number") or 0),
    )
    turns: List[Turn] = []
    for entry in ordered:
        user = (entry.get("user_speech") or "").strip()
        bot = (entry.get("bot_speech") or "").strip()
        if user:
            turns.append(Turn(role="user", content=user))
        if bot:
            turns.append(Turn(role="assistant", content=bot))
    return turns


def _join_role(turns: List[Turn], role: str) -> str:
    """Concatenate every ``Turn.content`` for one role into a single string —
    used only to build the fallback ``LLMTestCase`` for non-conversation
    metrics. Empty when the role never spoke."""
    return "\n\n".join(t.content for t in turns if t.role == role and t.content)
