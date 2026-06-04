from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.call_metrics_service import CallMetricsService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request schemas
# ---------------------------------------------------------------------------

class CallMetricsFilterParam(BaseModel):
    field: str
    operator: str
    value: object


class ListCallMetricsRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    start_date_time: Optional[str] = None
    end_date_time: Optional[str] = None
    filters: Optional[List[CallMetricsFilterParam]] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: JWTClaims, db: Session) -> CallMetricsService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return CallMetricsService(db, org_id=org_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/list")
def list_call_metrics(
    body: ListCallMetricsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).list_metrics(
        page_no=body.page_no,
        page_size=body.page_size,
        start_date_time=body.start_date_time,
        end_date_time=body.end_date_time,
        filters=filters,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/{call_id}")
def get_metrics_for_call(
    call_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    result = _get_service(claims, db).get_by_call_id(call_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Metrics not found for this call")
    return result
