from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.api.v1.agents import (
    CreateAgentRequest,
    GeneratePromptRequest,
    GeneratedPromptResponse,
    ImprovePromptRequest,
    UpdateAgentRequest,
    _prompt_errors,
    list_agents_for_org,
)
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    agent = svc.get_agent(agent_id)
    return svc.agent_response(agent)


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


@router.post("/list")
def list_agents(
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    return list_agents_for_org(db, org_id, body)


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
