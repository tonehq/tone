from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.api_key_service import ApiKeyService
from core.middleware.auth import get_jwt_claims, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_api_key(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    service_provider_id = data.get("service_provider_id")
    name = data.get("name")
    api_key_value = data.get("api_key")

    if not service_provider_id or not name or not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_provider_id, name, and api_key are required"
        )

    return ApiKeyService(db, user_id=claims.user_id).upsert_api_key(
        service_provider_id=service_provider_id,
        name=name,
        api_key_value=api_key_value,
        description=data.get("description"),
        additional_credentials=data.get("additional_credentials"),
        rate_limit_config=data.get("rate_limit_config"),
        expires_at=data.get("expires_at"),
        key_uuid=data.get("uuid"),
        key_status=data.get("status")
    )


@router.get("/list")
def get_all_api_keys(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return ApiKeyService(db, user_id=claims.user_id).get_all_api_keys()


@router.get("/get")
def get_api_key(
    api_key_id: int = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return ApiKeyService(db, user_id=claims.user_id).get_api_key(api_key_id)


@router.delete("/delete")
def delete_api_key(
    api_key_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return ApiKeyService(db, user_id=claims.user_id).delete_api_key(api_key_id)


@router.post("/validate")
def validate_api_key(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    api_key_id = data.get("api_key_id")
    is_valid = data.get("is_valid")

    if api_key_id is None or is_valid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key_id and is_valid are required"
        )

    return ApiKeyService(db, user_id=claims.user_id).validate_api_key(
        api_key_id=api_key_id,
        is_valid=is_valid,
        validation_error=data.get("validation_error")
    )
