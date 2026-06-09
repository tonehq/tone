"""Generic faceted-list helpers: filter / sort / facet-count / distinct-value.

Extracted from the call-log implementation (``core.services.call_service``) so
the simple list endpoints (Tool, MCP Server, Knowledge Base, Agent) can offer
the same Vercel-style faceted filtering without copying the logic. These are
pure functions over a SQLAlchemy ``Query`` — no model/session coupling — so a
router, a route-builder closure, or a service method can all reuse them.

A ``column_map`` maps a public field name to a SQLAlchemy column/expression.
Only scalar columns belong in the map; raw JSONB columns must never be added
(grouping/sorting on them is meaningless). Unknown or ``None``-mapped fields are
skipped silently, matching the call-log behaviour.
"""

from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Query


def apply_filters(
    query: Query,
    filters: Optional[List[Dict[str, Any]]],
    column_map: Dict[str, Any],
    exclude_field: Optional[str] = None,
) -> Query:
    """Apply ``[{field, operator, value}]`` filters to ``query`` immutably.

    Supported operators: ``equal_to``, ``greater_than``, ``less_than``,
    ``between`` (value is ``[lo, hi]``), ``in`` (value is a list), ``contains``
    (case-insensitive substring). ``exclude_field`` skips one field so a facet's
    own selection doesn't constrain its own counts (Vercel semantics).
    """
    if not filters:
        return query

    for f in filters:
        field = f.get("field")
        operator = f.get("operator")
        value = f.get("value")

        if exclude_field is not None and field == exclude_field:
            continue

        col = column_map.get(field)
        if col is None:
            continue

        if operator == "equal_to":
            query = query.filter(col == value)
        elif operator == "greater_than":
            query = query.filter(col > value)
        elif operator == "less_than":
            query = query.filter(col < value)
        elif operator == "between":
            if isinstance(value, list) and len(value) == 2:
                query = query.filter(col.between(value[0], value[1]))
        elif operator == "in":
            if isinstance(value, list):
                query = query.filter(col.in_(value))
        elif operator == "contains":
            query = query.filter(col.ilike(f"%{value}%"))

    return query


def apply_sort(
    query: Query,
    column_map: Dict[str, Any],
    sort_by: Optional[str],
    sort_order: str,
    default_col: Any,
) -> Query:
    """Order ``query`` by ``sort_by`` (validated against ``column_map``).

    Falls back to ``default_col`` when ``sort_by`` is missing or unmapped — a bad
    sort field is silently ignored, matching the existing list endpoints.
    """
    sort_col = column_map.get(sort_by) if sort_by else None
    if sort_col is None:
        sort_col = default_col
    order_fn = asc if sort_order == "asc" else desc
    return query.order_by(order_fn(sort_col))


def build_facets(
    base_query_factory: Callable[[], Query],
    column_map: Dict[str, Any],
    facet_fields: List[str],
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: int = 50,
) -> Dict[str, List[Dict[str, Any]]]:
    """Per-value counts for each facet field, for the filter drawer.

    Each facet reflects every *other* active filter but NOT its own selection,
    so toggling a value within a facet doesn't zero out its siblings.
    ``base_query_factory`` must return a fresh query each call (it carries the
    entity's base constraints, joins and org scope).
    """
    result: Dict[str, List[Dict[str, Any]]] = {}

    for field in facet_fields:
        col = column_map.get(field)
        if col is None:
            continue

        scoped = apply_filters(
            base_query_factory(), filters, column_map, exclude_field=field
        )
        rows = (
            scoped.with_entities(col, func.count())
            .group_by(col)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        result[field] = [
            {"value": value, "count": count}
            for value, count in rows
            if value is not None and value != ""
        ]

    return result


def distinct_values(
    base_query: Query,
    column_map: Dict[str, Any],
    column_name: str,
) -> Dict[str, Any]:
    """Distinct non-null/non-empty values of ``column_name`` for autocomplete.

    Raises ``HTTPException(400)`` for a column that isn't in ``column_map``.
    """
    col = column_map.get(column_name)
    if col is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid column: {column_name}. "
                f"Allowed: {', '.join(sorted(column_map))}"
            ),
        )
    rows = base_query.with_entities(col).distinct().all()
    values = sorted([r[0] for r in rows if r[0] is not None and r[0] != ""])
    return {"column": column_name, "values": values}
