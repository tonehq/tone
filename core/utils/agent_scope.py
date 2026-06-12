"""Reusable SQL helpers for scoping queries to an agent's published version.

Tools, MCP servers, and knowledge-base attachments are stored per-version
(``agent_tools.agent_config_id`` and friends). Every runtime / admin read of
those tables must filter to the agent's currently-published config so:

* live calls only see the published version's tools/MCP/KB,
* admin lists don't accidentally return the union across versions,
* drafts can never leak into a live conversation.

The same scalar subquery — ``SELECT published_config_id FROM agents WHERE
id = :agent_id`` — was being reimplemented in six different modules. This
helper centralises it so the per-version scoping invariant has exactly one
source of truth.
"""

from typing import Any

from sqlalchemy import select

from core.models.agent import Agent


def published_config_subquery(agent_id: Any):
    """Scalar subquery: the agent's currently-published ``AgentConfig.id``.

    Returns NULL for agents without a published version, which is exactly what
    we want — every per-version equality filter (``agent_config_id ==
    subquery``) then matches nothing, so unpublished agents contribute zero
    rows. Callers can use the result directly inside any SQLAlchemy
    ``filter(...)`` clause.
    """
    return (
        select(Agent.published_config_id)
        .where(Agent.id == agent_id)
        .scalar_subquery()
    )
