"""EE edition routes for the Cloud Providers catalog — thin wrappers over the
shared ``CloudProviderService``. The only difference from the core edition is
the auth dependency; the request schemas are imported from core so the two
editions can't drift on the wire contract."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from core.api.v1.cloud_providers import (
    CreateCloudProviderRequest,
    ListCloudProvidersRequest,
    UpdateCloudProviderRequest,
)
from core.database.session import get_db
from core.services.cloud_provider_service import CloudProviderService
from ee.middleware.auth import (
    EEJWTClaims,
    require_ee_admin_or_owner,
    require_ee_org_member,
)

router = APIRouter()


def _service(claims: EEJWTClaims, db: Session) -> CloudProviderService:
    return CloudProviderService(db, org_id=UUID(claims.org_id))


@router.post("/list")
def list_cloud_providers(
    body: ListCloudProvidersRequest = Body(default_factory=ListCloudProvidersRequest),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _service(claims, db).list_cloud_providers(body.model_dump(exclude_none=True))


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_cloud_provider(
    body: CreateCloudProviderRequest,
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    record = svc.create_cloud_provider(body.model_dump(exclude_none=True))
    return svc.cloud_provider_response(record)


@router.get("/{cloud_provider_id}")
def get_cloud_provider(
    cloud_provider_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _service(claims, db)
    return svc.cloud_provider_response(svc.get_cloud_provider(cloud_provider_id))


@router.put("/{cloud_provider_id}", status_code=status.HTTP_200_OK)
def update_cloud_provider(
    cloud_provider_id: str,
    body: UpdateCloudProviderRequest,
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
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
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _service(claims, db).delete_cloud_provider(cloud_provider_id)
