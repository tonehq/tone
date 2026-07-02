from uuid import UUID
from typing import List, Dict, Any

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.models.tool import Tool
from core.services.tool_service import ToolService
from core.api.v1.faceted_schemas import FacetsRequest
from core.middleware.auth import require_org_member, JWTClaims
from shared.config import settings

router = APIRouter()


def _get_service(claims: JWTClaims, db: Session) -> ToolService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return ToolService(db, org_id=org_id)


@router.post("/list")
def list_tools(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_tools(body)


@router.post("/facets")
def get_tool_facets(
    body: FacetsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).get_facets(filters=filters)


@router.get("/filter-values")
def get_tool_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_filter_values(column_name=column_name)


@router.get("/get_all_tools")
def get_all_tools(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_tools()
    return [svc.tool_response(t) for t in tools if not t.is_template]


@router.get("/get_template_tools")
def get_template_tools(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_template_tools()
    return [svc.tool_response(t) for t in tools]


@router.get("/get_tool")
def get_tool(
    tool_id: str = Query(..., description="The tool ID to fetch"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tool = svc.get_tool(tool_id)
    return svc.tool_response(tool)


@router.post("/upsert_tool", status_code=status.HTTP_200_OK)
def upsert_tool(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create or update a tool. Send id to update; send name and description to create."""
    svc = _get_service(claims, db)
    tool = svc.upsert_tool(data)
    return svc.tool_response(tool)


@router.delete("/delete_tool", status_code=status.HTTP_200_OK)
def delete_tool(
    tool_id: str = Query(..., description="The tool ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_tool(tool_id)


class AttachToolRequest(BaseModel):
    tool_id: str
    agent_ids: List[str]


class DetachToolRequest(BaseModel):
    tool_id: str
    agent_ids: List[str]


@router.post("/attach_tool_to_agents")
def attach_tool_to_agents(
    body: AttachToolRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    svc.attach_tool_to_agents(body.agent_ids, body.tool_id)
    return {"message": f"Tool attached to {len(body.agent_ids)} agent(s) successfully"}


@router.delete("/detach_tool_from_agents")
def detach_tool_from_agents(
    body: DetachToolRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.detach_tool_from_agents(body.agent_ids, body.tool_id)


@router.get("/get_tools_by_agent")
def get_tools_by_agent(
    agent_id: str = Query(..., description="The agent ID to fetch tools for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_tools_by_agent(agent_id)
    return [svc.tool_response(t) for t in tools]
