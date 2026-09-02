from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.models.tool import Tool
from core.services.tool_service import ToolService
from core.api.v1.faceted_schemas import FacetsRequest
from core.schemas.tool_requests import ToolListRequest, UpsertToolRequest
from core.middleware.auth import require_org_member, JWTClaims
from shared.config import settings

router = APIRouter()


def _get_service(claims: JWTClaims, db: Session) -> ToolService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return ToolService(db, org_id=org_id)


@router.post("/list")
def list_tools(
    body: ToolListRequest = ToolListRequest(),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    # exclude_unset keeps the dict identical to the raw body the service read
    # before (only client-supplied keys; extras pass through via extra="allow").
    return _get_service(claims, db).list_tools(body.model_dump(exclude_unset=True))


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
    # Single-resource edit-fetch: the edit form reads back the real auth_config
    # to pre-fill, so this one endpoint returns decrypted secrets. List/collection
    # responses stay masked (the default).
    return svc.tool_response(tool, mask_secrets=False)


@router.post("/upsert_tool", status_code=status.HTTP_200_OK)
def upsert_tool(
    body: UpsertToolRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create or update a tool. Send id to update; send name and description to create.

    Optional ``agent_ids`` full-syncs the tool's published-version agent
    attachments (absent = attachments untouched). Sync problems come back in
    ``attachment_warnings`` — the tool itself is still saved."""
    svc = _get_service(claims, db)
    # exclude_unset so the service sees exactly the keys the client sent — the
    # update path copies provided keys onto the row, and create-only required
    # checks (name/description → 400) stay in the service.
    tool = svc.upsert_tool(body.model_dump(exclude_unset=True))
    resp = svc.tool_response(tool)
    warnings = getattr(tool, "attachment_warnings", None)
    if warnings:
        resp["attachment_warnings"] = warnings
    summary = getattr(tool, "attachment_summary", None)
    if summary is not None:
        resp["attachment_summary"] = summary
    return resp


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


@router.get("/get_agents_by_tool")
def get_agents_by_tool(
    tool_id: str = Query(..., description="The tool ID to fetch attached agents for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Agents whose published version carries this tool — feeds the edit form's
    Agents section (the counterpart of upsert_tool's ``agent_ids``)."""
    svc = _get_service(claims, db)
    return svc.get_agents_by_tool(tool_id)


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
