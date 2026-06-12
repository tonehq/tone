from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, exists, or_
from sqlalchemy.orm import Session

from core.api.v1.faceted_schemas import FacetsRequest
from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.models.agent import Agent
from core.models.channel import Channel
from core.models.phone_number import PhoneNumber
from core.services.agent_service import AgentService
from core.utils.faceted_query import apply_filters, apply_sort, build_facets, distinct_values
from core.utils.list_params import resolve_sort
from shared.config import settings

router = APIRouter()


AGENT_FACET_FIELDS = ["agent_type", "status"]


def _agent_column_map(org_id: UUID) -> Dict[str, Any]:
    # ``status`` mirrors the list UI, where an agent is "active" when it has at
    # least one phone number attached. A CASE over an EXISTS subquery lets it
    # flow through the generic faceted-query helpers as a string facet.
    has_phone = exists().where(
        and_(PhoneNumber.agent_id == Agent.id, PhoneNumber.organization_id == org_id)
    )
    return {
        "name": Agent.name,
        "agent_type": Agent.agent_type,
        "status": case((has_phone, "active"), else_="inactive"),
        "is_active": Agent.is_active,
        "created_at": Agent.created_at,
        "updated_at": Agent.updated_at,
    }


def _agent_base_query(db: Session, org_id: UUID):
    """Org-scoped base query for agents (excludes soft-deleted rows)."""
    return db.query(Agent).filter(
        Agent.organization_id == org_id, Agent.deleted_at.is_(None)
    )


# ---------------------------------------------------------------------------
# Pydantic request schemas
# ---------------------------------------------------------------------------

class AgentConfigRequest(BaseModel):
    first_message: Optional[str] = None
    end_call_message: Optional[str] = None
    system_prompt_template: Optional[str] = None
    conversation_history_token_limit: Optional[int] = None
    language_id: Optional[str] = None
    knowledge_model_id: Optional[str] = None
    llm_settings: Optional[Dict[str, Any]] = None
    voice_settings: Optional[Dict[str, Any]] = None
    stt_settings: Optional[Dict[str, Any]] = None
    conversation_settings: Optional[Dict[str, Any]] = None


class PhoneNumberAttachment(BaseModel):
    number: str
    channel_id: str
    label: Optional[str] = None


class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: str
    is_active: bool = True
    config: Optional[AgentConfigRequest] = None
    tool_ids: Optional[List[str]] = None
    mcp_server_ids: Optional[List[str]] = None
    upload_ids: Optional[List[str]] = None
    phone_numbers: Optional[List[PhoneNumberAttachment]] = None


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[AgentConfigRequest] = None
    tool_ids: Optional[List[str]] = None
    mcp_server_ids: Optional[List[str]] = None
    upload_ids: Optional[List[str]] = None
    phone_numbers: Optional[List[PhoneNumberAttachment]] = None


class SaveAsNewVersionRequest(BaseModel):
    """Body for ``POST /agent/save_as_new_version``.

    Mirrors ``UpdateAgentRequest`` minus the top-level agent attributes
    (name/description/agent_type/is_active) — a new version is purely a config
    snapshot, not an agent rename.

    ``source_config_id`` declares which existing version the new draft should
    clone its fields and tool/MCP/KB attachments from. The editor sends the
    version currently loaded in the form ("save what I'm looking at"). When
    omitted, the service falls back to the published version.
    """
    config: Optional[AgentConfigRequest] = None
    tool_ids: Optional[List[str]] = None
    mcp_server_ids: Optional[List[str]] = None
    upload_ids: Optional[List[str]] = None
    phone_numbers: Optional[List[PhoneNumberAttachment]] = None
    source_config_id: Optional[str] = None


class SwitchActiveVersionRequest(BaseModel):
    config_id: str


class GeneratePromptRequest(BaseModel):
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    agent_type: Optional[str] = None
    instruction: Optional[str] = None


class ImprovePromptRequest(BaseModel):
    text: str = Field(..., min_length=1)
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    agent_type: Optional[str] = None


class GeneratedPromptResponse(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: JWTClaims, db: Session) -> AgentService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return AgentService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Helpers (shared with EE)
# ---------------------------------------------------------------------------

def _phone_numbers_for(db: Session, org_id: UUID, agent_ids: list[UUID]) -> dict[UUID, list[dict]]:
    """Batch-fetch phone numbers for the given agents. Returns {agent_id: [{type, no}, ...]}."""
    if not agent_ids:
        return {}
    rows = (
        db.query(PhoneNumber.agent_id, PhoneNumber.number, Channel.channel_type)
        .join(Channel, Channel.id == PhoneNumber.channel_id)
        .filter(
            PhoneNumber.organization_id == org_id,
            PhoneNumber.agent_id.in_(agent_ids),
        )
        .all()
    )
    grouped: dict[UUID, list[dict]] = {}
    for agent_id, number, channel_type in rows:
        grouped.setdefault(agent_id, []).append({"type": channel_type, "no": number})
    return grouped


def _serialize_agent(agent: Agent, phone_map: dict[UUID, list[dict]]) -> dict:
    return {
        "id": str(agent.id),
        "uuid": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "agent_type": agent.agent_type,
        "is_active": agent.is_active,
        "phone_number": phone_map.get(agent.id, []),
        "created_at": agent.created_at.timestamp() if agent.created_at else None,
        "updated_at": agent.updated_at.timestamp() if agent.updated_at else None,
    }


def list_agents_for_org(db: Session, org_id: UUID, body: dict) -> dict:
    """Shared list pipeline used by both core and EE agent list endpoints."""
    page = max(int(body.get("page") or 1), 1)
    page_size = min(max(int(body.get("page_size") or 20), 1), 100)
    search = body.get("search")
    is_active = body.get("is_active")
    agent_type = body.get("agent_type")

    column_map = _agent_column_map(org_id)
    query = _agent_base_query(db, org_id)

    # Named params (back-compat).
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Agent.name.ilike(like), Agent.description.ilike(like)))
    if is_active is not None:
        query = query.filter(Agent.is_active == bool(is_active))
    if agent_type:
        query = query.filter(Agent.agent_type == agent_type)

    # Generic faceted filters + sort.
    query = apply_filters(query, body.get("filters"), column_map)
    total = query.count()
    sort_by, sort_order = resolve_sort(body, "updated_at")
    query = apply_sort(query, column_map, sort_by, sort_order, Agent.updated_at)

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    phone_map = _phone_numbers_for(db, org_id, [a.id for a in items])
    return {
        "items": [_serialize_agent(a, phone_map) for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def agent_facets_for_org(db: Session, org_id: UUID, filters=None) -> dict:
    """Per-value facet counts for the agent filter drawer."""
    return build_facets(
        lambda: _agent_base_query(db, org_id),
        _agent_column_map(org_id),
        AGENT_FACET_FIELDS,
        filters,
    )


def agent_filter_values_for_org(db: Session, org_id: UUID, column_name: str) -> dict:
    """Distinct values of a column for token-search autocomplete."""
    column_map = _agent_column_map(org_id)
    allowed = {k: column_map[k] for k in ("name", "agent_type", "status")}
    return distinct_values(_agent_base_query(db, org_id), allowed, column_name)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/get_all_agents")
def get_all_agents(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    rows = (
        db.query(Agent.id, Agent.name)
        .filter(Agent.organization_id == org_id, Agent.deleted_at.is_(None))
        .order_by(Agent.name.asc())
        .all()
    )
    return [{"id": str(r.id), "uuid": str(r.id), "name": r.name} for r in rows]


@router.post("/create_agent", status_code=status.HTTP_201_CREATED)
def create_agent(
    body: CreateAgentRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    agent = svc.create_agent(body.model_dump(), user_id)
    return svc.agent_response(agent)


@router.get("/get_agent")
def get_agent(
    agent_id: str = Query(..., description="The agent ID to fetch"),
    config_id: Optional[str] = Query(
        None,
        description=(
            "Optional version id. When provided, returns the agent rendered "
            "against this specific config version instead of the live one."
        ),
    ),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    agent = svc.get_agent(agent_id)
    config = svc.get_version(agent_id, config_id) if config_id else None
    return svc.agent_response(agent, config=config)


@router.put("/update_agent")
def update_agent(
    body: UpdateAgentRequest,
    agent_id: str = Query(..., description="The agent ID to update"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    data = body.model_dump(exclude_unset=True)
    agent = svc.update_agent(agent_id, data, user_id)
    return svc.agent_response(agent)


@router.delete("/delete_agent", status_code=status.HTTP_200_OK)
def delete_agent(
    agent_id: str = Query(..., description="The agent ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_agent(agent_id)


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

@router.get("/list_versions")
def list_agent_versions(
    agent_id: str = Query(..., description="The agent ID to list versions for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.list_versions(agent_id)


@router.post("/save_as_new_version", status_code=status.HTTP_201_CREATED)
def save_as_new_version(
    body: SaveAsNewVersionRequest,
    agent_id: str = Query(..., description="The agent ID to version"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    data = body.model_dump(exclude_unset=True)
    source_config_uuid = UUID(body.source_config_id) if body.source_config_id else None
    # New draft is returned alongside the agent so the response renders the
    # freshly-saved version — otherwise the response would still resolve to the
    # currently-live config and the editor would lose the user's edits.
    agent, new_config = svc.save_as_new_version(
        agent_id, data, user_id, source_config_id=source_config_uuid
    )
    return svc.agent_response(agent, config=new_config)


@router.post("/switch_active_version")
def switch_active_version(
    body: SwitchActiveVersionRequest,
    agent_id: str = Query(..., description="The agent ID to switch live version for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    agent = svc.switch_active_version(agent_id, body.config_id)
    return svc.agent_response(agent)


@router.delete("/delete_version", status_code=status.HTTP_200_OK)
def delete_agent_version(
    agent_id: str = Query(..., description="The agent ID owning the version"),
    config_id: str = Query(..., description="The version (agent_config) ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_version(agent_id, config_id)


@router.post("/list")
def list_agents(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return list_agents_for_org(db, org_id, body)


@router.post("/facets")
def get_agent_facets(
    body: FacetsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return agent_facets_for_org(db, org_id, filters)


@router.get("/filter-values")
def get_agent_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return agent_filter_values_for_org(db, org_id, column_name)


# ---------------------------------------------------------------------------
# AI prompt authoring helpers (Generate / Improve)
# ---------------------------------------------------------------------------

def _ai_service(claims: JWTClaims):
    from fastapi import HTTPException

    from core.services.ai_generation_service import (
        AIGenerationService, resolve_openai_api_key)

    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    api_key = resolve_openai_api_key(org_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OpenAI API key configured. Add an OpenAI provider key to use AI generation.",
        )
    return AIGenerationService(api_key)


@contextmanager
def _prompt_errors():
    """Translate AI-generation failures into clean HTTP 400s for the client."""
    from fastapi import HTTPException

    from core.services.ai_generation_service import PromptTruncatedError

    try:
        yield
    except PromptTruncatedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/generate_prompt", response_model=GeneratedPromptResponse)
def generate_prompt(
    body: GeneratePromptRequest,
    claims: JWTClaims = Depends(require_org_member),
):
    svc = _ai_service(claims)
    with _prompt_errors():
        text = svc.generate_system_prompt(
            agent_name=body.agent_name or "",
            agent_description=body.agent_description or "",
            agent_type=body.agent_type or "",
            instruction=body.instruction or "",
        )
    return GeneratedPromptResponse(text=text)


@router.post("/improve_prompt", response_model=GeneratedPromptResponse)
def improve_prompt(
    body: ImprovePromptRequest,
    claims: JWTClaims = Depends(require_org_member),
):
    svc = _ai_service(claims)
    with _prompt_errors():
        text = svc.improve_system_prompt(
            text=body.text,
            agent_name=body.agent_name or "",
            agent_description=body.agent_description or "",
            agent_type=body.agent_type or "",
        )
    return GeneratedPromptResponse(text=text)
