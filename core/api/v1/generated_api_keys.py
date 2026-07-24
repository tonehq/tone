"""Generated API Keys router — customer-facing programmatic-access keys.

Writes (create / revoke / delete) require admin/owner; reads (get / list) are open
to any org member. All handlers are org-scoped via the service layer (no IDOR).

Distinct from ``api_keys`` in Model Providers (those are provider credentials for
LLM/STT/TTS services, managed under Settings → Model Providers).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.generated_api_key_service import GeneratedApiKeyService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # ``None`` = never expires. When set, must be a future timestamp; the
    # service normalizes naive datetimes to UTC before comparing.
    expires_at: Optional[datetime] = None


class ListApiKeysRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _get_service(claims: JWTClaims, db: Session) -> GeneratedApiKeyService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return GeneratedApiKeyService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/create_api_key", status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: CreateApiKeyRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Mint a new API key. The plaintext ``key`` field is returned exactly once —
    the client MUST show it to the user immediately and drop it. After this
    response the key is unrecoverable."""
    svc = _get_service(claims, db)
    row, full_key = svc.create_api_key(name=body.name, expires_at=body.expires_at)
    response = svc.api_key_response(row)
    response["key"] = full_key
    return response


@router.post("/list")
def list_api_keys(
    body: ListApiKeysRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_api_keys(
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/get_api_key")
def get_api_key(
    api_key_id: UUID = Query(..., description="The API key ID to fetch"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.api_key_response(svc.get_api_key(api_key_id))


@router.post("/revoke_api_key")
def revoke_api_key(
    api_key_id: UUID = Query(..., description="The API key ID to revoke"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    return svc.api_key_response(svc.revoke_api_key(api_key_id))


@router.delete("/delete_api_key")
def delete_api_key(
    api_key_id: UUID = Query(..., description="The API key ID to delete"),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_api_key(api_key_id)
