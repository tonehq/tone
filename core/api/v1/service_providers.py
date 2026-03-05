from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Set

from core.database.session import get_db
from core.models.voice import Voice
from core.services.service_provider_service import ServiceProviderService
from core.middleware.auth import get_jwt_claims, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_service_provider(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
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

    return ServiceProviderService(db, user_id=claims.user_id).upsert_service_provider(
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
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    EXCLUDED_PROVIDER_IDS = {35, 38, 43, 46, 48, 50}
    providers = ServiceProviderService(db, user_id=claims.user_id).get_all_service_providers(
        provider_type=provider_type
    )
    # Get TTS provider IDs that have at least one voice
    tts_provider_ids_with_voices: Set[int] = set(
        row[0] for row in db.query(Voice.service_provider_id).filter(Voice.is_active == True).distinct().all()
    )
    result = []
    for p in providers:
        if p.get("id") in EXCLUDED_PROVIDER_IDS:
            continue
        # For TTS providers, only include if they have voices
        if p.get("provider_type") == "tts" and p.get("id") not in tts_provider_ids_with_voices:
            continue
        result.append(p)
    return result


@router.get("/get")
def get_service_provider(
    provider_id: int = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return ServiceProviderService(db, user_id=claims.user_id).get_service_provider(provider_id)


@router.delete("/delete")
def delete_service_provider(
    provider_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return ServiceProviderService(db, user_id=claims.user_id).delete_service_provider(provider_id)

