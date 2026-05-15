from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.account_service import AccountService
from core.middleware.auth import get_jwt_claims, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_account(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    model_provider_menu_id = data.get("model_provider_menu_id")
    name = data.get("name")
    service_type = data.get("service_type")

    if not name or not service_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and service_type are required"
        )
    if model_provider_menu_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_provider_menu_id is required"
        )

    return AccountService(db, user_id=claims.user_id).upsert_account(
        model_provider_menu_id=model_provider_menu_id,
        name=name,
        service_type=service_type,
        config=data.get("config", {}),
        api_key_id=data.get("api_key_id"),
        description=data.get("description"),
        is_default=data.get("is_default", False),
        is_public=data.get("is_public", False),
        tags=data.get("tags"),
        account_uuid=data.get("uuid"),
        account_status=data.get("status"),
        api_key_value=data.get("api_key_value"),
        api_key_name=data.get("api_key_name"),
        additional_credentials=data.get("additional_credentials"),
    )


@router.get("/list")
def get_all_accounts(
    service_type: Optional[str] = Query(None),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return AccountService(db, user_id=claims.user_id).get_all_accounts(
        service_type=service_type
    )


@router.get("/get")
def get_account(
    account_id: int = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return AccountService(db, user_id=claims.user_id).get_account(account_id)


@router.get("/default")
def get_default_account(
    service_type: str = Query(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db)
):
    return AccountService(db, user_id=claims.user_id).get_default_account(
        service_type=service_type
    )


@router.delete("/delete")
def delete_account(
    uuid: str = Query(None),
    account_id: int = Query(None),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db)
):
    account_svc = AccountService(db, user_id=claims.user_id)
    if uuid:
        return account_svc.delete_account_by_uuid(uuid)
    if account_id:
        return account_svc.delete_account(account_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="uuid or account_id is required"
    )
