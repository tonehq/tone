"""EE agent-readiness router.

Thin wrapper: reuses the core service + schemas but goes through the EE auth
middleware. Mirrors the shape of ``ee/api/v1/agents.py``.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.v1.agent_readiness import ReadinessRequest
from core.database.session import get_db
from core.services.readiness import ReadinessService
from core.services.readiness.schemas import ReadinessReport, ReadinessSummary
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()


def _get_service(claims: EEJWTClaims, db: Session) -> ReadinessService:
    org_id = UUID(claims.org_id)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return ReadinessService(db, user_id=user_id, org_id=org_id)


@router.post("/{agent_id}/readiness", response_model=ReadinessReport)
async def check_readiness(
    agent_id: str,
    body: ReadinessRequest = ReadinessRequest(),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
) -> ReadinessReport:
    svc = _get_service(claims, db)
    return await svc.check(
        agent_id,
        depth=body.depth,
        config_id=body.config_id,
        trigger=body.trigger or "api",
        deep_categories=set(body.categories) if body.categories is not None else None,
    )


@router.get("/{agent_id}/readiness/summary", response_model=ReadinessSummary)
async def readiness_summary(
    agent_id: str,
    config_id: Optional[str] = Query(None),
    trigger: Optional[str] = Query(None, description="Optional analytics label"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
) -> ReadinessSummary:
    svc = _get_service(claims, db)
    return await svc.summary(
        agent_id, config_id=config_id, trigger=trigger or "list_page"
    )
