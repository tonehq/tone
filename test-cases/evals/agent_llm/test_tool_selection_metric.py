"""Unit tests for the deterministic ``tool_selection`` metric.

Pure Python, no LLM / DB / DeepEval — the whole point of this metric is
that it's cheap to run and byte-reproducible across replays.
"""

from __future__ import annotations

from core.services.evals.agent_llm.tool_selection_metric import (
    score_tool_selection,
)


def test_returns_none_when_no_expected_tools():
    """Text-only scenario → metric skips (returns None) so the scorecard
    for pre-Phase-2 scenarios is unchanged."""
    assert score_tool_selection(None, None) is None
    assert score_tool_selection([], None) is None
    assert score_tool_selection(None, [{"name": "book", "arguments": {}}]) is None


def test_perfect_match_scores_one():
    """Expected tool called with exactly the expected args → 1.0 / PASS."""
    r = score_tool_selection(
        [{"name": "book", "arguments": {"date": "2026-08-26", "time": "15:00"}}],
        [{"name": "book", "arguments": {"date": "2026-08-26", "time": "15:00"}}],
    )
    assert r["score"] == 1.0
    assert r["verdict"] == "pass"


def test_name_match_only_scores_half():
    """Right tool but no arg matching at all → 0.5, FAIL (below PARTIAL
    threshold)."""
    r = score_tool_selection(
        [{"name": "book", "arguments": {"date": "2026-08-26"}}],
        [{"name": "book", "arguments": {}}],  # missing every expected arg key
    )
    assert r["score"] == 0.5
    # 0.5 is exactly PARTIAL threshold → verdict is "partial", not fail
    assert r["verdict"] == "partial"


def test_name_plus_keys_but_wrong_values_scores_zero_eight():
    """Right tool, right arg keys, wrong values → 0.8 / PASS.
    (This is deliberately optimistic — "the LLM knew to extract date and
    time from the message, it just picked the wrong values" is a partial
    success worth surfacing.)"""
    r = score_tool_selection(
        [{"name": "book", "arguments": {"date": "2026-08-26"}}],
        [{"name": "book", "arguments": {"date": "wrong"}}],
    )
    assert r["score"] == 0.8
    assert r["verdict"] == "pass"


def test_wrong_tool_called_scores_zero():
    """LLM called a different tool than expected → 0.0 / FAIL. The reason
    string mentions which expected tool was missed so the operator can
    debug from the results table without re-running."""
    r = score_tool_selection(
        [{"name": "book", "arguments": {}}],
        [{"name": "cancel", "arguments": {}}],
    )
    assert r["score"] == 0.0
    assert r["verdict"] == "fail"
    assert "book" in r["reason"]


def test_no_tool_called_when_expected_scores_zero():
    """LLM emitted no tool calls at all → 0.0 / FAIL. Distinct reason
    from "wrong tool" so an operator can tell them apart."""
    r = score_tool_selection([{"name": "book"}], [])
    assert r["score"] == 0.0
    assert r["verdict"] == "fail"
    assert "not called" in r["reason"]


def test_no_expected_args_auto_satisfies_arg_subscores():
    """When ``expected.arguments`` is empty, only the name match matters —
    the LLM shouldn't be penalized for not inventing arguments the
    generator didn't ask for. Score is 1.0."""
    r = score_tool_selection(
        [{"name": "book"}],
        [{"name": "book", "arguments": {"random_arg": "value"}}],
    )
    assert r["score"] == 1.0


def test_extra_actual_tools_do_not_tank_score_but_are_noted():
    """LLM called MORE tools than expected → still scored on the expected
    ones; surplus is called out in the reason so a reviewer can see it."""
    r = score_tool_selection(
        [{"name": "book"}],
        [{"name": "book"}, {"name": "cancel"}],
    )
    assert r["score"] == 1.0
    assert "surplus" in r["reason"]
    assert "cancel" in r["reason"]


def test_multiple_expected_tools_averaged():
    """Two expected tools; one called perfectly, one missed → mean = 0.5."""
    r = score_tool_selection(
        [{"name": "book"}, {"name": "cancel"}],
        [{"name": "book"}],
    )
    assert r["score"] == 0.5
    assert r["verdict"] == "partial"


def test_malformed_actual_list_treated_as_no_tools():
    """A non-list ``actual_tools`` (e.g. None) is coerced to ``[]`` — no
    crash, tool scored as "not called"."""
    r = score_tool_selection([{"name": "book"}], "not a list")
    assert r["score"] == 0.0


def test_actual_tools_missing_name_are_skipped():
    """Malformed actual entries (no name) are dropped silently — a broken
    provider payload shouldn't crash the whole run."""
    r = score_tool_selection(
        [{"name": "book"}],
        [{"arguments": {}}, {"name": "book"}],  # first entry has no name
    )
    assert r["score"] == 1.0  # second entry matches


# ── Post-review regression guards ────────────────────────────────────────


def test_matched_actual_is_consumed_not_reused():
    """Regression: two expected calls to the same tool, only one actual —
    the second expected MUST NOT score against the same already-matched
    actual. Before this fix the second expected re-matched the first
    actual by name and got 0.5, inflating aggregate from 0.5 → 0.75."""
    r = score_tool_selection(
        [
            {"name": "send_email", "arguments": {"to": "a@example.com"}},
            {"name": "send_email", "arguments": {"to": "b@example.com"}},
        ],
        [{"name": "send_email", "arguments": {"to": "a@example.com"}}],
    )
    # First expected perfect (1.0), second unmatched (0.0), mean = 0.5.
    assert r["score"] == 0.5
    assert r["verdict"] == "partial"


def test_value_coercion_int_vs_string():
    """Regression: providers often stringify numeric args (schema didn't
    declare type). ``1 == "1"`` should count as a value match — else a
    semantically-correct tool call scores PARTIAL for a type mismatch
    the LLM had no way to avoid."""
    r = score_tool_selection(
        [{"name": "set_age", "arguments": {"age": 25}}],
        [{"name": "set_age", "arguments": {"age": "25"}}],
    )
    assert r["score"] == 1.0


def test_value_coercion_bool_vs_string():
    """Same regression for booleans — ``True == "true"`` counts as match."""
    r = score_tool_selection(
        [{"name": "toggle", "arguments": {"enabled": True}}],
        [{"name": "toggle", "arguments": {"enabled": "true"}}],
    )
    assert r["score"] == 1.0


def test_surplus_report_only_lists_unconsumed_actuals():
    """Post-fix: surplus report should reflect the greedy 1:1 matching —
    a called tool that was consumed by an expected entry MUST NOT appear
    in the surplus list."""
    r = score_tool_selection(
        [{"name": "book"}],
        [{"name": "book"}, {"name": "cancel"}],
    )
    assert r["score"] == 1.0
    assert "cancel" in r["reason"]
    assert "surplus" in r["reason"]
    # 'book' was consumed by the expected entry; it should NOT appear
    # in the surplus segment.
    surplus_segment = r["reason"].split("surplus")[1]
    assert "book" not in surplus_segment
