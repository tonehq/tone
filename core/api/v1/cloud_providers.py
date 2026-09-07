"""Thin route layer for the Cloud Providers catalog. Business logic lives in
``core/services/cloud_provider_service.py`` so the EE edition can share it
without copy-paste drift.

``cloud_providers`` is a global catalog shared across every tenant. Writes are
admin-gated so one org member can't rename or remove a definition other orgs
depend on; reads stay authenticated (org member) where the UI needs them."""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.cloud_provider_service import CloudProviderService
from shared.config import settings

router = APIRouter()


# ─── request schemas ───────────────────────────────────────────────────────
# Shared by ``core`` and ``ee`` — ee/api/v1/cloud_providers.py imports these so
# the two editions can't drift on the wire contract.


class CreateCloudProviderRequest(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    meta_data_schema: Optional[Dict[str, Any]] = None


class UpdateCloudProviderRequest(BaseModel):
    provider_id: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    meta_data_schema: Optional[Dict[str, Any]] = None


class ListCloudProvidersRequest(BaseModel):
    page: int = 1
    page_size: int = 20
    search: Optional[str] = None
    sort_by: Optional[str] = None
    is_active: Optional[bool] = None


def _resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


def _service(claims: JWTClaims, db: Session) -> CloudProviderService:
    return CloudProviderService(db, org_id=_resolve_org_id(claims))


@router.post("/list")
def list_cloud_providers(
    body: ListCloudProvidersRequest = Body(default_factory=ListCloudProvidersRequest),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_cloud_providers(body.model_dump(exclude_none=True))


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_cloud_provider(
    body: CreateCloudProviderRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    record = svc.create_cloud_provider(body.model_dump(exclude_none=True))
    return svc.cloud_provider_response(record)


@router.get("/{cloud_provider_id}")
def get_cloud_provider(
    cloud_provider_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    return svc.cloud_provider_response(svc.get_cloud_provider(cloud_provider_id))


@router.put("/{cloud_provider_id}", status_code=status.HTTP_200_OK)
def update_cloud_provider(
    cloud_provider_id: str,
    body: UpdateCloudProviderRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    record = svc.update_cloud_provider(
        cloud_provider_id, body.model_dump(exclude_unset=True)
    )
    return svc.cloud_provider_response(record)


@router.delete("/{cloud_provider_id}", status_code=status.HTTP_200_OK)
def delete_cloud_provider(
    cloud_provider_id: str,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_cloud_provider(cloud_provider_id)
