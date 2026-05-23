from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.api.v1.dashboard import get_dashboard_stats_handler
from core.database.session import get_db
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return get_dashboard_stats_handler(claims, db)
