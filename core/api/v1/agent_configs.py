from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.agent_config_service import AgentConfigService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


@router.post("/upsert_agent_config", status_code=status.HTTP_200_OK)
def upsert_agent_config(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
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
    return AgentConfigService(db).upsert_agent_config(data)
