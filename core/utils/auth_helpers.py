"""Shared auth/identity helpers used across Core and EE editions.

Centralising these here keeps the parsing/raising behaviour consistent
between editions and between the API/service layers — see review feedback
on duplicated ``_coerce_uuid`` / ``_org_id`` / ``_svc`` helpers.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID

from fastapi import HTTPException, status

from core.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(raw: str) -> str:
    """SHA-256 hex digest of an opaque token (refresh token, email-request
    token). Never stores or returns the raw token."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def coerce_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
    """Best-effort UUID coercion. Returns ``None`` for empty/invalid input
    so callers that already treat ``None`` as ``not found`` keep working.
    Do not use this for tenant-scoping decisions — use ``require_org_id``."""
    if value is None or isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def require_org_id(org_id_value: Union[str, UUID, None]) -> UUID:
    """Resolve the effective org_id for a request.

    - Missing on Core single-tenant builds → fall back to ``DEFAULT_ORG_ID``.
    - Malformed (non-UUID) → raise 401 so a bad token can never fall through
      to a cross-tenant query.
    """
    if not org_id_value:
        return UUID(settings.DEFAULT_ORG_ID)
    if isinstance(org_id_value, UUID):
        return org_id_value
    try:
        return UUID(str(org_id_value))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid organization context",
        )
