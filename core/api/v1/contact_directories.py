"""Contact Directories router — CRUD over user-created directories.

Writes (create/update/delete/delete-impact) require admin/owner; reads (get/list)
require any org member. All handlers are org-scoped via the service layer (no IDOR).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.contacts.contact_directory_service import ContactDirectoryService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateDirectoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    # Optional: point the new directory at an existing org schema as its default.
    # Omitted → no default schema (no schema is auto-created per directory).
    default_schema_id: Optional[UUID] = None


class UpdateDirectoryRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    default_schema_id: Optional[UUID] = None


class ListDirectoriesRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _service(claims: JWTClaims, db: Session) -> ContactDirectoryService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return ContactDirectoryService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
def create_directory(
    body: CreateDirectoryRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    directory = _service(claims, db).create_directory(
        name=body.name,
        description=body.description,
        default_schema_id=body.default_schema_id,
    )
    return directory.to_dict()


@router.post("/list")
def list_directories(
    body: ListDirectoriesRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_directories(
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/{directory_id}")
def get_directory(
    directory_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_directory(directory_id).to_dict()


@router.patch("/{directory_id}")
def update_directory(
    directory_id: UUID,
    body: UpdateDirectoryRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    directory = _service(claims, db).update_directory(
        directory_id,
        **body.model_dump(exclude_unset=True),
    )
    return directory.to_dict()


@router.get("/{directory_id}/delete-impact")
def directory_delete_impact(
    directory_id: UUID,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_impact(directory_id)


@router.delete("/{directory_id}")
def delete_directory(
    directory_id: UUID,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_directory(directory_id)
