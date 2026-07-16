from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.api.v1.call_logs import FacetsRequest, ListCallsRequest, MetricsSummaryRequest
from core.database.session import get_db
from core.services.call_metrics_analytics_service import CallMetricsAnalyticsService
from core.services.call_service import CallService
from core.services.tool_execution_service import ToolExecutionService
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: EEJWTClaims, db: Session) -> CallService:
    return CallService(db, org_id=UUID(claims.org_id))


def _get_analytics_service(claims: EEJWTClaims, db: Session) -> CallMetricsAnalyticsService:
    return CallMetricsAnalyticsService(db, org_id=UUID(claims.org_id))


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


@router.post("/facets")
def get_facets(
    body: FacetsRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_service(claims, db).get_facets(
        start_date_time=body.start_date_time,
        end_date_time=body.end_date_time,
        filters=filters,
    )


@router.post("/metrics-summary")
def get_metrics_summary(
    body: MetricsSummaryRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _get_analytics_service(claims, db).summarize(
        start_date_time=body.start_date_time,
        end_date_time=body.end_date_time,
        filters=filters,
    )


@router.get("/{call_id}/audio-url")
def get_audio_url(
    call_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_audio_url(call_id=call_id)


@router.get("/{call_id}/tool-executions")
def get_call_tool_executions(
    call_id: str,
    status: Optional[str] = Query(None, description="Filter by status: success | error"),
    tool_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by tool type: custom | send_sms | google_calendar | read_document | mcp",
    ),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ToolExecutionService(db, org_id=UUID(claims.org_id)).list_for_call(
        call_id=call_id,
        status=status,
        tool_type=tool_type,
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
