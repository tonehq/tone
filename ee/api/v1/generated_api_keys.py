"""EE mirror of the Generated API Keys router.

Same shape as ``core/api/v1/generated_api_keys.py`` but bound to EE auth guards
(``require_ee_admin_or_owner`` / ``require_ee_org_member``) so the tenant_id
header + per-org membership check apply. Pydantic schemas are imported from
core to keep the request contract identical across editions.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.api.v1.generated_api_keys import CreateApiKeyRequest, ListApiKeysRequest
from core.database.session import get_db
from core.services.generated_api_key_service import GeneratedApiKeyService
from ee.middleware.auth import (
    EEJWTClaims,
    require_ee_admin_or_owner,
    require_ee_org_member,
)

router = APIRouter()


def _get_service(claims: EEJWTClaims, db: Session) -> GeneratedApiKeyService:
    return GeneratedApiKeyService(
        db,
        user_id=UUID(str(claims.user_id)) if claims.user_id else None,
        org_id=UUID(str(claims.org_id)),
    )


@router.post("/create_api_key", status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: CreateApiKeyRequest,
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    row, full_key = svc.create_api_key(name=body.name, expires_at=body.expires_at)
    response = svc.api_key_response(row)
    response["key"] = full_key
    return response


@router.post("/list")
def list_api_keys(
    body: ListApiKeysRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_api_keys(
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/get_api_key")
def get_api_key(
    api_key_id: UUID = Query(..., description="The API key ID to fetch"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.api_key_response(svc.get_api_key(api_key_id))


@router.post("/revoke_api_key")
def revoke_api_key(
    api_key_id: UUID = Query(..., description="The API key ID to revoke"),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.api_key_response(svc.revoke_api_key(api_key_id))


@router.delete("/delete_api_key")
def delete_api_key(
    api_key_id: UUID = Query(..., description="The API key ID to delete"),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_api_key(api_key_id)
