from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.api.v1.agents import (
    CreateAgentRequest,
    GeneratePromptRequest,
    GeneratedPromptResponse,
    ImprovePromptRequest,
    SaveAsNewVersionRequest,
    SwitchActiveVersionRequest,
    UpdateAgentRequest,
    _prompt_errors,
    agent_facets_for_org,
    agent_filter_values_for_org,
    list_agents_for_org,
)
from core.api.v1.faceted_schemas import FacetsRequest
from core.database.session import get_db
from core.models.agent import Agent
from core.services.agent_service import AgentService
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


def _get_service(claims: EEJWTClaims, db: Session) -> AgentService:
    org_id = UUID(claims.org_id)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return AgentService(db, user_id=user_id, org_id=org_id)


def _ai_service(claims: EEJWTClaims):
    from fastapi import HTTPException

    from core.services.ai_generation_service import (
        AIGenerationService, resolve_openai_api_key)

    api_key = resolve_openai_api_key(UUID(claims.org_id))
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OpenAI API key configured. Add an OpenAI provider key to use AI generation.",
        )
    return AIGenerationService(api_key)


@router.get("/get_all_agents")
def get_all_agents(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.list_versions(agent_id)


@router.post("/save_as_new_version", status_code=status.HTTP_201_CREATED)
def save_as_new_version(
    body: SaveAsNewVersionRequest,
    agent_id: str = Query(..., description="The agent ID to version"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    data = body.model_dump(exclude_unset=True)
    source_config_uuid = UUID(body.source_config_id) if body.source_config_id else None
    # New draft is returned alongside the agent so the response renders the
    # freshly-saved version (see core router for the full rationale).
    agent, new_config = svc.save_as_new_version(
        agent_id, data, user_id, source_config_id=source_config_uuid
    )
    return svc.agent_response(agent, config=new_config)


@router.post("/switch_active_version")
def switch_active_version(
    body: SwitchActiveVersionRequest,
    agent_id: str = Query(..., description="The agent ID to switch live version for"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    agent = svc.switch_active_version(agent_id, body.config_id)
    return svc.agent_response(agent)


@router.delete("/delete_version", status_code=status.HTTP_200_OK)
def delete_agent_version(
    agent_id: str = Query(..., description="The agent ID owning the version"),
    config_id: str = Query(..., description="The version (agent_config) ID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.delete_version(agent_id, config_id)


@router.post("/list")
def list_agents(
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    return list_agents_for_org(db, org_id, body)


@router.post("/facets")
def get_agent_facets(
    body: FacetsRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return agent_facets_for_org(db, org_id, filters)


@router.get("/filter-values")
def get_agent_filter_values(
    column_name: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    return agent_filter_values_for_org(db, org_id, column_name)


@router.post("/generate_prompt", response_model=GeneratedPromptResponse)
def generate_prompt(
    body: GeneratePromptRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
