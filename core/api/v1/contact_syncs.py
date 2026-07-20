"""Contact syncs router — datasource-driven imports into a directory.

Endpoints (all ``require_org_member`` — any member can run a sync):
- ``POST /contact-syncs`` (multipart): create + enqueue a sync from an uploaded CSV.
- ``POST /contact-syncs/list``: paginated list of syncs (optionally by directory).
- ``GET  /contact-syncs/{id}``: one sync's status/counts (incl. ``row_errors``).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.contacts.contact_sync_service import ContactSyncService
from shared.config import settings

router = APIRouter()


class ListContactSyncsRequest(BaseModel):
    directory_id: Optional[UUID] = None
    status: Optional[str] = Field(default=None, pattern="^(pending|processing|completed|failed)$")
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


def _resolve_ids(claims: JWTClaims):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return org_id, user_id


def _sync_service(claims: JWTClaims, db: Session) -> ContactSyncService:
    org_id, user_id = _resolve_ids(claims)
    return ContactSyncService(db, user_id=user_id, org_id=org_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contact_sync(
    directory_id: UUID = Form(...),
    schema_id: UUID = Form(...),
    agent_id: Optional[UUID] = Form(None),
    file: UploadFile = File(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Store the uploaded CSV, insert a pending sync, and enqueue its parse job.

    Returns the sync immediately (``status="pending"``); the client polls
    ``GET /contact-syncs/{id}`` while the worker imports.
    """
    sync = _sync_service(claims, db).create_contact_sync(
        directory_id=directory_id,
        schema_id=schema_id,
        agent_id=agent_id,
        file=file,
    )
    return sync.to_dict()


@router.post("/list")
def list_contact_syncs(
    body: ListContactSyncsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _sync_service(claims, db).list_contact_syncs(
        directory_id=body.directory_id,
        status=body.status,
        page_no=body.page_no,
        page_size=body.page_size,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/{sync_id}")
def get_contact_sync(
    sync_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _sync_service(claims, db).get_contact_sync(sync_id).to_dict()
