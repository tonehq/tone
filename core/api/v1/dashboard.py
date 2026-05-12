from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return DashboardService(db).get_stats()
