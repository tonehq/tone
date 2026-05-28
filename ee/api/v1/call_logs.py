from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.api.v1.call_logs import ListCallsRequest
from core.database.session import get_db
from core.services.call_service import CallService
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: EEJWTClaims, db: Session) -> CallService:
    return CallService(db, org_id=UUID(claims.org_id))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/filter-values")
def get_filter_values(
    column_name: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_filter_values(column_name=column_name)


@router.post("/list")
def get_calls(
    body: ListCallsRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
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


@router.get("/{call_id}")
def get_call_by_id(
    call_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    result = _get_service(claims, db).get_call_by_id(call_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call not found")
    return result
