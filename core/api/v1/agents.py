from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from core.database.session import get_db
from core.services.agent_service import AgentService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


@router.get("/get_all_agents", response_model=List[Dict[str, Any]])
def get_all_agents(
    agent_id: Optional[int] = Query(None, description="If provided, return only this agent"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return all agents with joined agent_config and service_providers (llm, tts, stt). If agent_id is given, return only that agent."""
    return AgentService(db).get_all_agents(agent_id=agent_id)


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
    return AgentService(db).upsert_agent(data, created_by=claims.user_id)
