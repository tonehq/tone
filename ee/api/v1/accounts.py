from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from core.database.session import get_db
from core.services.account_service import AccountService
from ee.middleware.auth import get_ee_jwt_claims, require_ee_admin_or_owner, require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_account(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    service_provider_id = data.get("service_provider_id")
    model_provider_menu_id = data.get("model_provider_menu_id")
    name = data.get("name")
    service_type = data.get("service_type")

    if not name or not service_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and service_type are required"
        )
    if service_provider_id is None and model_provider_menu_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either service_provider_id or model_provider_menu_id is required"
        )

    return AccountService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).upsert_account(
        service_provider_id=service_provider_id,
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


@router.post("/list")
def get_all_accounts(
    data: Dict[str, Any] = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    page = data.get("page")
    page_size = data.get("page_size")

    if page is not None:
        page = int(page)
        if page < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be >= 1")
    if page_size is not None:
        page_size = int(page_size)
        if page_size < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size must be >= 1")

    return AccountService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_all_accounts(
        service_type=data.get("service_type"),
        page=page,
        page_size=page_size,
    )


@router.get("/get")
def get_account(
    account_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return AccountService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_account(account_id)


@router.get("/default")
def get_default_account(
    service_type: str = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return AccountService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_default_account(
        service_type=service_type
    )


@router.delete("/delete")
def delete_account(
    uuid: str = Query(None),
    account_id: int = Query(None),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    account_svc = AccountService(db, org_id=UUID(claims.org_id), user_id=claims.user_id)
    if uuid:
        return account_svc.delete_account_by_uuid(uuid)
    if account_id:
        return account_svc.delete_account(account_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="uuid or account_id is required"
    )
