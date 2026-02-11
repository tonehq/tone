from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.generated_api_key_service import GeneratedApiKeyService
from core.middleware.auth import get_jwt_claims, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_basic_key(
    data: Dict[str, Any] = Body(...),
    id: Optional[int] = Query(None, description="Provide ID to update existing key"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    """
    Create or update a basic API key.
    Required fields: name, key_value
    Query params:
        - id: provide to update existing key
    """
    name = data.get("name")
    key_value = data.get("key_value")

    if not name or not key_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and key_value are required"
        )

    return GeneratedApiKeyService(db, user_id=claims.user_id).upsert_basic_key(
        name=name,
        key_value=key_value,
        key_id=id
    )


@router.post("/upsert-full", status_code=status.HTTP_200_OK)
def upsert_full_key(
    data: Dict[str, Any] = Body(...),
    id: Optional[int] = Query(None, description="Provide ID to update existing key"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    """
    Create or update an API key with full configuration.
    Required fields: name, key_value
    Query params:
        - id: provide to update existing key
    Optional body fields:
        - domains: list of allowed domains (e.g., ["example.com", "api.example.com"])
        - abuse_prevention: JSON object with:
            - is_toggled: boolean
            - recaptcha_secret_key: string
            - threshold: float or int
        - fraud_protection: boolean
    """
    name = data.get("name")
    key_value = data.get("key_value")

    if not name or not key_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and key_value are required"
        )

    return GeneratedApiKeyService(db, user_id=claims.user_id).upsert_full_key(
        name=name,
        key_value=key_value,
        key_id=id,
        domains=data.get("domains"),
        abuse_prevention=data.get("abuse_prevention"),
        fraud_protection=data.get("fraud_protection")
    )


@router.get("/list")
def get_all_keys(
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    """Get all generated API keys."""
    return GeneratedApiKeyService(db, user_id=claims.user_id).get_all_keys()


@router.get("/get")
def get_key(
    key_id: int = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    """Get a specific API key by ID."""
    return GeneratedApiKeyService(db, user_id=claims.user_id).get_key_by_id(key_id)


@router.delete("/delete")
def delete_key(
    key_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    """Delete an API key by ID."""
    return GeneratedApiKeyService(db, user_id=claims.user_id).delete_key(key_id)
