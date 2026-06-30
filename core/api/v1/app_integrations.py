"""HTTP routes for the ``app_integrations`` catalog.

Thin wrappers around :class:`AppIntegrationService`. The router is responsible
only for: request validation via Pydantic, role gating, service instantiation,
and shaping the response via ``svc.app_integration_response()``.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.app_integration_service import AppIntegrationService
from core.utils.pagination import parse_page, parse_sort
from shared.config import settings


router = APIRouter()


# ─────────────────────────────────────────────────────────────────────
# Pydantic request schemas
# ─────────────────────────────────────────────────────────────────────


class _AppIntegrationBase(BaseModel):
    """Fields shared by create + update. Optional here so update is a true PATCH."""

    slug: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_url: Optional[str] = None
    token_url: Optional[str] = None
    scopes: Optional[List[str]] = None
    extra_auth_params: Optional[Dict[str, Any]] = None
    client_id_env_key: Optional[str] = None
    client_secret_env_key: Optional[str] = None
    pkce_required: Optional[bool] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class CreateAppIntegrationRequest(_AppIntegrationBase):
    """slug, display_name, and auth_type are required at creation time;
    the service enforces this and returns 400 with a precise message."""

    slug: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=120)
    auth_type: str = Field(..., description="One of: oauth, api_key, bearer_token, none")


class UpdateAppIntegrationRequest(_AppIntegrationBase):
    """All fields optional — only supplied keys are patched."""
    pass


_ALLOWED_SORT_FIELDS = {"slug", "display_name", "category", "sort_order", "created_at", "updated_at"}


# ─────────────────────────────────────────────────────────────────────
# Service factory
# ─────────────────────────────────────────────────────────────────────


def _get_service(claims: JWTClaims, db: Session) -> AppIntegrationService:
    """Build a service bound to the caller's org. The catalog itself is global,
    but ``user_id`` is captured so created rows record their author."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if claims.user_id else None
    return AppIntegrationService(db, user_id=user_id, org_id=org_id)


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────


@router.post("/create_app_integration", status_code=status.HTTP_201_CREATED)
def create_app_integration(
    body: CreateAppIntegrationRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Add a new integration to the global catalog. Admin/owner only."""
    svc = _get_service(claims, db)
    integration = svc.create_app_integration(body.model_dump(exclude_unset=True))
    return svc.app_integration_response(integration)


@router.put("/update_app_integration", status_code=status.HTTP_200_OK)
def update_app_integration(
    id: UUID = Query(..., description="App integration UUID"),
    body: UpdateAppIntegrationRequest = Body(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Patch an existing integration. Admin/owner only."""
    svc = _get_service(claims, db)
    integration = svc.update_app_integration(id, body.model_dump(exclude_unset=True))
    return svc.app_integration_response(integration)


@router.get("/get_app_integration")
def get_app_integration(
    id: UUID = Query(..., description="App integration UUID"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Fetch a single integration by id. Any org member may read."""
    svc = _get_service(claims, db)
    integration = svc.get_app_integration(id)
    return svc.app_integration_response(integration)


@router.post("/list")
def list_app_integrations(
    data: Dict[str, Any] = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """List integrations with optional search, filters, sort, and pagination.

    Body shape::

        {
          "search":     "hub",
          "category":   "crm",
          "auth_type":  "oauth",
          "is_enabled": true,
          "is_default": true,
          "sort_by":    "sort_order",
          "sort_order": "asc",
          "page":       1,
          "page_size":  20
        }

    All fields are optional. Legacy ``sort`` ("-field" / "field") is also accepted.
    """
    svc = _get_service(claims, db)
    return svc.list_app_integrations(**parse_list_args(data))


@router.delete("/delete_app_integration", status_code=status.HTTP_200_OK)
def delete_app_integration(
    id: UUID = Query(..., description="App integration UUID"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Hard-delete a non-default integration. Admin/owner only.

    Default (seeded) integrations cannot be deleted — disable them via
    ``update_app_integration`` with ``{"is_enabled": false}`` instead.
    """
    svc = _get_service(claims, db)
    return svc.delete_app_integration(id)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _optional_bool(value) -> Optional[bool]:
    """Coerce truthy/falsy strings ("true"/"false") and bools from JSON, or
    return None when the caller didn't pass the filter at all."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes"):
            return True
        if v in ("false", "0", "no"):
            return False
    return bool(value)


def parse_list_args(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the standard list-request body into kwargs for the service.

    Shared between the core and EE routers so the contract (filter keys,
    sort handling, pagination defaults) lives in exactly one place. Treats
    the body as untrusted: unknown keys are dropped and bools coerced.
    """
    if data.get("sort_by") or data.get("sort_order"):
        sort_by = data.get("sort_by") or "sort_order"
        sort_order = data.get("sort_order") or "asc"
    else:
        sort_by, sort_order = parse_sort(data.get("sort"), _ALLOWED_SORT_FIELDS)
        sort_by = sort_by or "sort_order"
        sort_order = sort_order or "asc"

    page, page_size = parse_page(data)

    return {
        "search": data.get("search"),
        "category": data.get("category"),
        "auth_type": data.get("auth_type"),
        "is_enabled": _optional_bool(data.get("is_enabled")),
        "is_default": _optional_bool(data.get("is_default")),
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "page_size": page_size,
    }
