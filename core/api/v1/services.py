from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.service_service import ServiceConfigService
from core.middleware.auth import get_jwt_claims, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_service(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    service_provider_id = data.get("service_provider_id")
    name = data.get("name")
    service_type = data.get("service_type")
    config = data.get("config")

    if not all([service_provider_id, name, service_type, config]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_provider_id, name, service_type, and config are required"
        )

    return ServiceConfigService(db, user_id=claims.user_id).upsert_service(
        service_provider_id=service_provider_id,
        name=name,
        service_type=service_type,
        config=config,
        api_key_id=data.get("api_key_id"),
        description=data.get("description"),
        is_default=data.get("is_default", False),
        is_public=data.get("is_public", False),
        tags=data.get("tags"),
        service_uuid=data.get("uuid"),
        service_status=data.get("status")
    )


@router.get("/list")
def get_all_services(
    service_type: Optional[str] = Query(None),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return ServiceConfigService(db, user_id=claims.user_id).get_all_services(
        service_type=service_type
    )


@router.get("/get")
def get_service(
    service_id: int = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return ServiceConfigService(db, user_id=claims.user_id).get_service(service_id)


@router.get("/default")
def get_default_service(
    service_type: str = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return ServiceConfigService(db, user_id=claims.user_id).get_default_service(
        service_type=service_type
    )


@router.delete("/delete")
def delete_service(
    service_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    return ServiceConfigService(db, user_id=claims.user_id).delete_service(service_id)
