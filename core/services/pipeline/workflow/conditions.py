"""Deterministic ("logic") edge-condition evaluation — a safe, tiny expression engine.

Supports the LiquidJS-style boolean expressions Vapi uses on logic edges, e.g.
``{{ user_confirmed == true and number_of_guests <= 10 }}``. Evaluated against the
call's variable context with a whitelisted AST (no function calls, attribute access,
imports, etc.) — never a raw ``eval``.

AI conditions are NOT handled here; the engine routes those to an injected LLM
navigator. Empty prompts are treated as always-true.
"""
from __future__ import annotations

import ast
import operator
import re
from typing import Any, Dict

_BIN_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

_LIQUID = re.compile(r"^\s*\{\{(.*)\}\}\s*$", re.DOTALL)


def _strip_liquid(expr: str) -> str:
    m = _LIQUID.match(expr or "")
    return (m.group(1) if m else (expr or "")).strip()


def _coerce(value: str):
    low = value.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "nil", "none"):
        return None
    return value


def _eval(node: ast.AST, variables: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, variables)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in vals)
        return any(bool(v) for v in vals)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_eval(node.operand, variables))
    if isinstance(node, ast.Compare):
        left = _eval(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, variables)
            fn = _BIN_OPS.get(type(op))
            if fn is None:
                raise ValueError("unsupported comparison")
            # tolerant compare: stringify when types differ on equality
            try:
                if not fn(left, right):
                    return False
            except TypeError:
                if not fn(str(left), str(right)):
                    return False
            left = right
        return True
    if isinstance(node, ast.Name):
        low = node.id.lower()
        if low == "true":
            return True
        if low in ("false",):
            return False
        if low in ("none", "null", "nil"):
            return None
        return variables.get(node.id)
    if isinstance(node, ast.Constant):
        return node.value
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def evaluate_logic(expr: str, variables: Dict[str, Any]) -> bool:
    """Evaluate a logic-edge condition. Returns False on any parse/eval error (fail-closed)."""
    body = _strip_liquid(expr)
    if not body:
        return True  # empty == always
    # Bare value like "paid" → truthiness of the coerced literal.
    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError:
        return bool(_coerce(body))
    try:
        return bool(_eval(tree, variables))
    except Exception:
        return False
