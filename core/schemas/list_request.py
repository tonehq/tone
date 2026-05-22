"""
Shared request/response contract for list endpoints.

Any route that returns a paginated/filterable collection should accept
`ListRequest` as its body. This keeps the contract identical across
organizations, members, invitations, agents, tools, etc. — and lets the
frontend talk to all of them through a single helper.

Response shape stays free-form for now (most existing endpoints return a
bare list); endpoints that opt into the envelope can return `ListResponse`.
"""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field


SortOrder = Literal["asc", "desc"]


class ListRequest(BaseModel):
    """Common body for any POST /list endpoint."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: SortOrder = "desc"
    # Free-form per-entity filters — e.g. {"role": "admin", "status": "active"}.
    filters: Dict[str, Any] = Field(default_factory=dict)


T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    """Optional envelope for endpoints that want to return server-paginated data."""

    rows: List[T]
    total: int
    page: int
    page_size: int


def slice_for_page(items: List[T], page: int, page_size: int) -> List[T]:
    """In-memory pagination — useful while a service still returns the full list."""
    start = (page - 1) * page_size
    return items[start : start + page_size]


def _field_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _matches_search(row: Any, query: str, searchable_fields: Optional[List[str]]) -> bool:
    q = query.lower()
    if searchable_fields:
        for field in searchable_fields:
            val = _field_value(row, field)
            if val is not None and q in str(val).lower():
                return True
        return False
    # No explicit field list — search every value on the row.
    values = row.values() if isinstance(row, dict) else vars(row).values()
    for val in values:
        if val is not None and q in str(val).lower():
            return True
    return False


def apply_list_request(
    rows: List[Any],
    req: ListRequest,
    searchable_fields: Optional[List[str]] = None,
) -> "ListResponse[Any]":
    """
    Apply a `ListRequest`'s search/sort/pagination to an in-memory list and
    return a `ListResponse` envelope. Use this as a drop-in for services that
    already return Python lists (no DB-level pagination yet).

    `searchable_fields` restricts the search to specific keys; omit to search
    every value on each row.
    """
    filtered = list(rows)

    if req.search:
        filtered = [r for r in filtered if _matches_search(r, req.search, searchable_fields)]

    if req.sort_by:
        reverse = req.sort_order == "desc"
        filtered.sort(
            # `None` always sorts last regardless of direction.
            key=lambda r: (_field_value(r, req.sort_by) is None, _field_value(r, req.sort_by) or ""),
            reverse=reverse,
        )

    total = len(filtered)
    page_rows = slice_for_page(filtered, req.page, req.page_size)

    return ListResponse(
        rows=page_rows,
        total=total,
        page=req.page,
        page_size=req.page_size,
    )
