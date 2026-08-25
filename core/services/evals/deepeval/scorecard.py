"""Shared scorecard-aggregation helper used by every DeepEval-backed judge.

Both the RAG judge (``DeepEvalJudgeService``) and the per-agent LLM judge
(``AgentLlmJudgeService``) call this to turn a set of per-metric measurements
into an aggregate verdict + a single ``judge_reasoning`` string. Kept in one
place so the two judges can't drift.

Per-metric verdicts:
- ``pass``     — worth 1.0 toward the aggregate score.
- ``partial``  — worth 0.5. Emitted by the deterministic ``tool_selection``
  metric (agent-LLM judge) when the model called the right tool but with
  imperfect arguments. No LLM-graded DeepEval metric emits ``partial``
  today, so this weighting is a pure additive extension — the RAG judge's
  aggregate stays byte-identical to the pre-partial contract.
- anything else (``fail`` / missing / typo) — worth 0.

Aggregation policy:
- Verdict tiers by score ratio: ``PASS`` (100% of max), ``PARTIAL``
  (>=50%), ``FAIL`` (<50%).
- ``judge_reasoning`` concatenates the ``fail`` AND ``partial`` reasons
  (both are actionable — a partial tool match is exactly the "here's why"
  an operator needs to debug), ordered as the metrics were provided; each
  reason is clipped to ``per_metric_chars`` and the total to ``total_chars``
  so one wordy metric can't crowd out the rest. Prefixed with ``[partial]``
  when applicable so a reader can visually distinguish the two classes.

The caller is responsible for BUILDING the per-metric scorecard dict
(``{name: {"score", "verdict", "reason"}}``) — this helper is pure and does
not touch the DeepEval SDK or the DB.
"""

from __future__ import annotations

from typing import Mapping, Tuple

# Ratio of PASSING metrics required for each aggregate verdict tier.
_PASS_RATIO = 1.0
_PARTIAL_RATIO = 0.5

# Per-verdict weight toward the aggregate score. ``partial`` (0.5) is
# emitted by the deterministic ``tool_selection`` metric only; no existing
# DeepEval metric produces it, so this weighting is additive — RAG-judge
# scorecards (which only contain ``pass`` / ``fail``) aggregate identically
# to before this change.
_VERDICT_WEIGHTS: dict[str, float] = {"pass": 1.0, "partial": 0.5}

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
    - ``reasoning`` — joined failure + partial reasons, clipped per-metric
      and in total.
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
    # Score = sum of per-verdict weights (``pass`` 1.0, ``partial`` 0.5,
    # else 0.0). Ratio is score / total so a mix of pass + partial lands
    # in PARTIAL instead of misclassifying to PASS or FAIL.
    weighted_score = sum(
        _VERDICT_WEIGHTS.get(str(entry.get("verdict") or ""), 0.0)
        for entry in scores.values()
    )
    ratio = weighted_score / total
    if ratio >= _PASS_RATIO:
        verdict = "PASS"
    elif ratio >= _PARTIAL_RATIO:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    # Surface BOTH fail and partial reasons — an operator debugging a
    # partial verdict needs to see what specifically fell short (e.g. tool
    # called with the right name but wrong arg values). Partial reasons
    # are prefixed so they're visually distinguishable from hard failures.
    reasons: list[str] = []
    for name, entry in scores.items():
        entry_verdict = str(entry.get("verdict") or "")
        if entry_verdict not in ("fail", "partial"):
            continue
        raw_reason = str(entry.get("reason") or "").strip()
        if not raw_reason:
            continue
        clipped = raw_reason[:per_metric_chars]
        prefix = "[partial] " if entry_verdict == "partial" else ""
        reasons.append(f"{prefix}{name}: {clipped}")

    reasoning = " | ".join(reasons)[:total_chars] if reasons else ""
    return verdict, reasoning, scores
