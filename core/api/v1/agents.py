from contextlib import contextmanager
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from core.api.v1.faceted_schemas import FacetsRequest, ListRequest
from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.agent_service import AgentService
from core.services.readiness import ReadinessService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request schemas
# ---------------------------------------------------------------------------

class AgentConfigRequest(BaseModel):
    first_message: Optional[str] = None
    end_call_message: Optional[str] = None
    system_prompt_template: Optional[str] = None
    language_id: Optional[str] = None
    llm_settings: Optional[Dict[str, Any]] = None
    voice_settings: Optional[Dict[str, Any]] = None
    stt_settings: Optional[Dict[str, Any]] = None
    conversation_settings: Optional[Dict[str, Any]] = None
    # Workflow assignment: mode = "prompt" | "workflow"; workflow_id = assigned org workflow.
    mode: Optional[Literal["prompt", "workflow"]] = None
    workflow_id: Optional[str] = None

    @model_validator(mode="after")
    def _require_workflow_when_workflow_mode(self) -> "AgentConfigRequest":
        if self.mode == "workflow" and not self.workflow_id:
            raise ValueError("workflow_id is required when mode is 'workflow'")
        return self


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
    web_channel_ids: Optional[List[str]] = None
    # Optional per-attachment OAuth-connection overrides for this agent version.
    # Maps tool_id / mcp_server_id → oauth_connection_id (or ``null`` to clear).
    # Omitted entries fall back to ``tools.oauth_connection_id`` /
    # ``mcp_servers.oauth_connection_id`` at runtime.
    tool_oauth_overrides: Optional[Dict[str, Optional[str]]] = None
    mcp_server_oauth_overrides: Optional[Dict[str, Optional[str]]] = None


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
    web_channel_ids: Optional[List[str]] = None
    tool_oauth_overrides: Optional[Dict[str, Optional[str]]] = None
    mcp_server_oauth_overrides: Optional[Dict[str, Optional[str]]] = None


class SaveAsNewVersionRequest(BaseModel):
    """Body for ``POST /agent/save_as_new_version``.

    Mirrors ``UpdateAgentRequest`` minus the top-level agent attributes
    (name/description/agent_type/is_active) — a new version is purely a config
    snapshot, not an agent rename.

    ``source_config_id`` declares which existing version the new draft should
    clone its fields and tool/MCP/KB attachments from. When ``from_scratch``
    is ``False`` (default), the editor sends the id of the version it wants
    to copy — omitting it falls back to the published version. When
    ``from_scratch`` is ``True``, no source is read and the draft is born
    with whatever ``config`` the request carries (or empty fields if none) —
    used by the "Start fresh" option in the create-version dialog.
    """
    config: Optional[AgentConfigRequest] = None
    tool_ids: Optional[List[str]] = None
    mcp_server_ids: Optional[List[str]] = None
    upload_ids: Optional[List[str]] = None
    phone_numbers: Optional[List[PhoneNumberAttachment]] = None
    web_channel_ids: Optional[List[str]] = None
    tool_oauth_overrides: Optional[Dict[str, Optional[str]]] = None
    mcp_server_oauth_overrides: Optional[Dict[str, Optional[str]]] = None
    source_config_id: Optional[str] = None
    from_scratch: Optional[bool] = False


class UpdateVersionRequest(BaseModel):
    """Body for ``PUT /agent/update_version``.

    Mirrors {@link SaveAsNewVersionRequest} minus the versioning controls — an
    in-place update never branches into a new row. ``source_config_id`` picks
    which version is mutated; when omitted the service falls back to the live
    one.
    """
    config: Optional[AgentConfigRequest] = None
    tool_ids: Optional[List[str]] = None
    mcp_server_ids: Optional[List[str]] = None
    upload_ids: Optional[List[str]] = None
    phone_numbers: Optional[List[PhoneNumberAttachment]] = None
    web_channel_ids: Optional[List[str]] = None
    tool_oauth_overrides: Optional[Dict[str, Optional[str]]] = None
    mcp_server_oauth_overrides: Optional[Dict[str, Optional[str]]] = None
    source_config_id: Optional[str] = None


class SwitchActiveVersionRequest(BaseModel):
    config_id: str


class CloneAgentRequest(BaseModel):
    """Body for ``POST /agent/clone_agent``. ``name`` is optional — when omitted
    the clone is auto-named ``"<source> (copy)"``."""
    name: Optional[str] = None


class CreateFromTemplateRequest(BaseModel):
    """Body for ``POST /agent/create_from_template``. ``name`` is optional — when
    omitted the new agent takes the template's name."""
    source_config_id: str
    name: Optional[str] = None


class SaveAsTemplateRequest(BaseModel):
    """Body for ``POST /agent/save_as_template``. ``name`` is the template's
    display label shown in the create-from-template picker."""
    name: str


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
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/get_all_agents")
def get_all_agents(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_all_agents()


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
    version: Optional[int] = Query(
        None,
        description=(
            "Optional version number. Resolved to that version server-side so a "
            "deep-linked ?version=<n> loads in a single request. Ignored when "
            "config_id is given."
        ),
    ),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    agent = svc.get_agent(agent_id)
    if config_id:
        config = svc.get_version(agent_id, config_id)
    elif version is not None:
        config = svc.get_version_by_number(agent_id, version)
    else:
        config = None
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


@router.post("/clone_agent", status_code=status.HTTP_201_CREATED)
def clone_agent(
    agent_id: str = Query(..., description="The agent ID to clone"),
    body: Optional[CloneAgentRequest] = None,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    agent = svc.clone_agent(agent_id, user_id, name=body.name if body else None)
    return svc.agent_response(agent)


@router.get("/list_templates")
def list_agent_templates(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_templates()


@router.post("/create_from_template", status_code=status.HTTP_201_CREATED)
def create_from_template(
    body: CreateFromTemplateRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    agent = svc.create_from_template(body.source_config_id, user_id, name=body.name)
    return svc.agent_response(agent)


@router.post("/save_as_template", status_code=status.HTTP_201_CREATED)
def save_as_template(
    body: SaveAsTemplateRequest,
    agent_id: str = Query(..., description="The agent whose live config to snapshot as a template"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    config = svc.save_as_template(agent_id, user_id, name=body.name)
    return svc.version_response(config, is_live=False)


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
        agent_id,
        data,
        user_id,
        source_config_id=source_config_uuid,
        from_scratch=bool(body.from_scratch),
    )
    return svc.agent_response(agent, config=new_config)


@router.put("/update_version")
def update_version(
    body: UpdateVersionRequest,
    agent_id: str = Query(..., description="The agent ID owning the version"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """In-place update of a specific version row — no new draft is created.

    Targets ``source_config_id`` (the version currently loaded in the editor);
    falls back to the live version when omitted. This is the endpoint the
    Save button uses now that versioning lives behind its own button.
    """
    svc = _get_service(claims, db)
    data = body.model_dump(exclude_unset=True)
    source_config_uuid = UUID(body.source_config_id) if body.source_config_id else None
    agent, config = svc.update_version(
        agent_id, data, source_config_id=source_config_uuid
    )
    return svc.agent_response(agent, config=config)


@router.post("/switch_active_version")
async def switch_active_version(
    body: SwitchActiveVersionRequest,
    agent_id: str = Query(..., description="The agent ID to switch live version for"),
    force_warnings: bool = Query(
        False,
        description=(
            "Publish even if the readiness check reports warnings (blockers "
            "always prevent publish). Use only after the user has confirmed."
        ),
    ),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    # Publish gate: verify the target version is safe to promote before we
    # flip the FK. Raises a PublishGateError on blockers or unforced warnings
    # (mapped to HTTP 400 by the api_v1 readiness error handler) before any DB
    # write, so the transaction stays clean.
    readiness = ReadinessService(
        db,
        user_id=UUID(claims.user_id) if claims.user_id else None,
        org_id=UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID),
    )
    await readiness.gate_publish(
        agent_id, body.config_id, force_warnings=force_warnings
    )

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
    body: ListRequest = ListRequest(),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_agents(body.model_dump())


@router.post("/facets")
def get_agent_facets(
    body: FacetsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).facets(filters)


@router.get("/filter-values")
def get_agent_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).filter_values(column_name)


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
