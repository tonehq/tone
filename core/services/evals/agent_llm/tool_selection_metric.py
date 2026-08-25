"""Deterministic ``tool_selection`` metric for the agent-LLM eval.

The generator pre-labels a scenario with the tool call(s) the agent SHOULD
emit (``expected_tools``). The executor captures whatever tool call(s) the
model actually emitted (``actual_tools``). This module compares the two and
produces a numeric score without any LLM call, so tool-selection grading
adds zero LLM cost per scenario and is fully deterministic — safe to run
in CI and reproduce byte-identically across replays.

Scoring (per expected tool, best-match against actual):
    +0.5  the expected tool's name was called at all
    +0.3  every expected ``arguments`` key was present in the actual call
    +0.2  every expected ``arguments`` value matched exactly
    ────
     1.0  perfect match

Aggregate = mean across expected tools. When ``expected_tools`` is empty or
missing this metric returns ``None`` — no metric row is emitted so the
existing metric averages for text-only scenarios are unchanged.

The verdict thresholds match the DeepEval verdict conventions used by the
rest of the agent-LLM judge (PASS >= 0.8; PARTIAL >= 0.5; FAIL otherwise)
so the scorecard aggregator can consume this row unchanged.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional


METRIC_NAME = "tool_selection"

_SCORE_NAME_MATCH = 0.5
_SCORE_ARG_KEYS_MATCH = 0.3
_SCORE_ARG_VALUES_MATCH = 0.2

_PASS_THRESHOLD = 0.8
_PARTIAL_THRESHOLD = 0.5


def score_tool_selection(
    expected_tools: Optional[List[Mapping[str, Any]]],
    actual_tools: Optional[List[Mapping[str, Any]]],
) -> Optional[dict]:
    """Deterministically score whether the model called the expected
    tool(s) with the expected arguments.

    Returns a metric-registry-shaped dict (``{score, verdict, reason}``)
    OR ``None`` when there is nothing to score (empty ``expected_tools``).
    Callers merge the returned dict into their scorecard under
    :data:`METRIC_NAME`.

    Matching is greedy 1:1 — every actual call is consumed at most once
    against an expected entry, so N expected calls to the same tool with
    different args can't all score against a single actual call. Score
    per expected tool = best remaining candidate match; matched actuals
    are removed from the pool for subsequent expected entries.
    """
    expected_list = _normalize_tool_list(expected_tools)
    if not expected_list:
        return None
    # ``remaining_actuals`` is a mutable working copy — matched entries
    # are popped so the next expected can't reuse them. Preserves the
    # original ``actual_tools`` for the surplus report at the end.
    actual_list = _normalize_tool_list(actual_tools)
    remaining_actuals = list(actual_list)

    per_expected_scores: List[float] = []
    reasons: List[str] = []
    for e_idx, expected in enumerate(expected_list):
        best_score, best_reason, best_idx = _best_match(expected, remaining_actuals)
        if best_idx is not None:
            remaining_actuals.pop(best_idx)
        per_expected_scores.append(best_score)
        reasons.append(f"expected[{e_idx}] {expected.get('name')!r}: {best_reason}")

    # Extra actuals (the LLM called MORE tools than expected) don't tank
    # the score — the judge only grades EXPECTED tools were fulfilled.
    # Note them in the reason so a reviewer can see the surplus. Uses the
    # ``remaining_actuals`` list (post-consumption) so we only report the
    # calls that WEREN'T matched to any expected entry.
    if remaining_actuals:
        surplus = [t.get("name") for t in remaining_actuals]
        reasons.append(f"surplus actual tools: {surplus}")

    aggregate = sum(per_expected_scores) / len(per_expected_scores)
    verdict = _verdict_for_score(aggregate)
    return {
        "score": round(aggregate, 4),
        "verdict": verdict,
        "reason": "; ".join(reasons),
    }


def _best_match(
    expected: Mapping[str, Any],
    actual_list: List[Mapping[str, Any]],
) -> tuple[float, str, Optional[int]]:
    """Return ``(best_score, reason, best_idx)`` for ``expected`` against every
    candidate in ``actual_list``. When no actual call matches the name at
    all, score is 0.0, best_idx is ``None``, and the reason explains that.

    ``best_idx`` is the index of the winning candidate in ``actual_list``
    so the caller can remove it from a shared pool for greedy 1:1 matching.
    """
    expected_name = _clean_name(expected.get("name"))
    if not expected_name:
        return 0.0, "expected entry has no name", None

    best_score = 0.0
    best_reason = f"tool {expected_name!r} was not called"
    best_idx: Optional[int] = None

    expected_args = expected.get("arguments") or {}
    if not isinstance(expected_args, Mapping):
        expected_args = {}

    for idx, actual in enumerate(actual_list):
        if _clean_name(actual.get("name")) != expected_name:
            continue

        actual_args = actual.get("arguments") or {}
        if not isinstance(actual_args, Mapping):
            actual_args = {}

        score = _SCORE_NAME_MATCH
        # Arg keys present. Empty expected-args auto-satisfies both arg
        # sub-scores — the agent isn't required to invent parameters.
        if not expected_args:
            score += _SCORE_ARG_KEYS_MATCH + _SCORE_ARG_VALUES_MATCH
            reason = "name matched; no arguments required"
        else:
            missing_keys = [k for k in expected_args if k not in actual_args]
            if not missing_keys:
                score += _SCORE_ARG_KEYS_MATCH
                bad_values = [
                    k for k, v in expected_args.items()
                    if not _values_equal(actual_args.get(k), v)
                ]
                if not bad_values:
                    score += _SCORE_ARG_VALUES_MATCH
                    reason = "name + args matched exactly"
                else:
                    reason = f"name + arg keys matched; values differ on {bad_values}"
            else:
                reason = f"name matched; missing arg keys {missing_keys}"

        if score > best_score:
            best_score = score
            best_reason = reason
            best_idx = idx
            if best_score >= 1.0:
                break

    return best_score, best_reason, best_idx


def _values_equal(a: Any, b: Any) -> bool:
    """Compare two arg values with light coercion — providers often
    stringify numerics (``1`` vs ``"1"``) or types differ across
    JSON <-> Python round-trips (``25`` vs ``25.0``).

    Two-stage check:
    1. Strict equality — fast path, covers the majority.
    2. Case-insensitive string comparison of the trimmed reprs — catches
       ``1 <-> "1"``, ``True <-> "true"``, ``25.0 <-> "25"``.

    Deliberately does NOT do deep-structure equality (nested lists,
    dicts) — those are compared by the strict ``==`` path only, so a
    mismatch there stays a mismatch (as intended).
    """
    if a == b:
        return True
    if a is None or b is None:
        return False
    try:
        return str(a).strip().lower() == str(b).strip().lower()
    except Exception:  # noqa: BLE001 — any __str__ failure means "not equal"
        return False


def _normalize_tool_list(value: Any) -> List[dict]:
    """Coerce a list of tool-call dicts, dropping malformed entries and
    stripping non-dict payloads. Missing / non-list inputs return ``[]``."""
    if not isinstance(value, list):
        return []
    out: List[dict] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(dict(item))
    return out


def _clean_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _verdict_for_score(score: float) -> str:
    if score >= _PASS_THRESHOLD:
        return "pass"
    if score >= _PARTIAL_THRESHOLD:
        return "partial"
    return "fail"


__all__ = ["METRIC_NAME", "score_tool_selection"]
