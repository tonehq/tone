from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.models.agent import Agent
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


@router.get("/get_all_agents")
def get_all_agents(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    rows = (
        db.query(Agent.id, Agent.name)
        .filter(Agent.organization_id == org_id, Agent.deleted_at.is_(None))
        .order_by(Agent.name.asc())
        .all()
    )
    return [{"id": str(r.id), "uuid": str(r.id), "name": r.name} for r in rows]
