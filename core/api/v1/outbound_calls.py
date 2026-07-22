from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
    # Optional caller-id. When omitted, the service auto-selects the org's configured
    # outbound number (single → that one; multiple → round-robin).
    from_number: Optional[str] = None
    # One or many destinations. Accepts `to_numbers` (bulk / CSV) or a single `to_number`.
    to_numbers: Optional[List[str]] = None
    to_number: Optional[str] = None
    # When set, the call(s) are queued in scheduled_calls instead of dialing now.
    scheduled_at: Optional[datetime] = None
    # Directory the created contacts land in (default the org's "Global" directory).
    directory_id: Optional[UUID] = None
    # How many of this batch's calls run at once (UI selector). None/omitted → the env default.
    max_concurrency: Optional[int] = None
    # Trigger engine: "twilio" places a real PSTN call; "websocket" bridges the call over a
    # WebSocket to a remote /ws/test (agent-to-agent, no telephony). Defaults to twilio.
    provider: Literal["twilio", "websocket"] = "twilio"

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
    service.assert_ws_trigger_allowed(claims.email, body.provider)
    return service.create_outbound_call(
        agent_id=body.agent_id,
        from_number=body.from_number,
        to_numbers=body.resolved_numbers(),
        scheduled_at=body.scheduled_at,
        created_by_user_id=service.user_id,
        directory_id=body.directory_id,
        max_concurrency=body.max_concurrency,
        provider=body.provider,
    )


@router.post("/create-from-file")
def create_outbound_call_from_file(
    agent_id: UUID = Form(...),
    from_number: Optional[str] = Form(None),
    scheduled_at: Optional[datetime] = Form(None),
    directory_id: Optional[UUID] = Form(None),
    schema_id: Optional[UUID] = Form(None),
    schedule_column: Optional[str] = Form(None),
    max_concurrency: Optional[int] = Form(None),
    provider: str = Form("twilio"),
    file: UploadFile = File(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Place/queue outbound calls from an uploaded CSV/Excel of contacts.

    Runs the shared ingestion pipeline — Parse → loop → Validate → Schedule
    (Assign → Create) — so every data source flows through the same framework:
    ``select_source_for_upload`` picks a ``ContactSource`` (CSV/Excel/…), ``RecordParser``
    loops the parsed ``ParsedContact`` stream once and validates each via a composable
    ``RecordValidator``, and the valid records are created in ``directory_id`` (default the
    org's "Global" directory), assigned to the agent, and scheduled. The client picks a
    mapping schema only to download a matching sample; the file is parsed SERVER-SIDE.

    When ``schedule_column`` is given, that file column supplies each row's OWN call time
    (parsed with the matching ``schema_id`` datetime field's format + timezone); such rows
    override the request-level ``scheduled_at`` (which becomes the fallback for rows with no
    value). A row whose schedule cell is unparseable or in the past is reported as invalid
    rather than dialed immediately."""
    from core.services.contact_ingestion import select_source_for_upload
    from core.services.contact_ingestion.pipeline import RecordParser, parsed_contact_to_row
    from core.services.contact_ingestion.validation import build_contact_validator
    from core.services.contacts.contact_schema_service import ContactSchemaService

    _get_service(claims, db).assert_ws_trigger_allowed(claims.email, provider)
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        source = select_source_for_upload(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Parse → loop → validate through the shared, extensible framework. Dialing destination
    # (Global directory, no schema) → the ONE shared builder composes a phone-required validator.
    validator = build_contact_validator(require_phone=True)
    parsed = RecordParser(validator).parse(source, raw)  # unlimited
    if not parsed.valid:
        raise HTTPException(
            status_code=400,
            detail="No valid phone numbers found in the file. Include a 'phone_number' column.",
        )

    invalid = [
        {
            "to_number": bad.get("phone_number") or f"row {bad['index'] + 1}",
            "error": "; ".join(bad.get("errors") or []),
        }
        for bad in parsed.invalid
    ]

    # Per-row schedule time: read the user-named column into metadata['scheduled_at'] using
    # the schema field's datetime format/timezone. Rows with an unparseable/past cell are
    # dropped to `invalid` (not dialed); rows with an empty cell keep the request fallback.
    usable = parsed.valid
    if schedule_column and schedule_column.strip():
        org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
        user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
        schema_service = ContactSchemaService(db, user_id=user_id, org_id=org_id)
        schedule_errors = schema_service.apply_scheduled_at_from_column(
            parsed.valid, schema_id, schedule_column
        )
        if schedule_errors:
            errored = {id(rec) for rec, _ in schedule_errors}
            usable = [rec for rec in parsed.valid if id(rec) not in errored]
            invalid += [
                {"to_number": rec.phone_number or "unknown", "error": reason}
                for rec, reason in schedule_errors
            ]
        if not usable:
            raise HTTPException(
                status_code=400,
                detail="No rows had a usable schedule time in the selected column.",
            )

    rows = [parsed_contact_to_row(record) for record in usable]

    service = _get_service(claims, db)
    return service.create_outbound_calls_from_rows(
        agent_id=agent_id,
        from_number=from_number,
        rows=rows,
        invalid=invalid,
        directory_id=directory_id,
        scheduled_at=scheduled_at,
        created_by_user_id=service.user_id,
        max_concurrency=max_concurrency,
        provider=provider,
    )


@router.get("/concurrency-max")
def get_outbound_concurrency_max(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Capabilities for the New Outbound Call modal: ``max`` — the env ceiling
    (``MAX_CONCURRENT_OUTBOUND_CALLS``) the per-batch 'Concurrent calls' selector is capped to and
    defaults to (``null`` = unset); ``ws_trigger_allowed`` — whether THIS user may use the
    WebSocket trigger (env allowlist), so the UI shows the 'Trigger via' selector accordingly."""
    return _get_service(claims, db).get_concurrency_max(caller_email=claims.email)


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
