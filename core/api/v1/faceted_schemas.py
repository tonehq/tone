"""Shared Pydantic request schemas for faceted list endpoints.

Used by the Tool / MCP Server / Knowledge Base / Agent routers (Core and EE)
so the ``{field, operator, value}`` filter shape and the facets request body are
defined once. Mirrors ``core.api.v1.call_logs.CallFilterParam`` / ``FacetsRequest``.
"""

from typing import List, Optional

from pydantic import BaseModel


class FilterParam(BaseModel):
    field: str
    operator: str
    value: object


class FacetsRequest(BaseModel):
    filters: Optional[List[FilterParam]] = None
