from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.api.v1.call_logs import FacetsRequest, ListCallsRequest, MetricsSummaryRequest
from core.database.session import get_db
from core.services.call_metrics_analytics_service import CallMetricsAnalyticsService
from core.services.call_service import CallService
from core.services.loki_client import LokiError
from core.services.pipeline_log_sync_service import (
    PipelineLogSyncService,
    sync_result_payload,
)
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


def _parse_call_id(call_id: str) -> UUID:
    try:
        return UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid call_id")


@router.post("/{call_id}/sync-logs", status_code=status.HTTP_200_OK)
def sync_call_logs(
    call_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Read this call's log lines back from Loki into ``call_pipeline_logs`` (inline).
    Idempotent — see the OSS twin in ``core/api/v1/call_logs.py``."""
    svc = PipelineLogSyncService(db, org_id=UUID(claims.org_id))
    try:
        result = svc.sync_call_by_id(_parse_call_id(call_id))
    except LokiError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Loki query failed: {exc}")
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    return sync_result_payload(result)


@router.get("/{call_id}/logs")
def list_call_logs(
    call_id: str,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None, description="Filter by log level, e.g. ERROR"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Per-call log viewer feed, org-scoped. See the OSS twin for details."""
    return PipelineLogSyncService(db, org_id=UUID(claims.org_id)).list_for_call(
        _parse_call_id(call_id), limit=limit, offset=offset, level=level
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
