"""Request schemas for the Tool routers (Core + EE).

Defined once and imported by both ``core.api.v1.tools`` and ``ee.api.v1.tools``
(same pattern as ``core.api.v1.faceted_schemas``) so the two editions share an
identical, permissive request contract.

Design note — PERMISSIVE ON PURPOSE:
* Every field is Optional with no dumped default, so the schemas never reject a
  request the untyped ``Dict[str, Any] = Body(...)`` used to accept.
* ``extra="allow"`` keeps any unknown/extra field a client currently sends
  instead of 422-ing it.
* Routers pass ``model_dump(exclude_unset=True)`` into the SAME service method,
  so the service receives exactly the keys the client sent (no injected
  defaults) — the create-vs-update required-field checks stay in the service
  (``name``/``description`` required on create → HTTP 400, unchanged).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class UpsertToolRequest(BaseModel):
    """Body for ``POST /tools/upsert_tool``.

    Send ``id`` to update; send ``name`` + ``description`` to create. All fields
    are optional at the schema level — the create-only requirements are enforced
    inline in ``ToolService.upsert_tool`` (HTTP 400) exactly as before.
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tool_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    method: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    oauth_connection_id: Optional[str] = None
    app_integration_id: Optional[str] = None
    is_active: Optional[bool] = None
    # Absent = attachments untouched; present (incl. empty list / null) = full-sync.
    agent_ids: Optional[List[str]] = None


class ToolListRequest(BaseModel):
    """Body for ``POST /tools/list`` (search / filter / sort / paginate).

    Kept fully permissive: every documented key is optional and unknown keys
    pass through ``extra="allow"`` so the free-form list contract is unchanged.
    """

    model_config = ConfigDict(extra="allow")

    # ``page`` / ``page_size`` / ``is_active`` are typed ``Any`` on purpose: the
    # service re-coerces them (``int(...)`` / raw SQL compare), so passing the
    # raw value through avoids any Pydantic coercion that could change behavior.
    page: Optional[Any] = None
    page_size: Optional[Any] = None
    search: Optional[str] = None
    sort: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    tool_type: Optional[str] = None
    is_active: Optional[Any] = None
    filters: Optional[Any] = None
