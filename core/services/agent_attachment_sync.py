"""Shared agent↔entity attachment sync for the Tool and MCP-server services.

Both ``ToolService`` and ``McpServerService`` expose the same feature: an
optional ``agent_ids`` field on upsert that full-syncs the entity onto exactly
that set of agents' PUBLISHED versions, plus a ``get_agents_by_*`` reader that
feeds the edit form. The two only differ in the association model
(``AgentTool`` vs ``AgentMcpServer``), the FK column pointing at the entity, and
the attach/detach callables. This module holds the one copy of that logic so a
change to the sync semantics is made once.
"""

from typing import Any, Callable, Dict, List, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.models.agent import Agent


def sync_agent_attachments(
    db: Session,
    org_id: Any,
    *,
    link_model: Any,
    link_fk: Any,
    entity_id: Any,
    agent_ids: List,
    attach: Callable[[List[UUID]], int],
    detach: Callable[[List[UUID]], int],
) -> Tuple[List[str], Dict[str, int]]:
    """Full-sync ``entity_id``'s published-version attachments to ``agent_ids``.

    ``agent_ids`` becomes the exact set of agents whose PUBLISHED version carries
    the entity. ``attach`` / ``detach`` are the caller's own scoped methods
    (adapted to take a list of agent ids and return the count actually changed),
    so published-version resolution, scope validation, and per-agent audit
    logging stay in the owning service. State problems (unknown agent, no
    published version, missing scopes) come back as warning strings — the entity
    row is already saved and shouldn't be rolled back because one agent isn't
    attachable. Malformed ids are a caller bug and still raise 400.

    Returns ``(warnings, summary)`` where ``summary`` is
    ``{"attached": n, "detached": n}`` — what actually changed, so the client can
    confirm the sync did what the user expected.
    """
    try:
        desired = {UUID(str(a)) for a in agent_ids}
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_ids must be a list of agent UUIDs",
        )

    warnings: List[str] = []
    rows = (
        db.query(Agent.id, Agent.name, Agent.published_config_id)
        .filter(
            Agent.id.in_(desired),
            Agent.organization_id == org_id,
            Agent.deleted_at.is_(None),
        )
        .all()
    ) if desired else []
    unknown = desired - {r.id for r in rows}
    if unknown:
        warnings.append(
            "Unknown agents skipped: " + ", ".join(sorted(str(u) for u in unknown))
        )
    unpublished = sorted(r.name for r in rows if r.published_config_id is None)
    if unpublished:
        warnings.append(
            "Agents without a published version skipped (publish them first): "
            + ", ".join(unpublished)
        )
    attachable = {r.id for r in rows if r.published_config_id is not None}

    # Current = agents whose PUBLISHED config carries this entity. Draft /
    # historical versions are out of scope, mirroring attach/detach.
    current = {
        aid
        for (aid,) in db.query(link_model.agent_id)
        .join(Agent, Agent.id == link_model.agent_id)
        .filter(
            link_fk == entity_id,
            link_model.agent_config_id == Agent.published_config_id,
            Agent.organization_id == org_id,
        )
        .all()
    }

    to_add = sorted(attachable - current)
    to_remove = sorted(current - desired)
    attached = detached = 0
    if to_add:
        try:
            attached = attach(to_add)
        except HTTPException as exc:
            warnings.append(f"Attach failed: {exc.detail}")
    if to_remove:
        try:
            detached = detach(to_remove)
        except HTTPException as exc:
            warnings.append(f"Detach failed: {exc.detail}")
    return warnings, {"attached": attached, "detached": detached}


def get_attached_agents(
    db: Session,
    org_id: Any,
    *,
    link_model: Any,
    link_fk: Any,
    entity_id: Any,
) -> List[Dict[str, str]]:
    """Agents whose PUBLISHED version carries the entity — the same scope
    ``sync_agent_attachments`` reads and writes, so the edit form can round-trip
    the list without drift."""
    rows = (
        db.query(Agent.id, Agent.name)
        .join(link_model, link_model.agent_id == Agent.id)
        .filter(
            link_fk == entity_id,
            link_model.agent_config_id == Agent.published_config_id,
            Agent.organization_id == org_id,
            Agent.deleted_at.is_(None),
        )
        .order_by(Agent.name.asc())
        .all()
    )
    return [{"id": str(r.id), "name": r.name} for r in rows]
