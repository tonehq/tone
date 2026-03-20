import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.call_log_service import CallLogService

router = APIRouter()


@router.get("/list")
def get_call_logs(
    page_no: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    start_date_time: Optional[int] = Query(None),
    end_date_time: Optional[int] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    filters: Optional[str] = Query(None),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    parsed_filters = None
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filters format. Must be a JSON array.",
            )

    return CallLogService(db).get_call_logs(
        page_no=page_no,
        page_size=page_size,
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        filters=parsed_filters,
        sort_by=sort_by,
        sort_order=sort_order or "desc",
    )
