"""Unit tests for deterministic workflow logic-edge conditions.

Pure logic — no DB or network. Covers the condition case-matrix (A1–A13) the workflow
engine relies on to route "logic" edges and Decision nodes. Run:
    pytest test-cases/test_workflow_conditions.py -v -o "addopts="
"""

import pytest

from core.services.pipeline.workflow.conditions import evaluate_logic, validate_logic

VARS = {
    "guests": 6,
    "age": 17,
    "status": "paid",
    "name": "Sam",
    "confirmed": True,
    "items": ["a", "b"],
    "user": {"tier": "gold"},
    "n": "6",          # a number that arrived as a string (extractors often do this)
    "balance": -5,
}


class TestSupportedComparisons:
    """A1–A4: the operators that already worked, still work."""

    @pytest.mark.parametrize("expr, expected", [
        ("{{ guests > 5 }}", True),
        ("{{ guests > 6 }}", False),
        ("{{ age < 18 }}", True),
        ("{{ guests >= 6 }}", True),
        ("{{ age <= 17 }}", True),
        ("{{ status == 'paid' }}", True),
        ("{{ status != 'free' }}", True),
    ])
    def test_var_vs_literal(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected

    @pytest.mark.parametrize("expr, expected", [
        ("{{ guests > 5 and age < 18 }}", True),
        ("{{ guests > 100 and age < 18 }}", False),
        ("{{ guests > 100 or age < 18 }}", True),
        ("{{ not confirmed }}", False),
    ])
    def test_boolean_logic(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected

    @pytest.mark.parametrize("expr, expected", [
        ("{{ confirmed == true }}", True),
        ("{{ confirmed == false }}", False),
    ])
    def test_boolean_literals(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected


class TestEmptyAndProse:
    """A5/A6."""

    def test_empty_is_always_true(self):
        assert evaluate_logic("", VARS) is True
        assert evaluate_logic("{{ }}", VARS) is True

    def test_bare_boolean_literal(self):
        assert evaluate_logic("true", VARS) is True
        assert evaluate_logic("no", VARS) is False

    def test_natural_language_prose_fails_closed(self):
        assert evaluate_logic("the caller confirmed their order", VARS) is False


class TestNumericCoercion:
    """A7/A8: numeric comparisons must be numeric, never lexicographic."""

    @pytest.mark.parametrize("guests, expr, expected", [
        (6, "{{ guests > '10' }}", False),   # 6 > 10 — was wrongly True (string compare)
        (60, "{{ guests > '10' }}", True),
        (6, "{{ guests == '6' }}", True),
    ])
    def test_var_vs_quoted_number(self, guests, expr, expected):
        assert evaluate_logic(expr, {"guests": guests}) is expected

    @pytest.mark.parametrize("expr, expected", [
        ("{{ n > 10 }}", False),   # n == "6" — string-typed number, must compare as 6
        ("{{ n < 10 }}", True),
        ("{{ n == 6 }}", True),
        ("{{ n >= 6 }}", True),
    ])
    def test_string_typed_number(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected


class TestUndefinedVariable:
    """A9: a missing/typo'd variable must never make an ordered comparison fire."""

    @pytest.mark.parametrize("expr", [
        "{{ missing > 5 }}",
        "{{ missing < 5 }}",
        "{{ missing >= 5 }}",
        "{{ missing == 5 }}",
    ])
    def test_missing_var_fails_closed(self, expr):
        assert evaluate_logic(expr, {}) is False

    def test_explicit_null_ordered_is_false(self):
        assert evaluate_logic("{{ null > 5 }}", {}) is False


class TestArithmetic:
    """A10: the 'add' family."""

    @pytest.mark.parametrize("expr, expected", [
        ("{{ guests + 1 > 6 }}", True),
        ("{{ guests + 1 > 7 }}", False),
        ("{{ guests - 1 == 5 }}", True),
        ("{{ guests * 2 == 12 }}", True),
        ("{{ guests / 2 == 3 }}", True),
        ("{{ guests % 4 == 2 }}", True),
    ])
    def test_arithmetic(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected

    def test_division_by_zero_fails_closed(self):
        assert evaluate_logic("{{ guests / 0 == 1 }}", VARS) is False

    def test_arithmetic_on_string_number(self):
        assert evaluate_logic("{{ n + 1 == 7 }}", VARS) is True


class TestMembership:
    """A11: in / not in."""

    @pytest.mark.parametrize("expr, expected", [
        ("{{ 'a' in items }}", True),
        ("{{ status in items }}", False),
        ("{{ status not in items }}", True),
        ("{{ 'Sa' in name }}", True),   # substring
    ])
    def test_membership(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected

    def test_membership_missing_container_fails_closed(self):
        assert evaluate_logic("{{ 'a' in missing }}", {}) is False


class TestAttributeAccess:
    """A12: dotted access over dict-valued variables."""

    @pytest.mark.parametrize("expr, expected", [
        ("{{ user.tier == 'gold' }}", True),
        ("{{ user.tier == 'silver' }}", False),
        ("{{ user.missing == 'x' }}", False),
    ])
    def test_attribute(self, expr, expected):
        assert evaluate_logic(expr, VARS) is expected

    def test_attribute_on_non_dict_is_none(self):
        # name is a string, not a dict → attribute resolves to None → ordered compare False
        assert evaluate_logic("{{ name.length > 0 }}", VARS) is False


class TestExtras:
    def test_negative_numbers(self):
        assert evaluate_logic("{{ balance < -1 }}", VARS) is True
        assert evaluate_logic("{{ balance == -5 }}", VARS) is True

    def test_chained_comparison(self):
        assert evaluate_logic("{{ 1 < guests }}", VARS) is True
        assert evaluate_logic("{{ 5 < guests and guests < 10 }}", VARS) is True

    def test_liquid_wrapper_optional(self):
        assert evaluate_logic("guests > 5", VARS) is True


class TestValidateLogic:
    """A13: authoring-time validation surface."""

    @pytest.mark.parametrize("expr", [
        "",
        "true",
        "{{ guests > 5 }}",
        "{{ guests + 1 > 6 }}",
        "{{ status in items }}",
        "{{ user.tier == 'gold' }}",
        "{{ not confirmed and age < 18 }}",
    ])
    def test_valid_expressions(self, expr):
        assert validate_logic(expr) is None

    @pytest.mark.parametrize("expr", [
        "{{ foo() }}",          # function call
        "{{ a[0] > 1 }}",       # subscript
        "{{ guests >> 5 }}",    # bit-shift
        "{{ guests > }}",       # syntax error
    ])
    def test_invalid_expressions(self, expr):
        assert validate_logic(expr) is not None
