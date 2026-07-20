"""Reusable list-query helper — search + sort + paginate an already-org-scoped query.

Use ``apply_search_sort_pagination`` for every ``POST /…/list`` endpoint (directories,
contacts, schemas, syncs, agent-contacts) instead of hand-rolling the same
``ilike`` / ``order_by`` / ``offset+limit`` + ``count`` block in each service.

The caller passes a query that is ALREADY org-scoped (via ``BaseService.query``) and
already filtered for soft-delete where relevant; this helper only layers search, sort,
and pagination on top and returns ``(rows, total)``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Query


def apply_search_sort_pagination(
    query: Query,
    *,
    search: Optional[str] = None,
    search_fields: Optional[Sequence] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    sort_map: Optional[Dict[str, Any]] = None,
    page_no: int = 1,
    page_size: int = 20,
) -> Tuple[List[Any], int]:
    """Apply case-insensitive search, whitelisted sort, and pagination to ``query``.

    Args:
        query: an already-scoped SQLAlchemy ``Query``.
        search: free-text term; matched (``ilike``) against every column in
            ``search_fields``. Ignored when blank or when ``search_fields`` is empty.
        search_fields: model columns to search across.
        sort_by: key into ``sort_map`` selecting the sort column; falls back to the
            first ``sort_map`` entry (or no explicit sort) when unknown.
        sort_order: ``"asc"`` or ``"desc"`` (default ``"desc"``).
        sort_map: whitelist mapping public sort keys → model columns. Only keys here
            are sortable, so a client can never sort by an arbitrary column.
        page_no / page_size: 1-based pagination.

    Returns:
        ``(rows, total)`` — the page of rows and the total pre-pagination count.
    """
    term = (search or "").strip()
    if term and search_fields:
        like = f"%{term}%"
        query = query.filter(or_(*[col.ilike(like) for col in search_fields]))

    total = query.count()

    if sort_map:
        col = sort_map.get(sort_by) if sort_by else None
        if col is None:
            col = next(iter(sort_map.values()))
        query = query.order_by(col.asc() if sort_order == "asc" else col.desc())

    page_no = max(page_no, 1)
    page_size = min(max(page_size, 1), 200)
    rows = query.offset((page_no - 1) * page_size).limit(page_size).all()
    return rows, total
