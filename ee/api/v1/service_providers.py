from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Set
from uuid import UUID

from core.database.session import get_db
from core.models.voice import Voice
from core.services.service_provider_service import ServiceProviderService
from ee.middleware.auth import get_ee_jwt_claims, require_ee_admin_or_owner, require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_service_provider(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    name = data.get("name")
    display_name = data.get("display_name")
    provider_type = data.get("provider_type")
    auth_type = data.get("auth_type")

    if not all([name, display_name, provider_type, auth_type]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name, display_name, provider_type, and auth_type are required"
        )

    return ServiceProviderService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).upsert_service_provider(
        name=name,
        display_name=display_name,
        provider_type=provider_type,
        auth_type=auth_type,
        description=data.get("description"),
        logo_url=data.get("logo_url"),
        website_url=data.get("website_url"),
        documentation_url=data.get("documentation_url"),
        base_url=data.get("base_url"),
        supports_streaming=data.get("supports_streaming", False),
        config_schema=data.get("config_schema"),
        is_system=data.get("is_system", False),
        provider_status=data.get("status"),
        provider_id=data.get("id"),
    )


@router.get("/list")
def get_all_service_providers(
    provider_type: Optional[str] = Query(None),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    ALLOWED_PROVIDER_IDS = {1, 2, 3, 19, 20, 21, 23, 26, 30, 33, 36, 37, 38, 39, 40, 42, 43, 46, 47, 48, 49, 50, 51, 55}

    providers = ServiceProviderService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_all_service_providers(
        provider_type=provider_type
    )
    tts_provider_ids_with_voices: Set[int] = set(
        row[0] for row in db.query(Voice.service_provider_id).filter(Voice.is_active == True).distinct().all()
    )
    result = []
    for p in providers:
        if p.get("id") not in ALLOWED_PROVIDER_IDS:
            continue
        if p.get("provider_type") == "tts" and p.get("id") not in tts_provider_ids_with_voices:
            continue
        result.append(p)
    return result


@router.get("/get")
def get_service_provider(
    provider_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return ServiceProviderService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_service_provider(provider_id)


@router.delete("/delete")
def delete_service_provider(
    provider_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    return ServiceProviderService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).delete_service_provider(provider_id)
