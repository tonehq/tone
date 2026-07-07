"""Deterministic ("logic") edge-condition evaluation — a safe, tiny expression engine.

Supports the LiquidJS-style boolean expressions Vapi uses on logic edges, e.g.
``{{ user_confirmed == true and number_of_guests <= 10 }}``. Evaluated against the
call's variable context with a whitelisted AST (no function calls, subscripts, imports,
etc.) — never a raw ``eval``.

Supported grammar:
  * comparisons ``== != < <= > >=`` and membership ``in`` / ``not in``
  * boolean ``and`` / ``or`` / ``not``
  * arithmetic ``+ - * / % //`` and unary ``+ -`` over numbers
  * attribute access ``a.b`` over dict-valued variables (e.g. an extracted object)
  * literals (numbers, strings, ``true/false/yes/no``, ``null/nil/none``)

Comparison semantics are numeric-aware and fail-closed:
  * If both operands look numeric (an int/float, or a string like ``"6"``), they are
    compared as NUMBERS — so ``guests > "10"`` is 6 > 10 (False), not the lexicographic
    ``"6" > "10"`` (True) a naive string compare would give.
  * An **ordered** comparison (``< <= > >=``) against a missing/``null`` variable is
    ``False`` — a typo'd variable name can never make ``x > 5`` fire.

AI conditions are NOT handled here; the engine routes those to an injected LLM
navigator. Empty prompts are treated as always-true.
"""
from __future__ import annotations

import ast
import operator
import re
from typing import Any, Dict, Optional

_BIN_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_ORDERED = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)

_ARITH_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# AST node types the grammar permits — used by ``validate_logic`` to reject (at authoring
# time) expressions that would otherwise silently fail-closed to False at call time.
_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,
    ast.Attribute, ast.Name, ast.Load, ast.Constant,
)

_LIQUID = re.compile(r"^\s*\{\{(.*)\}\}\s*$", re.DOTALL)
_INT_RE = re.compile(r"[-+]?\d+")


def _strip_liquid(expr: str) -> str:
    m = _LIQUID.match(expr or "")
    return (m.group(1) if m else (expr or "")).strip()


def _as_number(value: Any):
    """Return an int/float when ``value`` is numeric or a numeric string, else None.

    Booleans are deliberately NOT treated as numbers (so ``confirmed > 0`` doesn't quietly
    compare True as 1).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return int(s) if _INT_RE.fullmatch(s) else float(s)
        except (ValueError, TypeError):
            return None
    return None


def _compare(op: ast.AST, left: Any, right: Any) -> bool:
    fn = _BIN_OPS[type(op)]
    is_ordered = isinstance(op, _ORDERED)

    ln, rn = _as_number(left), _as_number(right)
    if ln is not None and rn is not None:
        # Both operands are numeric (or numeric strings) → compare as numbers.
        return bool(fn(ln, rn))

    if left is None or right is None:
        # Missing/null operand. Ordered comparisons fail-closed (unknown is not orderable);
        # equality/inequality use standard None semantics (None == x → False).
        if is_ordered:
            return False
        return bool(fn(left, right))

    if is_ordered:
        # Both present but not both numeric — only a string/string compare is meaningful;
        # anything else (e.g. number vs non-numeric string) fails closed.
        if isinstance(left, str) and isinstance(right, str):
            return bool(fn(left, right))
        return False

    # Equality/inequality on mixed non-numeric types — compare leniently by string.
    try:
        return bool(fn(left, right))
    except TypeError:
        return bool(fn(str(left), str(right)))


def _eval(node: ast.AST, variables: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, variables)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in vals)
        return any(bool(v) for v in vals)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not bool(_eval(node.operand, variables))
        num = _as_number(_eval(node.operand, variables))
        if num is None:
            raise ValueError("unary +/- requires a number")
        return -num if isinstance(node.op, ast.USub) else num
    if isinstance(node, ast.BinOp):
        fn = _ARITH_OPS.get(type(node.op))
        if fn is None:
            raise ValueError("unsupported arithmetic operator")
        left = _as_number(_eval(node.left, variables))
        right = _as_number(_eval(node.right, variables))
        if left is None or right is None:
            raise ValueError("arithmetic requires numeric operands")
        if isinstance(node.op, (ast.Div, ast.Mod, ast.FloorDiv)) and right == 0:
            raise ValueError("division by zero")
        return fn(left, right)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, variables)
            if isinstance(op, (ast.In, ast.NotIn)):
                # A missing/null container fails closed for BOTH operators: an unknown
                # container can't confirm membership OR non-membership, so a typo'd
                # variable never makes an ``in``/``not in`` branch fire.
                if right is None:
                    ok = False
                else:
                    try:
                        contained = left in right
                    except TypeError:
                        contained = False
                    ok = contained if isinstance(op, ast.In) else not contained
            elif type(op) in _BIN_OPS:
                ok = _compare(op, left, right)
            else:
                raise ValueError("unsupported comparison")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.Attribute):
        obj = _eval(node.value, variables)
        # Only dict-valued variables expose attributes; never touch real object internals.
        return obj.get(node.attr) if isinstance(obj, dict) else None
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


def _bare_literal(body_lower: str) -> Optional[bool]:
    """A bare boolean/null literal → its truthiness; None if not a bare literal."""
    if body_lower in ("true", "yes"):
        return True
    if body_lower in ("false", "no", "null", "nil", "none"):
        return False
    return None


def evaluate_logic(expr: str, variables: Dict[str, Any]) -> bool:
    """Evaluate a logic-edge condition. Returns False on any parse/eval error (fail-closed)."""
    body = _strip_liquid(expr)
    if not body:
        return True  # empty == always
    bare = _bare_literal(body.lower())
    if bare is not None:
        return bare
    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError:
        # Unparseable expression (e.g. natural-language prose on a logic edge) never
        # matches — fail-closed so a malformed condition can't silently fire every turn.
        return False
    try:
        return bool(_eval(tree, variables))
    except Exception:
        return False


def validate_logic(expr: str) -> Optional[str]:
    """Return a human-readable error if ``expr`` is not a valid logic condition, else None.

    Pure and side-effect free — used to reject unsupported/typo'd expressions at authoring
    time (frontend + graph validation) instead of letting them silently fail-closed to
    False during a live call. An empty expression is valid (means "always").
    """
    body = _strip_liquid(expr)
    if not body or _bare_literal(body.lower()) is not None:
        return None
    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError as exc:
        return f"Not a valid expression: {exc.msg}."
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return (
                f"Unsupported expression element '{type(node).__name__}'. Use comparisons "
                "(> < >= <= == !=), and/or/not, in, arithmetic (+ - * /), or a.b access."
            )
    return None
