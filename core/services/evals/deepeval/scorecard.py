"""Shared scorecard-aggregation helper used by every DeepEval-backed judge.

Both the RAG judge (``DeepEvalJudgeService``) and the per-agent LLM judge
(``AgentLlmJudgeService``) call this to turn a set of per-metric measurements
into an aggregate verdict + a single ``judge_reasoning`` string. Kept in one
place so the two judges can't drift.

Aggregation policy:
- Verdict tiers by ratio of passing metrics: ``PASS`` (100%), ``PARTIAL``
  (>=50%), ``FAIL`` (<50%).
- ``judge_reasoning`` concatenates the failure reasons only, ordered as the
  metrics were provided; each reason is clipped to ``per_metric_chars`` and
  the total to ``total_chars`` so one wordy metric can't crowd out the rest.

The caller is responsible for BUILDING the per-metric scorecard dict
(``{name: {"score", "verdict", "reason"}}``) — this helper is pure and does
not touch the DeepEval SDK or the DB.
"""

from __future__ import annotations

from typing import Mapping, Tuple

# Ratio of PASSING metrics required for each aggregate verdict tier.
_PASS_RATIO = 1.0
_PARTIAL_RATIO = 0.5

# Default clipping caps — chosen to fit ~6 metric reasons in one field.
_DEFAULT_PER_METRIC_CHARS = 300
_DEFAULT_TOTAL_CHARS = 2000


def aggregate_scorecard(
    scorecard: Mapping[str, Mapping[str, object]],
    *,
    per_metric_chars: int = _DEFAULT_PER_METRIC_CHARS,
    total_chars: int = _DEFAULT_TOTAL_CHARS,
) -> Tuple[str, str, dict]:
    """Aggregate a per-metric scorecard into ``(verdict, reasoning, scores)``.

    - ``verdict`` — ``"PASS" | "PARTIAL" | "FAIL"`` (empty scorecard → FAIL).
    - ``reasoning`` — joined failure reasons, clipped per-metric and in total.
    - ``scores`` — the input scorecard as a plain dict (defensive copy so
      callers can mutate without touching the input).

    An empty ``scorecard`` yields ``("FAIL", "", {})`` — callers that need
    to distinguish "no metrics ran" from "every metric ran and failed"
    should check both the returned verdict AND ``bool(scorecard)``.
    """
    scores = dict(scorecard)
    if not scores:
        return "FAIL", "", {}

    total = len(scores)
    passes = sum(1 for entry in scores.values() if entry.get("verdict") == "pass")
    ratio = passes / total
    if ratio >= _PASS_RATIO:
        verdict = "PASS"
    elif ratio >= _PARTIAL_RATIO:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    fail_reasons: list[str] = []
    for name, entry in scores.items():
        if entry.get("verdict") != "fail":
            continue
        raw_reason = str(entry.get("reason") or "").strip()
        if not raw_reason:
            continue
        clipped = raw_reason[:per_metric_chars]
        fail_reasons.append(f"{name}: {clipped}")

    reasoning = " | ".join(fail_reasons)[:total_chars] if fail_reasons else ""
    return verdict, reasoning, scores
