"""Shared Pydantic request schemas for faceted list endpoints.

Used by the Tool / MCP Server / Knowledge Base / Agent routers (Core and EE)
so the ``{field, operator, value}`` filter shape and the facets request body are
defined once. Mirrors ``core.api.v1.call_logs.CallFilterParam`` / ``FacetsRequest``.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class FilterParam(BaseModel):
    field: str
    operator: str
    value: object


class FacetsRequest(BaseModel):
    filters: Optional[List[FilterParam]] = None


class ListRequest(BaseModel):
    """Permissive body for faceted ``POST /…/list`` endpoints.

    Every field is optional and unknown keys are preserved (``extra="allow"``)
    so no previously-valid request — which sent a bare/partial JSON object — is
    rejected. Consumers read values via ``model_dump()`` and keep their existing
    clamping / whitelist behavior.
    """

    model_config = ConfigDict(extra="allow")

    page: Optional[int] = None
    page_size: Optional[int] = None
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    filters: Optional[List[Any]] = None
