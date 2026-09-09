"""Shared loader for per-agent profile variables in the runtime pipeline.

Every runtime code path that resolves ``{{profile.<key>}}`` MUST call this
helper to obtain the context map. That way the load happens in ONE place and
never gets re-implemented per call site (per project rules).

Wired today:
- LLM prompt path — ``core/services/pipeline/runner/pipecat.py`` calls this
  and passes the map into ``build_call_context(profile_variables=...)``.

Not yet wired (staged, no runtime construction site):
- Workflow node substitution — ``core/services/pipeline/workflow/engine.py``
  substitutes tokens from ``ctx.variables`` only. Whoever wires
  ``WorkflowEngine`` into the runtime MUST seed ``WorkflowCallContext.variables``
  with ``load_profile_context(...)`` at engine start, otherwise
  ``{{profile.<key>}}`` tokens inserted via the frontend node drawer will
  render as literal text at call time. The frontend already offers those
  tokens in the workflow node picker, so the seam is user-visible.

On failure we log the traceback and return ``{}`` so an unavailable DB does
NOT crash a live call — unresolved ``{{profile.x}}`` tokens gracefully render
verbatim (the existing behavior for unknown keys in ``substitute_variables``).
"""

from __future__ import annotations

from typing import Optional, Union
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.services.agents.agent_profile_variable_service import (
    AgentProfileVariableService,
)


def load_profile_context(
    db: Session,
    org_id: Optional[Union[str, UUID]],
    agent_id: Optional[Union[str, UUID]],
) -> dict[str, str]:
    """Return the ``{"profile.<key>": <value>}`` map for an agent, or ``{}``.

    ``org_id`` / ``agent_id`` may be missing during synthetic / test flows —
    skip the load rather than raising, so those paths don't need to know
    about profile variables at all.
    """
    if not agent_id or not org_id:
        return {}
    try:
        return AgentProfileVariableService(db, org_id=org_id).get_variables_map(agent_id)
    except Exception:  # noqa: BLE001 — resolver must never break a call
        logger.exception(
            "[profile-vars] load failed org={} agent={}", org_id, agent_id
        )
        return {}
