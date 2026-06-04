from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.api.v1.call_metrics import ListCallMetricsRequest
from core.database.session import get_db
from core.services.call_metrics_service import CallMetricsService
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


def _get_service(claims: EEJWTClaims, db: Session) -> CallMetricsService:
    return CallMetricsService(db, org_id=UUID(claims.org_id))


@router.post("/list")
def list_call_metrics(
    body: ListCallMetricsRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    result = _get_service(claims, db).get_by_call_id(call_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Metrics not found for this call")
    return result
