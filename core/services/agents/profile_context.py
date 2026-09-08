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

from core.services.agents.agent_profile_crm_config_service import (
    AgentProfileCrmConfigService,
)
from core.services.agents.agent_profile_variable_service import (
    AgentProfileVariableService,
)
from core.services.agents.profile_crm_enrichment_service import ProfileCrmPlan


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


def load_profile_crm_plan(
    db: Session,
    org_id: Optional[Union[str, UUID]],
    agent_id: Optional[Union[str, UUID]],
) -> ProfileCrmPlan:
    """Build the per-call CRM enrichment plan (sync DB reads only).

    Returns a disabled ``ProfileCrmPlan`` when enrichment is off, unconfigured,
    there are no empty mapped variables, or on any DB error — so the caller can
    unconditionally start enrichment and it simply no-ops. The actual CRM call
    is done separately (async) by ``ProfileCrmEnrichmentService.enrich``.
    """
    if not agent_id or not org_id:
        return ProfileCrmPlan()
    try:
        config = AgentProfileCrmConfigService(db, org_id=org_id).get_config(agent_id)
        if config is None or not config.is_enabled:
            return ProfileCrmPlan()
        fill_plan = AgentProfileVariableService(db, org_id=org_id).get_crm_fill_plan(
            agent_id
        )
        if not fill_plan:
            return ProfileCrmPlan()
        # Resolve the CRM slug (hubspot/salesforce/zoho_crm) so the async enrich
        # step can pick the per-CRM preset without a second DB hit. None = a
        # custom MCP → generic single-phone-argument flow.
        crm_slug = None
        if config.mcp_server_id:
            from core.services.mcp_server_service import McpServerService

            crm_slug = McpServerService(db, org_id=org_id).get_integration_slug(
                config.mcp_server_id
            )
        return ProfileCrmPlan(
            enabled=True,
            mcp_server_id=config.mcp_server_id,
            lookup_tool_name=config.lookup_tool_name,
            phone_argument=config.phone_argument,
            crm_slug=crm_slug,
            fill_plan=fill_plan,
        )
    except Exception:  # noqa: BLE001 — resolver must never break a call
        logger.exception(
            "[profile-crm] plan load failed org={} agent={}", org_id, agent_id
        )
        return ProfileCrmPlan()
