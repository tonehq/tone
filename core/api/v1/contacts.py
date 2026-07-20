"""Contacts router — directory-scoped contact CRUD + schedule-calls.

Every contact lives inside a ``ContactDirectory``; the list/create/bulk-delete routes are
nested under ``/contact-directories/{directory_id}``, while single-contact update/delete
address the contact by id (the service still org- + directory-scopes the lookup, so no
IDOR). All handlers are org-scoped via ``require_org_member``.

Multi-add is PARTIAL: ``POST /contact-directories/{id}/contacts`` returns
``{"created": [...], "failed": [{index, errors}]}`` (see C-7) for both single- and
multi-row bodies. The standalone ``POST /schedule-calls`` (delegating to
``OutboundCallService``) is kept unchanged.

Upload/import and schema/field endpoints have moved out (to the sync + schema services).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.contacts.contact_service import ContactService
from core.services.outbound_call_service import OutboundCallService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ListContactsRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class ContactRow(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    external_id: Optional[str] = None
    contact_metadata: Optional[Dict[str, Any]] = None


class CreateContactsRequest(BaseModel):
    """Single- or multi-row create. Exactly one of ``contact`` / ``contacts`` is used;
    both shapes normalise to a list so the response is always ``{created, failed}``."""

    contact: Optional[ContactRow] = None
    contacts: Optional[List[ContactRow]] = Field(default=None, max_length=1000)
    # Optional agent assignment: when set, the created contacts are also assigned to this
    # agent (idempotent) in the same request. When omitted the contacts are just created.
    agent_id: Optional[UUID] = None

    def as_rows(self) -> List[Dict[str, Any]]:
        rows = self.contacts if self.contacts is not None else (
            [self.contact] if self.contact is not None else []
        )
        return [r.model_dump() for r in rows]


class UpdateContactRequest(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    contact_metadata: Optional[Dict[str, Any]] = None


class BulkDeleteContactsRequest(BaseModel):
    ids: List[UUID] = Field(min_length=1, max_length=500)


class ScheduleContactCallsRequest(BaseModel):
    agent_id: UUID
    from_number: str
    contact_ids: List[UUID] = Field(min_length=1, max_length=500)
    scheduled_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Service helpers
# ---------------------------------------------------------------------------

def _resolve_ids(claims: JWTClaims):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return org_id, user_id


def _contact_service(claims: JWTClaims, db: Session) -> ContactService:
    org_id, user_id = _resolve_ids(claims)
    return ContactService(db, user_id=user_id, org_id=org_id)


def _outbound_service(claims: JWTClaims, db: Session) -> OutboundCallService:
    org_id, user_id = _resolve_ids(claims)
    return OutboundCallService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Directory-scoped contact CRUD
# ---------------------------------------------------------------------------

@router.post("/contact-directories/{directory_id}/contacts/list")
def list_contacts(
    directory_id: UUID,
    body: ListContactsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _contact_service(claims, db).list_contacts(
        directory_id,
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.post("/contact-directories/{directory_id}/contacts", status_code=status.HTTP_201_CREATED)
def create_contacts(
    directory_id: UUID,
    body: CreateContactsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create one or many contacts (partial success). Returns
    ``{"created": [...], "failed": [{index, errors}]}`` (C-7).

    When ``agent_id`` is provided, the freshly-created contacts are ALSO assigned to that
    agent in the same request (idempotent — reuses ``AgentContactService`` so the
    directory General view and the agent Contacts tab share one create endpoint).
    """
    return _contact_service(claims, db).create_contacts(
        directory_id, body.as_rows(), agent_id=body.agent_id
    )


@router.patch("/contacts/{contact_id}")
def update_contact(
    contact_id: UUID,
    body: UpdateContactRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    contact = _contact_service(claims, db).update_contact(
        contact_id,
        name=body.name,
        phone_number=body.phone_number,
        contact_metadata=body.contact_metadata,
    )
    return contact.to_dict()


@router.delete("/contacts/{contact_id}")
def delete_contact(
    contact_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    _contact_service(claims, db).delete_contact(contact_id)
    return {"ok": True}


@router.post("/contact-directories/{directory_id}/contacts/bulk-delete")
def bulk_delete_contacts(
    directory_id: UUID,
    body: BulkDeleteContactsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _contact_service(claims, db).bulk_delete_contacts(directory_id, body.ids)


# ---------------------------------------------------------------------------
# Scheduling (unchanged)
# ---------------------------------------------------------------------------

@router.post("/contact/schedule-calls")
def schedule_contact_calls(
    body: ScheduleContactCallsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Schedule outbound calls to the selected contacts. Reuses OutboundCallService's
    agent/from-number validation and the ``scheduled_calls`` infrastructure; each row
    carries its ``contact_id`` and per-contact schedule time."""
    service = _outbound_service(claims, db)
    return service.schedule_calls_for_contacts(
        agent_id=body.agent_id,
        from_number=body.from_number,
        contact_ids=body.contact_ids,
        scheduled_at=body.scheduled_at,
        created_by_user_id=service.user_id,
    )
