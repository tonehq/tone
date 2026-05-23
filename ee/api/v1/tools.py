from uuid import UUID
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.models.tool import Tool
from core.services.tool_service import ToolService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

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
    oauth_connection_id: Optional[int] = None
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
    oauth_connection_id: Optional[int] = None
    is_active: Optional[bool] = None


def _get_service(claims: EEJWTClaims, db: Session) -> ToolService:
    return ToolService(db, org_id=UUID(claims.org_id))


@router.post("/create_tool", status_code=status.HTTP_201_CREATED)
def create_tool(
    body: CreateToolRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tool = svc.create_tool(body.model_dump())
    return svc.tool_response(tool)


@router.post("/list")
def list_tools(
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    from sqlalchemy import or_
    from core.services.crud import list_records

    org_id = UUID(claims.org_id)

    page = max(int(body.get("page") or 1), 1)
    page_size = min(max(int(body.get("page_size") or 20), 1), 100)
    search = body.get("search")
    sort_by = body.get("sort_by")
    tool_type = body.get("tool_type")
    is_active = body.get("is_active")

    filters = [Tool.tool_type != 'mcp', Tool.is_template != True]
    if search:
        filters.append(or_(
            Tool.name.ilike(f"%{search}%"),
            Tool.description.ilike(f"%{search}%"),
        ))
    if tool_type:
        filters.append(Tool.tool_type == tool_type)
    if is_active is not None:
        filters.append(Tool.is_active == is_active)

    allowed_sort_fields = {"name", "tool_type", "is_active", "created_at", "updated_at"}
    order_by = Tool.updated_at.desc()
    if sort_by:
        desc = sort_by.startswith("-")
        field_name = sort_by.lstrip("-")
        if field_name in allowed_sort_fields:
            col = getattr(Tool, field_name)
            order_by = col.desc() if desc else col.asc()

    svc = ToolService(db, org_id=org_id)
    items, total = list_records(db, Tool, org_id, page, page_size, filters, order_by)
    return {
        "items": [svc.tool_response(t) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/get_all_tools")
def get_all_tools(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_tools()
    return [svc.tool_response(t) for t in tools if not t.is_template]


@router.get("/get_template_tools")
def get_template_tools(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_template_tools()
    return [svc.tool_response(t) for t in tools]


@router.get("/get_tool")
def get_tool(
    tool_id: str = Query(..., description="The tool ID to fetch"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tool = svc.get_tool(tool_id)
    return svc.tool_response(tool)


@router.post("/upsert_tool", status_code=status.HTTP_200_OK)
def upsert_tool(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Create or update a tool. Send id to update; send name and description to create."""
    svc = _get_service(claims, db)
    tool = svc.upsert_tool(data)
    return svc.tool_response(tool)


@router.put("/update_tool")
def update_tool(
    tool_id: str = Query(..., description="The tool ID to update"),
    body: UpdateToolRequest = None,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    data = body.model_dump(exclude_none=True)
    tool = svc.update_tool(tool_id, data)
    return svc.tool_response(tool)


@router.delete("/delete_tool", status_code=status.HTTP_200_OK)
def delete_tool(
    tool_id: str = Query(..., description="The tool ID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    svc.attach_tool_to_agents(body.agent_ids, body.tool_id)
    return {"message": f"Tool attached to {len(body.agent_ids)} agent(s) successfully"}


@router.delete("/detach_tool_from_agents")
def detach_tool_from_agents(
    body: DetachToolRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.detach_tool_from_agents(body.agent_ids, body.tool_id)


@router.get("/get_tools_by_agent")
def get_tools_by_agent(
    agent_id: str = Query(..., description="The agent ID to fetch tools for"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    tools = svc.get_tools_by_agent(agent_id)
    return [svc.tool_response(t) for t in tools]
