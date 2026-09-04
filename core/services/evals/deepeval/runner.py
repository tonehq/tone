"""Shared DeepEval metric-measurement runner — the ONE async loop that fires
every enabled metric concurrently, folds one metric's exception into a
per-metric FAIL entry (peers keep contributing), and returns the scorecard
dict ``{name: {"score", "verdict", "reason"}}``.

Previously ``_safe_measure`` + ``_run_all`` were copy-pasted in all three
DeepEval judges (RAG ``deepeval/judge_service.py``, agent-LLM
``agent_llm/agent_llm_judge.py``, call-transcript ``call_transcript/judge.py``).
The bodies were identical except for TWO things:

- **The test case per metric.** RAG and agent-LLM measure every metric against
  a single ``LLMTestCase``; the call-transcript judge dispatches
  conversation-native metrics to a ``ConversationalTestCase`` and everything
  else to an ``LLMTestCase``. That difference is now injected via the
  ``test_case_for`` callable (``name -> test_case``) — callers pass a lambda
  returning the same case for every name, or a selector keyed on
  ``CONVERSATION_METRICS``.
- **The log tag.** Each judge prefixed its ``logger.exception`` with its own
  context tag; that is now the ``log_tag`` argument.

Verdict + score coercion still come from
``core.services.evals.deepeval.verdict`` (``verdict_for`` / ``to_float``) —
this module does NOT re-implement them.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, List, Tuple

from deepeval.metrics.base_metric import BaseMetric
from loguru import logger

from core.services.evals.deepeval.verdict import to_float, verdict_for
from core.services.evals.errors import EvalConfigurationError
from core.services.rag.errors import humanize_provider_error


class JudgeOrchestratorError(Exception):
    """Raised by :func:`run_scorecard` when the metric run fails for a
    non-configuration reason. Carries the already-humanized, user-safe reason
    so each judge renders its own catastrophic fail-shape without re-importing
    ``humanize_provider_error``. ``EvalConfigurationError`` is deliberately NOT
    wrapped — it re-raises so a systemic config bug aborts the whole run."""


async def _safe_measure(
    name: str,
    metric: BaseMetric,
    tc: Any,
    *,
    log_tag: str,
) -> Tuple[str, float, str, str]:
    """Run one metric, capture any exception as a FAIL entry so peers keep
    contributing. ``name`` is the registry key (authoritative) — never derived
    from the DeepEval class name so scorecard keys stay stable across SDK class
    renames."""
    try:
        await metric.a_measure(tc)
        score = to_float(getattr(metric, "score", None))
        verdict = verdict_for(name, metric, score)
        reason = getattr(metric, "reason", None) or ""
        return name, score, verdict, reason
    except Exception as e:  # noqa: BLE001
        logger.exception(log_tag + " metric {} raised", name)
        return name, 0.0, "fail", humanize_provider_error(e)


async def run_metrics(
    named_metrics: List[Tuple[str, BaseMetric]],
    test_case_for: Callable[[str], Any],
    *,
    log_tag: str,
) -> dict:
    """Fire every metric concurrently on the test case ``test_case_for(name)``
    returns; one failing metric is captured (not raised) so the others still
    contribute to the aggregate verdict.

    Args:
        named_metrics: ``(registry_name, metric)`` pairs from ``build_metrics``.
        test_case_for: maps a metric name to the test case it measures against.
        log_tag: context prefix for the per-metric ``logger.exception`` message.
    """
    results = await asyncio.gather(
        *[
            _safe_measure(name, metric, test_case_for(name), log_tag=log_tag)
            for name, metric in named_metrics
        ],
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


def run_scorecard(
    named_metrics: List[Tuple[str, BaseMetric]],
    test_case_for: Callable[[str], Any],
    *,
    log_tag: str,
    model: str,
) -> dict:
    """Synchronously run :func:`run_metrics` and return the scorecard.

    Shared by all three DeepEval judges (RAG / agent-LLM / call-transcript) so
    the ``asyncio.run`` call and the orchestrator-error policy live in ONE
    place. Re-raises :class:`EvalConfigurationError` unchanged (systemic → the
    caller aborts the run); wraps any other failure in
    :class:`JudgeOrchestratorError` carrying a humanized, user-safe reason so
    each judge renders its own flavor-specific catastrophic fail-shape
    (legacy-column dict for RAG, ``metric_scores`` dict for the others).
    """
    try:
        return asyncio.run(
            run_metrics(named_metrics, test_case_for, log_tag=log_tag)
        )
    except EvalConfigurationError:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(log_tag + " judge orchestrator failed model={}", model)
        raise JudgeOrchestratorError(humanize_provider_error(e)) from e
