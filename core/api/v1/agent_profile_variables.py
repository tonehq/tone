"""Agent Profile Variables routes — CRUD for per-agent ``{{profile.<key>}}``
placeholders.

The router lives in one file (not the two-edition ``knowledge_base_routes``
builder pattern) because these routes have no EE-vs-Core diff — same auth
dep, same service, same response shape. Mounted in both editions from
``main.py``.

Every route is org-scoped through :func:`require_org_member`; the service
layer double-checks by scoping every SQL read to the caller's org. The
per-agent unique constraint on ``(agent_id, key)`` means a valid id from
another agent still 404s.
"""

from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.api.v1._agent_guards import ensure_agent_in_org, resolve_org_id
from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.agents.agent_profile_variable_service import (
    AgentProfileVariableService,
)
from core.services.agents.errors import (
    ProfileVariableInvalidError,
    ProfileVariableKeyConflictError,
    ProfileVariableNotFoundError,
)

router = APIRouter()


# ── Pydantic bodies ─────────────────────────────────────────────────────


class ProfileVariableIn(BaseModel):
    """Body for POST /agents/{agent_id}/profile-variables."""

    key: str = Field(..., min_length=1, max_length=64)
    value: str = Field(default="", max_length=10_240)
    description: Optional[str] = Field(default=None, max_length=1000)
    source: Literal["static", "webhook"] = "static"
    source_path: Optional[str] = Field(default=None, max_length=200)


class ProfileVariablePatchRequest(BaseModel):
    """PATCH-style body for PUT /agents/{agent_id}/profile-variables/{id}.
    Every field is optional; fields left unset on the body are not touched."""

    key: Optional[str] = Field(default=None, min_length=1, max_length=64)
    value: Optional[str] = Field(default=None, max_length=10_240)
    description: Optional[str] = Field(default=None, max_length=1000)
    source: Optional[Literal["static", "webhook"]] = None
    source_path: Optional[str] = Field(default=None, max_length=200)


# ── Helpers ─────────────────────────────────────────────────────────────


def _handle_profile_var_error(exc: Exception) -> HTTPException:
    """Typed service error → HTTP mapping. Kept next to the router so every
    handler uses the same shape (no per-route try/except drift)."""
    if isinstance(exc, ProfileVariableNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_VAR_NOT_FOUND", "message": str(exc)},
        )
    if isinstance(exc, ProfileVariableKeyConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PROFILE_VAR_KEY_CONFLICT", "message": str(exc)},
        )
    if isinstance(exc, ProfileVariableInvalidError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PROFILE_VAR_INVALID", "message": str(exc)},
        )
    raise exc  # not ours — bubble up


# ── Routes ──────────────────────────────────────────────────────────────


@router.get("/agents/{agent_id}/profile-variables")
def list_profile_variables(
    agent_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """All profile variables for one agent, ordered by key. No pagination —
    per-agent sets are tiny; the frontend filters client-side."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileVariableService(db, org_id=org_id)
    rows = svc.list_variables(agent_id)
    return {"items": [svc.variable_response(r) for r in rows]}


@router.post(
    "/agents/{agent_id}/profile-variables",
    status_code=status.HTTP_201_CREATED,
)
def create_profile_variable(
    agent_id: UUID,
    body: ProfileVariableIn = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create one profile variable. Returns the persisted row so the FE can
    drop it into its cache without a refetch."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileVariableService(db, org_id=org_id)
    try:
        row = svc.create_variable(
            agent_id,
            key=body.key,
            value=body.value,
            description=body.description,
            source=body.source,
            source_path=body.source_path,
        )
    except (
        ProfileVariableKeyConflictError,
        ProfileVariableInvalidError,
    ) as exc:
        raise _handle_profile_var_error(exc) from exc
    return svc.variable_response(row)


@router.put("/agents/{agent_id}/profile-variables/{variable_id}")
def update_profile_variable(
    agent_id: UUID,
    variable_id: UUID,
    body: ProfileVariablePatchRequest = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """PATCH-style update — fields left unset on the body are not touched."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileVariableService(db, org_id=org_id)
    try:
        row = svc.update_variable(
            agent_id,
            variable_id,
            key=body.key,
            value=body.value,
            description=body.description,
            source=body.source,
            source_path=body.source_path,
        )
    except (
        ProfileVariableNotFoundError,
        ProfileVariableKeyConflictError,
        ProfileVariableInvalidError,
    ) as exc:
        raise _handle_profile_var_error(exc) from exc
    return svc.variable_response(row)


@router.delete(
    "/agents/{agent_id}/profile-variables/{variable_id}",
    status_code=status.HTTP_200_OK,
)
def delete_profile_variable(
    agent_id: UUID,
    variable_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Hard-delete one profile variable. Any surviving ``{{profile.<key>}}``
    references render verbatim (unknown-key fallback in ``substitute_variables``)
    — matches the "delete = loose" v1 decision, no cascading edits."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileVariableService(db, org_id=org_id)
    try:
        svc.delete_variable(agent_id, variable_id)
    except ProfileVariableNotFoundError as exc:
        raise _handle_profile_var_error(exc) from exc
    return {"deleted": str(variable_id)}
