from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.outbound_call_service import OutboundCallService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateOutboundCallRequest(BaseModel):
    agent_id: UUID
    from_number: str
    # One or many destinations. Accepts `to_numbers` (bulk / CSV) or a single `to_number`.
    to_numbers: Optional[List[str]] = None
    to_number: Optional[str] = None
    # When set, the call(s) are queued in scheduled_calls instead of dialing now.
    scheduled_at: Optional[datetime] = None

    def resolved_numbers(self) -> List[str]:
        nums = list(self.to_numbers or [])
        if self.to_number:
            nums.append(self.to_number)
        return [n for n in nums if n and n.strip()]


class ScheduledFilterParam(BaseModel):
    field: str
    operator: Optional[str] = None
    value: object


class ListScheduledCallsRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    start_date_time: Optional[str] = None
    end_date_time: Optional[str] = None
    filters: Optional[List[ScheduledFilterParam]] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class BulkCancelRequest(BaseModel):
    ids: List[UUID] = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: JWTClaims, db: Session) -> OutboundCallService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return OutboundCallService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create")
def create_outbound_call(
    body: CreateOutboundCallRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Place an outbound call now, or queue it when scheduled_at is provided.
    Immediate calls surface in Call History as a log; scheduled calls appear in
    the Scheduled Calls list."""
    service = _get_service(claims, db)
    return service.create_outbound_call(
        agent_id=body.agent_id,
        from_number=body.from_number,
        to_numbers=body.resolved_numbers(),
        scheduled_at=body.scheduled_at,
        created_by_user_id=service.user_id,
    )


@router.post("/scheduled/list")
def list_scheduled_calls(
    body: ListScheduledCallsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).list_scheduled_calls(
        page_no=body.page_no,
        page_size=body.page_size,
        filters=filters,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
        start_date_time=body.start_date_time,
        end_date_time=body.end_date_time,
    )


@router.post("/scheduled/bulk-cancel")
def bulk_cancel_scheduled_calls(
    body: BulkCancelRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Cancel multiple selected scheduled calls at once. Returns per-id outcome
    ({canceled, canceled_ids, skipped})."""
    return _get_service(claims, db).cancel_scheduled_calls(body.ids)


@router.get("/scheduled/{scheduled_call_id}")
def get_scheduled_call(
    scheduled_call_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_scheduled_call(scheduled_call_id)


@router.post("/scheduled/{scheduled_call_id}/cancel")
def cancel_scheduled_call(
    scheduled_call_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    service = _get_service(claims, db)
    service.cancel_scheduled_call(scheduled_call_id)
    return service.get_scheduled_call(scheduled_call_id)
