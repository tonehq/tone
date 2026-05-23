from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.models.agent import Agent
from shared.config import settings

router = APIRouter()


@router.get("/get_all_agents")
def get_all_agents(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    rows = (
        db.query(Agent.id, Agent.name)
        .filter(Agent.organization_id == org_id, Agent.deleted_at.is_(None))
        .order_by(Agent.name.asc())
        .all()
    )
    return [{"id": str(r.id), "uuid": str(r.id), "name": r.name} for r in rows]
