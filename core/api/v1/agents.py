from uuid import UUID

from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from core.database.session import get_db
from core.services.agent_service import AgentService
from core.middleware.auth import require_org_member, JWTClaims
from shared.config import settings

router = APIRouter()


@router.get("/get_all_agents", response_model=List[Dict[str, Any]])
def get_all_agents(
    agent_id: Optional[int] = Query(None, description="If provided, return only this agent"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return all agents with joined agent_config and service_providers (llm, tts, stt). If agent_id is given, return only that agent."""
    return AgentService(db).get_all_agents(agent_id=agent_id, created_by=claims.user_id)


@router.get("/get_agent", response_model=Dict[str, Any])
def get_agent(
    agent_id: int = Query(..., description="The agent ID to fetch"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    results = AgentService(db).get_all_agents(agent_id=agent_id, created_by=claims.user_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return results[0]


@router.delete("/delete_agent", status_code=status.HTTP_200_OK)
def delete_agent(
    agent_id: int = Query(..., description="The agent ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return AgentService(db).delete_agent(agent_id)


@router.post("/duplicate_agent", status_code=status.HTTP_200_OK)
def duplicate_agent(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    agent_id = data.get("agent_id")
    name = data.get("name")
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_id is required",
        )
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return AgentService(db, org_id=org_id).duplicate_agent(
        agent_id=int(agent_id),
        new_name=name,
        created_by=claims.user_id,
    )


@router.post("/upsert_agent", status_code=status.HTTP_200_OK)
def upsert_agent(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    name = data.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return AgentService(db, org_id=org_id).upsert_agent(data, created_by=claims.user_id)
