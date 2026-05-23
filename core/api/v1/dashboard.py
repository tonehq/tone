from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.dashboard_service import DashboardService
from core.utils.org import resolve_org_id

router = APIRouter()


def get_dashboard_stats_handler(claims: JWTClaims, db: Session) -> dict:
    """Shared handler used by both Core and EE dashboard routers."""
    return DashboardService(db, org_id=resolve_org_id(claims)).get_stats()


@router.get("/stats")
def get_dashboard_stats(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return get_dashboard_stats_handler(claims, db)
