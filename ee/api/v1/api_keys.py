from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, File, Form, UploadFile
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from uuid import UUID
import json

from core.database.session import get_db
from core.services.api_key_service import ApiKeyService
from ee.middleware.auth import get_ee_jwt_claims, require_ee_admin_or_owner, require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
async def upsert_api_key(
    service_provider_id: int = Form(...),
    name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    api_key: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    additional_credentials: Optional[str] = Form(None),
    rate_limit_config: Optional[str] = Form(None),
    expires_at: Optional[int] = Form(None),
    uuid: Optional[str] = Form(None),
    key_status: Optional[str] = Form(None),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    api_key_value = None

    # If file is uploaded, use file content as the api_key value
    if file and file.filename:
        content = await file.read()
        try:
            api_key_value = content.decode("utf-8").strip()
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a valid text/JSON file"
            )
        if file.filename.endswith(".json"):
            try:
                json.loads(api_key_value)
            except (json.JSONDecodeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON file content"
                )
    elif api_key:
        api_key_value = api_key

    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a file or api_key must be provided"
        )

    # Parse JSON string fields if provided
    parsed_additional = None
    if additional_credentials:
        try:
            parsed_additional = json.loads(additional_credentials)
        except (json.JSONDecodeError, ValueError):
            parsed_additional = None

    parsed_rate_limit = None
    if rate_limit_config:
        try:
            parsed_rate_limit = json.loads(rate_limit_config)
        except (json.JSONDecodeError, ValueError):
            parsed_rate_limit = None

    return ApiKeyService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).upsert_api_key(
        service_provider_id=service_provider_id,
        name=name,
        api_key_value=api_key_value,
        description=description,
        additional_credentials=parsed_additional,
        rate_limit_config=parsed_rate_limit,
        expires_at=expires_at,
        key_uuid=uuid,
        key_status=key_status
    )


@router.get("/list")
def get_all_api_keys(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return ApiKeyService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_all_api_keys()


@router.post("/list_by_provider")
def list_api_keys_by_provider(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """List api_keys for one provider, scoped to caller's org."""
    sp_id = data.get("service_provider_id")
    if sp_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_provider_id is required",
        )
    try:
        sp_id = int(sp_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_provider_id must be an integer",
        )
    return ApiKeyService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).list_by_provider(
        service_provider_id=sp_id,
        status_filter=data.get("status"),
        page=int(data.get("page") or 1),
        page_size=int(data.get("page_size") or 20),
    )


@router.get("/get")
def get_api_key(
    api_key_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return ApiKeyService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_api_key(api_key_id)


@router.delete("/delete")
def delete_api_key(
    api_key_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    return ApiKeyService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).delete_api_key(api_key_id)


@router.post("/validate")
def validate_api_key(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    api_key_id = data.get("api_key_id")
    is_valid = data.get("is_valid")

    if api_key_id is None or is_valid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key_id and is_valid are required"
        )

    return ApiKeyService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).validate_api_key(
        api_key_id=api_key_id,
        is_valid=is_valid,
        validation_error=data.get("validation_error")
    )
