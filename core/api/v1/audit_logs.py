"""HTTP surface for the audit log (v1: agent-scope only).

Single POST list endpoint. Filters: required ``agent_id``, optional action
list, optional actor and date range, plus pagination. Gated by
``require_admin_or_owner`` since the audit trail can carry sensitive
``changes`` payloads.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner
from core.services.audit_log_service import AuditLogService
from shared.config import settings


router = APIRouter()


class ListAuditLogsRequest(BaseModel):
    agent_id: str = Field(..., description="The agent whose history to fetch")
    actions: Optional[List[str]] = Field(
        default=None,
        description=(
            "Filter to one or more action names (e.g. 'agent.tool.attached'). "
            "Omit to return every action type."
        ),
    )
    actor_user_id: Optional[str] = None
    start_date_time: Optional[datetime] = None
    end_date_time: Optional[datetime] = None
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=AuditLogService.DEFAULT_PAGE_SIZE,
        ge=1,
        le=AuditLogService.MAX_PAGE_SIZE,
    )


def _get_service(claims: JWTClaims, db: Session) -> AuditLogService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return AuditLogService(db, user_id=user_id, org_id=org_id)


def _parse_uuid(value: str, field: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}",
        )


@router.post("/list")
def list_audit_logs(
    body: ListAuditLogsRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    agent_uuid = _parse_uuid(body.agent_id, "agent_id")
    actor_uuid = _parse_uuid(body.actor_user_id, "actor_user_id") if body.actor_user_id else None

    return _get_service(claims, db).list(
        agent_id=agent_uuid,
        actions=body.actions,
        actor_user_id=actor_uuid,
        start_date_time=body.start_date_time,
        end_date_time=body.end_date_time,
        page_no=body.page_no,
        page_size=body.page_size,
    )
