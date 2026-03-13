from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from core.database.session import get_db
from core.services.agent_config_service import AgentConfigService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.post("/upsert_agent_config", status_code=status.HTTP_200_OK)
def upsert_agent_config(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    if data.get("agent_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_id is required",
        )
    if not data.get("system_prompt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="system_prompt is required",
        )
    return AgentConfigService(db, org_id=UUID(claims.org_id)).upsert_agent_config(data)
