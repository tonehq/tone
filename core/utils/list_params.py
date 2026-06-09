"""Helpers for reading list-endpoint request params from a dict body."""

from typing import Any, Dict, Optional, Tuple


def resolve_sort(
    body: Dict[str, Any],
    default_field: str,
    default_order: str = "desc",
) -> Tuple[Optional[str], str]:
    """Resolve a (sort_by, sort_order) pair from a request body.

    Supports both the new contract (``sort_by`` = plain field + ``sort_order`` =
    ``asc``/``desc``) and the legacy ``sort_by`` = ``"-field"`` prefixed string,
    so existing callers keep working. Returns ``(default_field, default_order)``
    when no sort is supplied.
    """
    raw = body.get("sort_by")
    order = body.get("sort_order")
    if order is None:
        if raw and raw.startswith("-"):
            return raw[1:], "desc"
        if raw:
            return raw, "asc"
        return default_field, default_order
    return (raw or default_field), order
