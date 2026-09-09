"""Shared route guards for agent-scoped endpoints.

Extracted so agent sub-resource routers (profile variables, profile webhook, …)
share ONE org-resolution + agent-in-org check instead of each re-declaring it.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.middleware.auth import JWTClaims
from core.models.agent import Agent
from shared.config import settings


def resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


def ensure_agent_in_org(db: Session, org_id: UUID, agent_id: UUID) -> UUID:
    """Verify ``agent_id`` belongs to the caller's org AND is not soft-deleted —
    otherwise a forged URL could still hit an agent sub-resource service, and a
    tombstoned agent would silently accept CRUD. Fail fast at the route
    boundary (mirrors ``agent_llm_evals``)."""
    exists = (
        db.query(Agent.id)
        .filter(
            Agent.id == agent_id,
            Agent.organization_id == org_id,
            Agent.deleted_at.is_(None),
        )
        .first()
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return agent_id
