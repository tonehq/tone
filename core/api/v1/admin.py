"""Admin operational endpoints.

* ``GET  /admin/log-level`` — report the effective log level (agent/org/env) and
  the process baseline.
* ``POST /admin/log-level`` — set the DB log level for the caller's organization,
  or for a specific agent in it. ``level: null`` clears it (inherit the parent).

Levels resolve most-specific-first: agent > organization > env baseline > INFO
(see core/services/log_level_resolver.py). Changing a level takes effect on the
next call for that agent/org — no build, no restart. All reads/writes are scoped
to the caller's organization.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.logging import _VALID_LEVELS, _normalize_level, get_applied_level, resolve_level
from core.middleware.auth import JWTClaims, require_admin_or_owner
from core.models.agent import Agent
from core.models.organization import Organization
from core.services.log_level_resolver import resolve_call_log_level
from shared.config import settings

router = APIRouter()

# Operator-facing levels. The resolver accepts the full loguru set, but the UI and
# this endpoint only advertise the three that matter for investigation.
_OPERATOR_LEVELS = ["INFO", "DEBUG", "TRACE"]


def _caller_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


def _scoped_agent(db: Session, agent_id: UUID, org_id: UUID) -> Agent:
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.organization_id == org_id)
        .first()
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.get("/log-level")
def read_log_level(
    agent_id: Optional[UUID] = None,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Effective level for an agent (``?agent_id=``) or the caller's org, plus the
    process baseline and the level currently applied to this pod's sink."""
    org_id = _caller_org_id(claims)
    baseline, baseline_source = resolve_level()
    result = {
        "baseline": baseline,
        "baseline_source": baseline_source,
        "applied": get_applied_level(),
        "allowed_levels": _OPERATOR_LEVELS,
    }
    if agent_id is not None:
        agent = _scoped_agent(db, agent_id, org_id)
        level, source = resolve_call_log_level(db, agent=agent)
        result.update(
            {
                "scope": "agent",
                "agent_id": str(agent_id),
                "agent_level": agent.log_level,
                "effective": level,
                "source": source,
            }
        )
    else:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        level, source = resolve_call_log_level(db, org=org)
        result.update(
            {
                "scope": "organization",
                "organization_id": str(org_id),
                "organization_level": org.log_level,
                "effective": level,
                "source": source,
            }
        )
    return result


@router.post("/log-level")
def set_log_level(
    level: Optional[str] = Body(None, embed=True),
    agent_id: Optional[UUID] = Body(None, embed=True),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    """Set the log level for the caller's org, or a specific agent in it. ``level``
    null/blank clears it (inherit the parent). Invalid level → 400."""
    org_id = _caller_org_id(claims)

    normalized: Optional[str] = None
    if level is not None and str(level).strip() != "":
        normalized = _normalize_level(level)
        if normalized is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid log level: {level!r}. Allowed: {sorted(_VALID_LEVELS)}",
            )

    if agent_id is not None:
        agent = _scoped_agent(db, agent_id, org_id)
        agent.log_level = normalized
        db.commit()
        effective, source = resolve_call_log_level(db, agent=agent)
        return {
            "scope": "agent",
            "agent_id": str(agent_id),
            "level": normalized,
            "effective": effective,
            "source": source,
        }

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    org.log_level = normalized
    db.commit()
    effective, source = resolve_call_log_level(db, org=org)
    return {
        "scope": "organization",
        "organization_id": str(org_id),
        "level": normalized,
        "effective": effective,
        "source": source,
    }
