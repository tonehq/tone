"""Enterprise-edition knowledge-base router.

The route logic lives in the shared builder (``core.api.v1.knowledge_base_routes``);
this module only wires in the EE auth dependency and org-id resolution.
"""

from uuid import UUID

from core.api.v1.knowledge_base_routes import build_knowledge_base_router
from ee.middleware.auth import EEJWTClaims, require_ee_org_member


def _resolve_org_id(claims: EEJWTClaims) -> UUID:
    return UUID(claims.org_id)


router = build_knowledge_base_router(require_ee_org_member, _resolve_org_id)
