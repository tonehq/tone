"""Contact Datasources router — CRUD over the CSV datasources that feed directories.

Create/delete require admin/owner; list requires any org member. CSV-only at launch.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.contacts.contact_datasource_service import ContactDatasourceService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateDatasourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    directory_id: Optional[UUID] = None
    type: str = Field(default="csv")
    config: Optional[Dict[str, Any]] = None


class ListDatasourcesRequest(BaseModel):
    directory_id: Optional[UUID] = None
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _service(claims: JWTClaims, db: Session) -> ContactDatasourceService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return ContactDatasourceService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
def create_datasource(
    body: CreateDatasourceRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    datasource = _service(claims, db).create_datasource(
        name=body.name,
        directory_id=body.directory_id,
        type=body.type,
        config=body.config,
    )
    return datasource.to_dict()


@router.post("/list")
def list_datasources(
    body: ListDatasourcesRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_datasources(
        directory_id=body.directory_id,
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.delete("/{datasource_id}")
def delete_datasource(
    datasource_id: UUID,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    _service(claims, db).delete_datasource(datasource_id)
    return {"ok": True}
