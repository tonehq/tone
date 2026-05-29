from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import UUID

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.call_service import CallService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request schemas
# ---------------------------------------------------------------------------

class CallFilterParam(BaseModel):
    field: str
    operator: str
    value: object


class ListCallsRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    start_date_time: Optional[str] = None
    end_date_time: Optional[str] = None
    filters: Optional[List[CallFilterParam]] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: JWTClaims, db: Session) -> CallService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return CallService(db, org_id=org_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/filter-values")
def get_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_filter_values(column_name=column_name)


@router.post("/list")
def get_calls(
    body: ListCallsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).get_calls(
        page_no=body.page_no,
        page_size=body.page_size,
        start_date_time=body.start_date_time,
        end_date_time=body.end_date_time,
        filters=filters,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/{call_id}/audio-url")
def get_audio_url(
    call_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_audio_url(call_id=call_id)


@router.get("/{call_id}")
def get_call_by_id(
    call_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    result = _get_service(claims, db).get_call_by_id(call_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call not found")
    return result
