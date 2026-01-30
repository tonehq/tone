from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.agent_service import AgentService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


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
