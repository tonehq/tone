from uuid import UUID
from typing import List, Dict, Any

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.services.mcp_server_service import McpServerService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


class AttachMcpServerRequest(BaseModel):
    mcp_server_id: int
    agent_ids: List[int]
    selected_tools: List[str] = None


class DetachMcpServerRequest(BaseModel):
    mcp_server_id: int
    agent_ids: List[int]


class UpdateAgentMcpServerRequest(BaseModel):
    mcp_server_id: int
    agent_id: int
    selected_tools: List[str]


def _get_service(claims: EEJWTClaims, db: Session) -> McpServerService:
    return McpServerService(db, org_id=UUID(claims.org_id))


@router.post("/upsert_mcp_server", status_code=status.HTTP_200_OK)
def upsert_mcp_server(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Create or update an MCP server. Send id to update; send name and server_url to create."""
    svc = _get_service(claims, db)
    mcp_server = svc.upsert_mcp_server(data)
    return svc.mcp_server_response(mcp_server)


@router.get("/get_all_mcp_servers")
def get_all_mcp_servers(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    servers = svc.get_mcp_servers()
    return [svc.mcp_server_response(s) for s in servers]


@router.get("/get_mcp_server")
def get_mcp_server(
    mcp_server_id: int = Query(..., description="The MCP server ID to fetch"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    mcp_server = svc.get_mcp_server(mcp_server_id)
    return svc.mcp_server_response(mcp_server)


@router.get("/discover_tools")
async def discover_tools(
    mcp_server_id: int = Query(..., description="The MCP server ID to discover tools from"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Connect to an MCP server and return its available tools."""
    svc = _get_service(claims, db)
    return await svc.discover_tools(mcp_server_id)


@router.delete("/delete_mcp_server", status_code=status.HTTP_200_OK)
def delete_mcp_server(
    mcp_server_id: int = Query(..., description="The MCP server ID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_mcp_server(mcp_server_id)


@router.post("/attach_mcp_server_to_agents")
def attach_mcp_server_to_agents(
    body: AttachMcpServerRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    svc.attach_to_agents(body.mcp_server_id, body.agent_ids, body.selected_tools)
    return {"message": f"MCP server attached to {len(body.agent_ids)} agent(s) successfully"}


@router.delete("/detach_mcp_server_from_agents")
def detach_mcp_server_from_agents(
    body: DetachMcpServerRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.detach_from_agents(body.mcp_server_id, body.agent_ids)


@router.put("/update_agent_mcp_server")
def update_agent_mcp_server(
    body: UpdateAgentMcpServerRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Update selected tools for an MCP server attached to an agent."""
    svc = _get_service(claims, db)
    return svc.update_agent_mcp_server(body.mcp_server_id, body.agent_id, body.selected_tools)


@router.get("/get_mcp_servers_by_agent")
def get_mcp_servers_by_agent(
    agent_id: int = Query(..., description="The agent ID to fetch MCP servers for"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.get_mcp_servers_by_agent(agent_id)
