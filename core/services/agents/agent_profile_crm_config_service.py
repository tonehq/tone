"""``AgentProfileCrmConfigService`` — the per-agent CRM lookup settings used to
fill empty profile variables at call start.

One row per agent (``UNIQUE(agent_id)``). Transport-agnostic: takes a session +
org context via ``BaseService``; every query is org-scoped via ``self.query()``.
Errors are TYPED (``ProfileCrmConfigInvalidError``); the route layer maps them
to HTTP status codes — never raise ``HTTPException`` here.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from core.models.agent_profile_crm_config import AgentProfileCrmConfig
from core.services.agents.errors import ProfileCrmConfigInvalidError
from core.services.base import BaseService

MAX_TOOL_NAME_LEN = 200
MAX_PHONE_ARG_LEN = 120


class AgentProfileCrmConfigService(BaseService):
    """Get/upsert the single CRM-lookup config row for an agent."""

    def get_config(self, agent_id: UUID) -> Optional[AgentProfileCrmConfig]:
        return (
            self.query(AgentProfileCrmConfig)
            .filter(AgentProfileCrmConfig.agent_id == agent_id)
            .first()
        )

    def upsert_config(
        self,
        agent_id: UUID,
        *,
        mcp_server_id: Optional[UUID] = None,
        lookup_tool_name: Optional[str] = None,
        phone_argument: Optional[str] = None,
        is_enabled: bool = False,
    ) -> AgentProfileCrmConfig:
        """Create or update the agent's CRM-lookup config.

        When ``is_enabled`` is true the config must be usable, so
        ``mcp_server_id`` (attached to this agent) + ``lookup_tool_name`` +
        ``phone_argument`` are required. A disabled config may be saved partial
        (draft) so the user can fill it in over multiple edits.
        """
        clean_tool = _validate_len(lookup_tool_name, MAX_TOOL_NAME_LEN, "Lookup tool name")
        clean_arg = _validate_len(phone_argument, MAX_PHONE_ARG_LEN, "Phone argument")

        if is_enabled:
            if not mcp_server_id or not clean_tool or not clean_arg:
                raise ProfileCrmConfigInvalidError(
                    "To enable CRM enrichment, choose a CRM server, a lookup tool, "
                    "and the phone argument."
                )
            self._ensure_server_attached(agent_id, mcp_server_id)
        elif mcp_server_id:
            self._ensure_server_attached(agent_id, mcp_server_id)

        row = self.get_config(agent_id)
        if row is None:
            row = AgentProfileCrmConfig(
                organization_id=self.org_id,
                agent_id=agent_id,
                mcp_server_id=mcp_server_id,
                lookup_tool_name=clean_tool,
                phone_argument=clean_arg,
                is_enabled=is_enabled,
            )
            self.db.add(row)
        else:
            row.mcp_server_id = mcp_server_id
            row.lookup_tool_name = clean_tool
            row.phone_argument = clean_arg
            row.is_enabled = is_enabled

        try:
            self.db.commit()
        except IntegrityError as exc:
            # UNIQUE(agent_id) race — re-read and apply onto the winner.
            self.db.rollback()
            raise ProfileCrmConfigInvalidError(
                "Could not save CRM config; please retry."
            ) from exc
        self.db.refresh(row)
        return row

    def config_response(self, row: Optional[AgentProfileCrmConfig]) -> Optional[dict]:
        return row.to_dict() if row is not None else None

    def _ensure_server_attached(self, agent_id: UUID, mcp_server_id: UUID) -> None:
        """The chosen CRM must be an MCP server attached to this agent's
        published config (reuses the same scope the runtime lookup uses), so a
        forged id can't point enrichment at another org's server."""
        from core.models.agent_mcp_server import AgentMcpServer
        from core.utils.agent_scope import published_config_subquery

        attached = (
            self.query(AgentMcpServer)
            .filter(
                AgentMcpServer.agent_id == agent_id,
                AgentMcpServer.mcp_server_id == mcp_server_id,
                AgentMcpServer.agent_config_id == published_config_subquery(agent_id),
            )
            .first()
        )
        if attached is None:
            raise ProfileCrmConfigInvalidError(
                "The selected CRM server is not attached to this agent."
            )


def _validate_len(
    value: Optional[str], max_len: int, label: str
) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > max_len:
        raise ProfileCrmConfigInvalidError(f"{label} is too long (max {max_len}).")
    return value
