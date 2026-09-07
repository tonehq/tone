"""Thin route layer for the Model Providers page. Business logic lives in
``core/services/model_provider_service.py`` so the EE edition can share it
without copy-paste drift."""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.api.v1.faceted_schemas import FacetsRequest
from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.model_provider_service import ModelProviderService
from shared.config import settings

router = APIRouter()


# ─── request schemas ───────────────────────────────────────────────────────
# Shared by ``core`` and ``ee`` — ee/api/v1/services.py imports these so the
# two editions can't drift on the wire contract.


class CreateModelProviderRequest(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    meta_data_schema: Optional[Dict[str, Any]] = None


class UpdateModelProviderRequest(BaseModel):
    provider_id: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    meta_data_schema: Optional[Dict[str, Any]] = None


class ListModelProvidersRequest(BaseModel):
    page: int = 1
    page_size: int = 20
    search: Optional[str] = None
    sort_by: Optional[str] = None
    is_active: Optional[bool] = None


def _resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


def _service(claims: JWTClaims, db: Session) -> ModelProviderService:
    return ModelProviderService(db, org_id=_resolve_org_id(claims))


# ─── aggregated list + single-key CRUD ─────────────────────────────────────


@router.post("/list")
def list_services(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_services(body)


@router.post("/facets")
def get_service_facets(
    body: FacetsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _service(claims, db).get_service_facets(filters)


@router.get("/filter-values")
def get_service_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_service_filter_values(column_name)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_service(
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).create_service(body)


@router.get("/{service_id}")
def get_service(
    service_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_service(service_id)


@router.patch("/{service_id}")
def update_service(
    service_id: str,
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).update_service(service_id, body)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_200_OK)
def delete_provider_services(
    provider_id: str,
    service_type: str | None = None,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_provider_services(
        provider_id, service_type=service_type
    )


@router.delete("/{service_id}", status_code=status.HTTP_200_OK)
def delete_service(
    service_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_service(service_id)


# ─── catalog ───────────────────────────────────────────────────────────────


@router.get("/providers/catalog")
def list_providers_catalog(
    service_type: Optional[str] = Query(
        None,
        description=(
            "Optional 'llm' | 'stt' | 'tts'. When set, restricts the catalog to "
            "providers the current org has an active ApiKey for in that kind."
        ),
    ),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_providers_catalog(service_type=service_type)


# ─── flat models list (all providers) ───────────────────────────────────────
# One row per catalog Model, joined to the org's API-key presence. Reads only,
# so any org member may list/filter.


@router.post("/models/list")
def list_models(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_models(body)


@router.post("/models/facets")
def get_model_facets(
    body: FacetsRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    filters = [f.model_dump() for f in body.filters] if body.filters else None
    return _service(claims, db).get_model_facets(filters)


@router.get("/models/filter-values")
def get_model_filter_values(
    column_name: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_model_filter_values(column_name)


# ─── provider CRUD (admin) ─────────────────────────────────────────────────
# `model_providers` is a global catalog shared across every tenant. Writes are
# admin-gated so one org member can't rename or remove a definition that other
# orgs depend on. Reads (get + admin list) stay authenticated but not
# admin-gated where the UI needs them.


@router.post("/providers/list_providers")
def list_providers(
    body: ListModelProvidersRequest = Body(default_factory=ListModelProvidersRequest),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_providers(body.model_dump(exclude_none=True))


@router.post("/providers/create_provider", status_code=status.HTTP_201_CREATED)
def create_provider(
    body: CreateModelProviderRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    provider = svc.create_provider(body.model_dump(exclude_none=True))
    return svc.provider_response(provider)


@router.get("/providers/get_provider/{provider_id}")
def get_provider(
    provider_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    provider = svc.get_provider(provider_id)
    return svc.provider_response(provider)


@router.put(
    "/providers/update_provider/{provider_id}", status_code=status.HTTP_200_OK
)
def update_provider(
    provider_id: str,
    body: UpdateModelProviderRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    provider = svc.update_provider(
        provider_id, body.model_dump(exclude_unset=True)
    )
    return svc.provider_response(provider)


@router.delete(
    "/providers/delete_provider/{provider_id}", status_code=status.HTTP_200_OK
)
def delete_provider(
    provider_id: str,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_provider(provider_id)


# ─── per-provider drill-down ───────────────────────────────────────────────


@router.post("/providers/{provider_id}/keys")
def list_provider_keys(
    provider_id: str,
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_provider_keys(provider_id, body)


@router.get("/providers/{provider_id}/keys/filter-values")
def get_provider_key_filter_values(
    provider_id: str,
    column_name: str = Query(...),
    service_type: Optional[str] = None,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_provider_key_filter_values(
        provider_id, column_name, service_type
    )


@router.post("/providers/{provider_id}/models")
def list_provider_models(
    provider_id: str,
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_provider_models(provider_id, body)


@router.get("/providers/{provider_id}/models/filter-values")
def get_provider_model_filter_values(
    provider_id: str,
    column_name: str = Query(...),
    service_type: Optional[str] = None,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_provider_model_filter_values(
        provider_id, column_name, service_type
    )


# The `models` table is a global catalog (no organization_id) referenced by
# agent_configs across tenants. Writes are admin-gated so a single org member
# can't rename/delete a row that other orgs depend on. Reads stay open to any
# org member so they can pick a model in their agent forms.


@router.post(
    "/providers/{provider_id}/models/create",
    status_code=status.HTTP_201_CREATED,
)
def create_provider_model(
    provider_id: str,
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).create_provider_model(provider_id, body)


@router.patch("/providers/{provider_id}/models/{model_id}")
def update_provider_model(
    provider_id: str,
    model_id: str,
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).update_provider_model(provider_id, model_id, body)


@router.delete(
    "/providers/{provider_id}/models/{model_id}",
    status_code=status.HTTP_200_OK,
)
def delete_provider_model(
    provider_id: str,
    model_id: str,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_provider_model(provider_id, model_id)


# ─── TTS cascade (language → provider → voice) ───────────────────────────


@router.get("/tts/languages")
def list_tts_languages(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_tts_languages()


@router.get("/tts/providers")
def list_tts_providers(
    language: str = Query(..., description="Language name to filter TTS providers"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_tts_providers(language)


@router.get("/tts/voices")
def list_tts_voices(
    provider_id: str = Query(..., description="Provider ID to fetch voices for"),
    language: str = Query(..., description="Language name to filter voices"),
    model_id: Optional[str] = Query(None, description="Model ID to filter voices by"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_tts_voices(provider_id, language, model_id=model_id)
