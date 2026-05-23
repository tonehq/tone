from uuid import UUID

from core.middleware.auth import JWTClaims
from shared.config import settings


def resolve_org_id(claims: JWTClaims) -> UUID:
    """Resolve the effective org_id for a request. Falls back to
    ``settings.DEFAULT_ORG_ID`` for single-tenant Core when no org_id is
    present on the claims. EE middleware already enforces a valid org_id, so
    the fallback is unused there."""
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
