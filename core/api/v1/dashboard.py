from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.dashboard_service import DashboardService
from shared.config import settings

router = APIRouter()


def _resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


@router.get("/stats")
def get_dashboard_stats(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return DashboardService(db, org_id=_resolve_org_id(claims)).get_stats()
