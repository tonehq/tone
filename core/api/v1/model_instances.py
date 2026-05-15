from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.model_instance_service import ModelInstanceService
from core.middleware.auth import get_jwt_claims, require_admin_or_owner, JWTClaims

router = APIRouter()


_ALLOWED_SORT_FIELDS = {"created_at", "updated_at"}


def _parse_sort(sort: Optional[str], allowed: set, default: str = "-created_at"):
    """Parse '-field' / 'field' into (sort_by, sort_order). Validates against allowed set."""
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page must be >= 1",
        )
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
def upsert_model_instance(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    model_menu_id = data.get("model_menu_id")

    if not model_menu_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_menu_id is required",
        )

    return ModelInstanceService(db, user_id=claims.user_id).upsert_model_instance(
        model_menu_id=model_menu_id,
        account_id=data.get("account_id"),
        host_region=data.get("host_region"),
        instance_status=data.get("status"),
        instance_id=data.get("id"),
    )


@router.post("/list")
def get_all_model_instances(
    data: Dict[str, Any] = Body(default={}),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    """List model instances with filtering, sorting, and pagination.

    Body: {
      model_menu_id?: int,
      account_id?: int,
      status?: string,
      sort?: string,
      page?: int (>=1, default 1),
      page_size?: int,
    }
    """
    sort_by, sort_order = _parse_sort(data.get("sort"), _ALLOWED_SORT_FIELDS)
    page, page_size = _parse_page(data)

    return ModelInstanceService(db, user_id=claims.user_id).get_all_model_instances(
        model_menu_id=data.get("model_menu_id"),
        account_id=data.get("account_id"),
        status_filter=data.get("status"),
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.post("/get")
def get_model_instance(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(get_jwt_claims),
    db: Session = Depends(get_db),
):
    """Fetch a single model instance by id.

    Body: { "instance_id": int (required) }
    """
    instance_id = data.get("instance_id")
    if instance_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instance_id is required",
        )
    try:
        instance_id = int(instance_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instance_id must be an integer",
        )

    return ModelInstanceService(db, user_id=claims.user_id).get_model_instance(instance_id)


@router.delete("/delete")
def delete_model_instance(
    instance_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return ModelInstanceService(db, user_id=claims.user_id).delete_model_instance(instance_id)
