from uuid import UUID
from typing import List, Dict, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.services.mcp_server_service import McpServerService
from core.api.v1.faceted_schemas import FacetsRequest
from core.middleware.auth import require_org_member, JWTClaims
from core.utils.pagination import parse_sort, parse_page
from shared.config import settings

router = APIRouter()

_ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "name"}


class AttachMcpServerRequest(BaseModel):
    mcp_server_id: str
    agent_ids: List[str]


class DetachMcpServerRequest(BaseModel):
    mcp_server_id: str
    agent_ids: List[str]


def _get_service(claims: JWTClaims, db: Session) -> McpServerService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return McpServerService(db, org_id=org_id)


@router.post("/list")
def list_mcp_servers(
    data: Dict[str, Any] = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """List MCP servers with search, filtering, sorting, and pagination.

    Body: {
      search?: string,
      is_active?: boolean,
      sort?: string,           # "-field" for desc, "field" for asc
      page?: int (>=1, default 1),
      page_size?: int,         # None/0 means "all"
    }
    """
    # Prefer the new sort_by/sort_order contract; fall back to legacy "-field" sort.
    if data.get("sort_by") or data.get("sort_order"):
        sort_by = data.get("sort_by") or "created_at"
        sort_order = data.get("sort_order") or "desc"
    else:
        sort_by, sort_order = parse_sort(data.get("sort"), _ALLOWED_SORT_FIELDS)
    page, page_size = parse_page(data)

    is_active = data.get("is_active")
    if is_active is not None:
        is_active = bool(is_active)

    svc = _get_service(claims, db)
    return svc.list_mcp_servers(
        search=data.get("search"),
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        filters=data.get("filters"),
    )


@router.post("/facets")
def get_mcp_facets(
    body: FacetsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).get_facets(filters=filters)


@router.get("/filter-values")
def get_mcp_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_filter_values(column_name=column_name)


@router.post("/upsert_mcp_server", status_code=status.HTTP_200_OK)
async def upsert_mcp_server(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create or update an MCP server. Send id to update; send name and server_url to create."""
    svc = _get_service(claims, db)
    mcp_server = await svc.upsert_mcp_server(data)
    return svc.mcp_server_response(mcp_server)


@router.post("/validate_mcp_server", status_code=status.HTTP_200_OK)
async def validate_mcp_server(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Validate an MCP server connection without creating it. Returns discovered tools on success."""
    svc = _get_service(claims, db)
    server_url = data.get("server_url")
    transport_type = data.get("transport_type", "streamable_http")
    auth_config = data.get("auth_config")
    auth_type = data.get("auth_type")
    oauth_connection_id = data.get("oauth_connection_id")
    if not server_url:
        raise HTTPException(status_code=400, detail="server_url is required")
    # Reflect how the server will actually authenticate at call time: custom headers from
    # meta_data plus a fresh OAuth bearer (which wins on conflict) when a connection is linked.
    from core.services.mcp_server_service import headers_from_meta

    extra_headers = {
        **headers_from_meta(data.get("meta_data")),
        **svc._resolve_oauth_headers(oauth_connection_id),
    }
    return await svc.validate_mcp_connection(
        server_url, transport_type, auth_config,
        extra_headers=extra_headers, auth_type=auth_type,
    )


@router.get("/get_mcp_server")
def get_mcp_server(
    mcp_server_id: str = Query(..., description="The MCP server ID to fetch"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    mcp_server = svc.get_mcp_server(mcp_server_id)
    return svc.mcp_server_response(mcp_server)


@router.get("/discover_tools")
async def discover_tools(
    mcp_server_id: str = Query(..., description="The MCP server ID to discover tools from"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Connect to an MCP server and return its available tools."""
    svc = _get_service(claims, db)
    return await svc.discover_tools(mcp_server_id)


@router.get("/get_mcp_tools")
async def get_mcp_tools(
    mcp_server_id: str = Query(..., description="The MCP server ID to fetch tools from"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return only tool name and description for an MCP server."""
    svc = _get_service(claims, db)
    result = await svc.discover_tools(mcp_server_id)
    return [{"name": t["name"], "description": t["description"]} for t in result["tools"]]


@router.delete("/delete_mcp_server", status_code=status.HTTP_200_OK)
def delete_mcp_server(
    mcp_server_id: str = Query(..., description="The MCP server ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_mcp_server(mcp_server_id)


@router.post("/attach_mcp_server_to_agents")
def attach_mcp_server_to_agents(
    body: AttachMcpServerRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    svc.attach_to_agents(body.mcp_server_id, body.agent_ids)
    return {"message": f"MCP server attached to {len(body.agent_ids)} agent(s) successfully"}


@router.delete("/detach_mcp_server_from_agents")
def detach_mcp_server_from_agents(
    body: DetachMcpServerRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.detach_from_agents(body.mcp_server_id, body.agent_ids)




@router.get("/get_mcp_servers_by_agent")
def get_mcp_servers_by_agent(
    agent_id: str = Query(..., description="The agent ID to fetch MCP servers for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.get_mcp_servers_by_agent(agent_id)
