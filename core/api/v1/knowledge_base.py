"""Core-edition knowledge-base router.

The route logic lives in the shared builder (``knowledge_base_routes``); this
module only wires in the Core auth dependency and org-id resolution.
"""

from uuid import UUID

from core.api.v1.knowledge_base_routes import build_knowledge_base_router
from core.middleware.auth import JWTClaims, require_org_member
from shared.config import settings


def _resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


router = build_knowledge_base_router(require_org_member, _resolve_org_id)
