"""Ingestion configs router — org-level, reusable ``IngestionConfig`` CRUD.

Recipes bundle a parser / tokeniser / embedder / vector store; the user
picks one when kicking off ``POST /knowledge-base/{upload_id}/runs``. The
run row still snapshots every field, so a config can be renamed, edited or
soft-deleted without affecting historical runs.

Guards: writes = admin/owner (``require_admin_or_owner``),
reads = member (``require_org_member``). Every handler is org-scoped inside
the service.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.ingestion_config_service import IngestionConfigService
from shared.config import settings

router = APIRouter(prefix="/ingestion-configs", tags=["ingestion-config"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CreateIngestionConfigRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    parser: str = Field(min_length=1, max_length=50)
    parser_config: Optional[Dict[str, Any]] = None
    tokeniser: str = Field(min_length=1, max_length=50)
    tokeniser_config: Optional[Dict[str, Any]] = None
    embedding_provider: str = Field(min_length=1, max_length=50)
    embedding_model: str = Field(min_length=1, max_length=120)
    embedding_dimensions: int = Field(gt=0)
    embedding_version: Optional[str] = Field(default=None, max_length=50)
    embedding_config: Optional[Dict[str, Any]] = None
    vector_store: str = Field(min_length=1, max_length=32)
    vector_store_ref: Optional[Dict[str, Any]] = None
    is_active: bool = True


class UpdateIngestionConfigRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    parser: Optional[str] = Field(default=None, min_length=1, max_length=50)
    parser_config: Optional[Dict[str, Any]] = None
    tokeniser: Optional[str] = Field(default=None, min_length=1, max_length=50)
    tokeniser_config: Optional[Dict[str, Any]] = None
    embedding_provider: Optional[str] = Field(
        default=None, min_length=1, max_length=50
    )
    embedding_model: Optional[str] = Field(default=None, min_length=1, max_length=120)
    embedding_dimensions: Optional[int] = Field(default=None, gt=0)
    embedding_version: Optional[str] = Field(default=None, max_length=50)
    embedding_config: Optional[Dict[str, Any]] = None
    vector_store: Optional[str] = Field(default=None, min_length=1, max_length=32)
    vector_store_ref: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ListIngestionConfigsRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    # Ceiling is 200 so the run modal can fetch every active config in one
    # page for the picker dropdown (matches the shared
    # apply_search_sort_pagination clamp of 200). Ordinary paginated tables
    # still use the default of 20.
    page_size: int = Field(default=20, ge=1, le=200)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    is_active_only: bool = False


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------


def _get_service(claims: JWTClaims, db: Session) -> IngestionConfigService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return IngestionConfigService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.post("/create_ingestion_config", status_code=status.HTTP_201_CREATED)
def create_ingestion_config(
    body: CreateIngestionConfigRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    row = svc.create_config(**body.model_dump())
    return svc.config_response(row)


@router.put("/update_ingestion_config/{config_id}", status_code=status.HTTP_200_OK)
def update_ingestion_config(
    config_id: UUID,
    body: UpdateIngestionConfigRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    row = svc.update_config(config_id, **body.model_dump(exclude_unset=True))
    return svc.config_response(row)


@router.post("/list")
def list_ingestion_configs(
    body: ListIngestionConfigsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_configs(
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
        is_active_only=body.is_active_only,
    )


@router.get("/{config_id}")
def get_ingestion_config(
    config_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.config_response(svc.get_config(config_id))


@router.delete("/{config_id}")
def delete_ingestion_config(
    config_id: UUID,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_config(config_id)
