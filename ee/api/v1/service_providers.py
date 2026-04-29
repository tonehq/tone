from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from uuid import UUID

from core.database.session import get_db
from core.services.service_provider_service import ServiceProviderService
from ee.middleware.auth import get_ee_jwt_claims, require_ee_admin_or_owner, require_ee_org_member, EEJWTClaims

router = APIRouter()


_ALLOWED_SP_SORT_FIELDS = {"created_at", "updated_at", "name", "display_name"}


def _parse_sort(sort: Optional[str], allowed: set, default: str = "-created_at"):
    raw = sort or default
    if raw.startswith("-"):
        sort_by, sort_order = raw[1:], "desc"
    else:
        sort_by, sort_order = raw, "asc"
    if sort_by not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field: {sort_by}. Allowed: {', '.join(sorted(allowed))}",
        )
    return sort_by, sort_order


def _parse_page(data: Dict[str, Any]):
    """Extract and validate page / page_size from a dict body.

    If page_size is omitted or 0, returns (page, None) to signal "return all rows".
    """
    try:
        page = int(data.get("page", 1) or 1)
        raw_page_size = data.get("page_size")
        page_size = None if raw_page_size is None else int(raw_page_size)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page and page_size must be integers",
        )
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be >= 1")
    if page_size is not None and page_size < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_size must be >= 0",
        )
    # page_size=0 means "all"
    if page_size == 0:
        page_size = None
    return page, page_size


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
    api_key = data.get("api_key")

    if not all([name, display_name, provider_type, auth_type]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name, display_name, provider_type, and auth_type are required"
        )

    if not isinstance(api_key, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key object is required",
        )

    is_update = data.get("id") is not None
    if not is_update and not api_key.get("api_key"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key.api_key (secret value) is required when creating a service provider",
        )
    if api_key.get("id") is None and not api_key.get("api_key"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key.id or api_key.api_key (secret value) is required",
        )

    return ServiceProviderService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).upsert_service_provider(
        name=name,
        display_name=display_name,
        provider_type=provider_type,
        auth_type=auth_type,
        api_key=api_key,
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


@router.post("/list")
def get_all_service_providers(
    data: Dict[str, Any] = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """List service providers with filtering, sorting, and pagination.

    Body: {provider_type?, name?, status?, sort?, page?, page_size?}.
    """
    sort_by, sort_order = _parse_sort(data.get("sort"), _ALLOWED_SP_SORT_FIELDS)
    page, page_size = _parse_page(data)

    return ServiceProviderService(
        db, org_id=UUID(claims.org_id), user_id=claims.user_id
    ).get_all_service_providers(
        provider_type=data.get("provider_type"),
        name=data.get("name"),
        status_filter=data.get("status"),
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.post("/get")
def get_service_provider(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Fetch a single service provider by id.

    Body: { "provider_id": int (required) }
    """
    provider_id = data.get("provider_id")
    if provider_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_id is required",
        )
    try:
        provider_id = int(provider_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_id must be an integer",
        )

    return ServiceProviderService(
        db, org_id=UUID(claims.org_id), user_id=claims.user_id
    ).get_service_provider(provider_id)


@router.delete("/delete")
def delete_service_provider(
    provider_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db)
):
    return ServiceProviderService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).delete_service_provider(provider_id)
