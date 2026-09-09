"""Agent Profile Webhook routes — the per-agent HTTP webhook data source for
``{{profile.<key>}}`` variables.

Singular resource (one webhook per agent) → GET / PUT (upsert) / DELETE, plus a
POST ``/test`` that calls the saved config with a sample phone and reports the
raw response + per-path resolution. Mounted in both editions from ``main.py``.

Every route is org-scoped through :func:`require_org_member` + ``ensure_agent_in_org``;
the service double-checks by scoping every SQL read to the caller's org.
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
from core.services.agents.agent_profile_webhook_service import (
    AgentProfileWebhookService,
)
from core.services.agents.errors import (
    ProfileWebhookInvalidError,
    ProfileWebhookNotFoundError,
)
from core.services.agents.profile_webhook_schemas import RequestIdentifierIn

router = APIRouter()


# ── Pydantic bodies ─────────────────────────────────────────────────────


class DirectionsBody(BaseModel):
    inbound: bool = True
    outbound: bool = False


class ProfileWebhookIn(BaseModel):
    """Body for PUT /agents/{agent_id}/profile-webhook (upsert)."""

    endpoint_url: str = Field(..., min_length=1, max_length=500)
    http_method: Literal["GET", "POST"] = "POST"
    # Plaintext key→value; encrypted at rest by the service (full-replace).
    headers: Optional[dict[str, str]] = None
    request_identifiers: list[RequestIdentifierIn] = Field(default_factory=list)
    directions: DirectionsBody = Field(default_factory=DirectionsBody)
    timeout_seconds: int = Field(default=3, ge=1, le=30)
    is_enabled: bool = True


class WebhookTestIn(BaseModel):
    sample_phone: str = Field(..., min_length=3, max_length=32)


# ── Helpers ─────────────────────────────────────────────────────────────


def _handle_profile_webhook_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProfileWebhookNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_WEBHOOK_NOT_FOUND", "message": str(exc)},
        )
    if isinstance(exc, ProfileWebhookInvalidError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PROFILE_WEBHOOK_INVALID", "message": str(exc)},
        )
    raise exc  # not ours — bubble up


# ── Routes ──────────────────────────────────────────────────────────────


@router.get("/agents/{agent_id}/profile-webhook")
def get_profile_webhook(
    agent_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """The agent's webhook config (with decrypted headers for the owner's edit
    form), or ``{"webhook": null}`` when none is configured."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileWebhookService(db, org_id=org_id)
    row = svc.get_webhook(agent_id)
    return {"webhook": svc.webhook_response(row) if row else None}


@router.put("/agents/{agent_id}/profile-webhook")
def upsert_profile_webhook(
    agent_id: UUID,
    body: ProfileWebhookIn = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create or replace the agent's webhook config. Headers are full-replaced
    and stored encrypted."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileWebhookService(db, org_id=org_id)
    try:
        row = svc.upsert_webhook(
            agent_id,
            endpoint_url=body.endpoint_url,
            http_method=body.http_method,
            headers=body.headers,
            request_identifiers=[i.model_dump(by_alias=True) for i in body.request_identifiers],
            directions=body.directions.model_dump(),
            timeout_seconds=body.timeout_seconds,
            is_enabled=body.is_enabled,
        )
    except ProfileWebhookInvalidError as exc:
        raise _handle_profile_webhook_error(exc) from exc
    return svc.webhook_response(row)


@router.delete(
    "/agents/{agent_id}/profile-webhook",
    status_code=status.HTTP_200_OK,
)
def delete_profile_webhook(
    agent_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileWebhookService(db, org_id=org_id)
    try:
        svc.delete_webhook(agent_id)
    except ProfileWebhookNotFoundError as exc:
        raise _handle_profile_webhook_error(exc) from exc
    return {"deleted": True}


@router.post("/agents/{agent_id}/profile-webhook/test")
async def test_profile_webhook(
    agent_id: UUID,
    body: WebhookTestIn = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Call the SAVED webhook with a sample phone and report the raw response +
    per-configured-path resolution (save before testing)."""
    org_id = resolve_org_id(claims)
    ensure_agent_in_org(db, org_id, agent_id)
    svc = AgentProfileWebhookService(db, org_id=org_id)
    try:
        return await svc.test_webhook(agent_id, body.sample_phone)
    except ProfileWebhookNotFoundError as exc:
        raise _handle_profile_webhook_error(exc) from exc
