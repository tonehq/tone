from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.services.dashboard_service import DashboardService
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return DashboardService(db, org_id=UUID(claims.org_id)).get_stats()
