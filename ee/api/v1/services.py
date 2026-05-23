"""EE edition routes for the Model Providers page — thin wrappers over the
shared ``ModelProviderService``. The only difference from the core edition is
the auth dependency."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.services.model_provider_service import ModelProviderService
from ee.middleware.auth import (
    EEJWTClaims,
    require_ee_admin_or_owner,
    require_ee_org_member,
)

router = APIRouter()


def _service(claims: EEJWTClaims, db: Session) -> ModelProviderService:
    return ModelProviderService(db, org_id=UUID(claims.org_id))


# ─── aggregated list + single-key CRUD ─────────────────────────────────────


@router.post("/list")
def list_services(
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_services(body)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_service(
    body: dict = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).create_service(body)


@router.get("/{service_id}")
def get_service(
    service_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).get_service(service_id)


@router.patch("/{service_id}")
def update_service(
    service_id: str,
    body: dict = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).update_service(service_id, body)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_200_OK)
def delete_provider_services(
    provider_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_provider_services(provider_id)


@router.delete("/{service_id}", status_code=status.HTTP_200_OK)
def delete_service(
    service_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_service(service_id)


# ─── catalog ───────────────────────────────────────────────────────────────


@router.get("/providers/catalog")
def list_providers_catalog(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_providers_catalog()


# ─── per-provider drill-down ───────────────────────────────────────────────


@router.post("/providers/{provider_id}/keys")
def list_provider_keys(
    provider_id: str,
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_provider_keys(provider_id, body)


@router.post("/providers/{provider_id}/models")
def list_provider_models(
    provider_id: str,
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).create_provider_model(provider_id, body)


@router.patch("/providers/{provider_id}/models/{model_id}")
def update_provider_model(
    provider_id: str,
    model_id: str,
    body: dict = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
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
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_provider_model(provider_id, model_id)
