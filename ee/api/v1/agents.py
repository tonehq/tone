from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from uuid import UUID

from core.database.session import get_db
from core.services.agent_service import AgentService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.get("/get_all_agents", response_model=List[Dict[str, Any]])
def get_all_agents(
    agent_id: Optional[int] = Query(None, description="If provided, return only this agent"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return AgentService(db, org_id=UUID(claims.org_id)).get_all_agents(agent_id=agent_id, created_by=claims.user_id)


@router.get("/get_agent", response_model=Dict[str, Any])
def get_agent(
    agent_id: int = Query(..., description="The agent ID to fetch"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    results = AgentService(db, org_id=UUID(claims.org_id)).get_all_agents(agent_id=agent_id, created_by=claims.user_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return results[0]


@router.delete("/delete_agent", status_code=status.HTTP_200_OK)
def delete_agent(
    agent_id: int = Query(..., description="The agent ID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return AgentService(db, org_id=UUID(claims.org_id)).delete_agent(agent_id)


@router.post("/upsert_agent", status_code=status.HTTP_200_OK)
def upsert_agent(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    name = data.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    return AgentService(db, org_id=UUID(claims.org_id)).upsert_agent(data, created_by=claims.user_id)
