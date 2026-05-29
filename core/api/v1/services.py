"""Thin route layer for the Model Providers page. Business logic lives in
``core/services/model_provider_service.py`` so the EE edition can share it
without copy-paste drift."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.model_provider_service import ModelProviderService
from shared.config import settings

router = APIRouter()


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
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_providers_catalog()


# ─── per-provider drill-down ───────────────────────────────────────────────


@router.post("/providers/{provider_id}/keys")
def list_provider_keys(
    provider_id: str,
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_provider_keys(provider_id, body)


@router.post("/providers/{provider_id}/models")
def list_provider_models(
    provider_id: str,
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_provider_models(provider_id, body)


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
