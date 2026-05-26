from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.api.v1.agents import (
    CreateAgentRequest,
    UpdateAgentRequest,
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
