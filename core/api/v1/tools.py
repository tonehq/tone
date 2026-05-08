from uuid import UUID
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.services.tool_service import ToolService
from core.middleware.auth import require_org_member, JWTClaims
from shared.config import settings

router = APIRouter()


class CreateToolRequest(BaseModel):
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    url: str
    method: str = "POST"
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_active: bool = True


class UpdateToolRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    method: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


def _get_service(claims: JWTClaims, db: Session) -> ToolService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return ToolService(db, org_id=org_id)


@router.post("/create_tool", status_code=status.HTTP_201_CREATED)
def create_tool(
    body: CreateToolRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tool = svc.create_tool(body.model_dump())
    return svc.tool_response(tool)


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
    tool_id: int = Query(..., description="The tool ID to fetch"),
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


@router.put("/update_tool")
def update_tool(
    tool_id: int = Query(..., description="The tool ID to update"),
    body: UpdateToolRequest = None,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    data = body.model_dump(exclude_none=True)
    tool = svc.update_tool(tool_id, data)
    return svc.tool_response(tool)


@router.delete("/delete_tool", status_code=status.HTTP_200_OK)
def delete_tool(
    tool_id: int = Query(..., description="The tool ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_tool(tool_id)


class AttachToolRequest(BaseModel):
    tool_id: int
    agent_ids: List[int]


class DetachToolRequest(BaseModel):
    tool_id: int
    agent_ids: List[int]


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
    agent_id: int = Query(..., description="The agent ID to fetch tools for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_tools_by_agent(agent_id)
    return [svc.tool_response(t) for t in tools]
