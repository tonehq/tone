from fastapi import APIRouter, Depends, Body, Query, status, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.model_service import ModelService
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
    """List models for a service provider with filtering, sorting, and pagination.

    Body: {
      service_provider_id: int (required),
      name?: string,                # partial match on model name
      status?: string,
      service_type?: string,
      sort?: string,                # "-created_at" | "name" | "updated_at"
      page?: int (>=1, default 1),
      page_size?: int (1..100, default 10),
    }
    """
    service_provider_id = data.get("service_provider_id")
    if service_provider_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_provider_id is required",
        )
    try:
        service_provider_id = int(service_provider_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_provider_id must be an integer",
        )

    sort_by, sort_order = _parse_sort(data.get("sort"), _ALLOWED_MODEL_SORT_FIELDS)
    page, page_size = _parse_page(data)

    return ModelService(db).get_models_by_provider(
        service_provider_id=service_provider_id,
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
    """Create or update a model. Send id to update; send service_provider_id and name to create."""
    return ModelService(db).upsert_model(data)


@router.delete("/delete_model", status_code=status.HTTP_200_OK)
def delete_model(
    model_id: int = Query(..., description="The model ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return ModelService(db).delete_model(model_id)
