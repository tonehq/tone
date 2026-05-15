from fastapi import APIRouter, Depends, Body, Query, status, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.model_menu_service import ModelMenuService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


_ALLOWED_MODEL_SORT_FIELDS = {"created_at", "updated_at", "name"}


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
    try:
        page = int(data.get("page", 1) or 1)
        page_size = int(data.get("page_size", 10) or 10)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page and page_size must be integers",
        )
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_size must be between 1 and 100",
        )
    return page, page_size


@router.post("/get_models_by_provider", status_code=status.HTTP_200_OK)
def get_models_by_provider(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """List models for a model provider menu with filtering, sorting, and pagination.

    Body: {
      model_provider_menu_id: int (required),
      name?: string,
      status?: string,
      service_type?: string,
      sort?: string,
      page?: int (>=1, default 1),
      page_size?: int (1..100, default 10),
    }
    """
    model_provider_menu_id = data.get("model_provider_menu_id")
    if model_provider_menu_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_provider_menu_id is required",
        )
    try:
        model_provider_menu_id = int(model_provider_menu_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_provider_menu_id must be an integer",
        )

    sort_by, sort_order = _parse_sort(data.get("sort"), _ALLOWED_MODEL_SORT_FIELDS)
    page, page_size = _parse_page(data)

    return ModelMenuService(db).get_models_by_provider(
        model_provider_menu_id=model_provider_menu_id,
        name=data.get("name"),
        status_filter=data.get("status"),
        service_type=data.get("service_type"),
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.post("/upsert_model", status_code=status.HTTP_200_OK)
def upsert_model(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create or update a model menu entry."""
    return ModelMenuService(db).upsert_model(data)


@router.delete("/delete_model", status_code=status.HTTP_200_OK)
def delete_model(
    model_id: int = Query(..., description="The model ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return ModelMenuService(db).delete_model(model_id)
