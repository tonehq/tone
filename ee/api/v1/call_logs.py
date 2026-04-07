from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID

from core.database.session import get_db
from core.services.call_log_service import CallLogService
from core.utils.storage import generate_presigned_url
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.get("/filter-values")
def get_filter_values(
    column_name: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return CallLogService(db, org_id=UUID(claims.org_id)).get_filter_values(column_name=column_name)


@router.post("/list")
def get_call_logs(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return CallLogService(db, org_id=UUID(claims.org_id)).get_call_logs(
        page_no=data.get("page_no", 1),
        page_size=data.get("page_size", 10),
        start_date_time=data.get("start_date_time"),
        end_date_time=data.get("end_date_time"),
        filters=data.get("filters"),
        sort_by=data.get("sort_by"),
        sort_order=data.get("sort_order", "desc"),
    )


@router.get("/{call_id}")
def get_call_log_by_id(
    call_id: int,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    result = CallLogService(db, org_id=UUID(claims.org_id)).get_call_log_by_id(call_log_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call log not found")
    return result


@router.get("/{call_id}/audio-url")
def get_audio_url(
    call_id: int,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    result = CallLogService(db, org_id=UUID(claims.org_id)).get_call_log_by_id(call_log_id=call_id)
    if not result:
        raise HTTPException(status_code=404, detail="Call log not found")

    audio_path = result.get("audio_file_path")
    if not audio_path:
        raise HTTPException(status_code=404, detail="No audio recording for this call")

    url = generate_presigned_url(audio_path)
    return {"url": url}
