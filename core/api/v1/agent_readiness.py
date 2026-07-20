"""Agent readiness endpoints.

Two routes, both org-scoped:

- ``POST /agent/{agent_id}/readiness`` — full report (Shallow or Deep).
- ``GET  /agent/{agent_id}/readiness/summary`` — small badge shape for lists.

The publish gate is not exposed as its own endpoint — it's called from inside
``POST /agent/switch_active_version`` so it can't be bypassed.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.readiness import ReadinessService
from core.services.readiness.schemas import (
    Category,
    Depth,
    ReadinessReport,
    ReadinessRunList,
    ReadinessSummary,
)
from shared.config import settings

router = APIRouter()


class ReadinessRequest(BaseModel):
    depth: Depth = Depth.SHALLOW
    config_id: Optional[str] = None
    # Free-form label describing WHY this check ran (e.g. "editor_load",
    # "field_change", "test_button", "list_page"). Stored on the event row so
    # analytics can slice audits by trigger. Not enforced against an enum so
    # the frontend can evolve trigger names independently.
    trigger: Optional[str] = None
    # Optional targeted-deep filter: when set alongside ``depth=deep``, only
    # deep checks in these categories run live; other deep checks return
    # SKIPPED. Used by the save flow to probe only the resources the user
    # actually touched. Ignored when ``depth=shallow``. Empty list is treated
    # as "no categories" — every deep check is skipped, effectively equivalent
    # to a shallow run.
    categories: Optional[List[Category]] = None
    # When true, bypass the read-through snapshot/coalesce caches and always run
    # + persist a fresh event. Set by the "Run deep test" button so each explicit
    # run appears as a new entry in the run-history list. Ignored for targeted
    # deep (categories) which already bypasses caches.
    force: bool = False


def _get_service(claims: JWTClaims, db: Session) -> ReadinessService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return ReadinessService(db, user_id=user_id, org_id=org_id)


@router.post("/{agent_id}/readiness", response_model=ReadinessReport)
async def check_readiness(
    agent_id: str,
    body: ReadinessRequest = ReadinessRequest(),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
) -> ReadinessReport:
    """Run the full readiness check for one agent.

    The report always contains the same shape (see ``ReadinessReport``); UIs
    render off ``overall_status`` + the flat ``checks`` list, so the same
    response drives the sidebar widget, the publish modal, and the "Test agent"
    dialog.
    """
    svc = _get_service(claims, db)
    return await svc.check(
        agent_id,
        depth=body.depth,
        config_id=body.config_id,
        trigger=body.trigger or "api",
        deep_categories=set(body.categories) if body.categories is not None else None,
        force=body.force,
    )


@router.get("/{agent_id}/readiness/summary", response_model=ReadinessSummary)
async def readiness_summary(
    agent_id: str,
    config_id: Optional[str] = Query(None),
    trigger: Optional[str] = Query(None, description="Optional analytics label"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
) -> ReadinessSummary:
    """Cheap Shallow summary — for the agent list badge."""
    svc = _get_service(claims, db)
    return await svc.summary(
        agent_id, config_id=config_id, trigger=trigger or "list_page"
    )


@router.get("/{agent_id}/readiness/runs", response_model=ReadinessRunList)
async def list_readiness_runs(
    agent_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max runs to return"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
) -> ReadinessRunList:
    """List past deep readiness runs (newest first) for the run-history dropdown.

    Metadata only — no per-check detail. Fetch a single run's full report via
    the ``/runs/{run_number}`` route below.
    """
    svc = _get_service(claims, db)
    return svc.list_runs(agent_id, limit=limit)


@router.get("/{agent_id}/readiness/runs/{run_number}", response_model=ReadinessReport)
async def get_readiness_run(
    agent_id: str,
    run_number: int,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
) -> ReadinessReport:
    """Return the full stored report (with checks) for one past run."""
    svc = _get_service(claims, db)
    return svc.get_run(agent_id, run_number)
