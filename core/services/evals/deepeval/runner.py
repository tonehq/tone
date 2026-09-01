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
        return name, 0.0, "fail", f"{type(e).__name__}: {e}"


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
