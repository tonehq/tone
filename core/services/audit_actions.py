"""Canonical action names for the audit log.

Centralises every action string so the rest of the codebase doesn't sprinkle
free-form literals across services. The action strings double as filter
values in the read API and labels in the UI, so renaming one here is the
single point of change.

Naming convention: ``<resource>.<sub_resource?>.<verb>`` — verbs are past
tense and resource-scoped (e.g. ``agent.tool.attached``, not
``attached_tool``).
"""
from typing import Final


class AgentAuditAction:
    """Actions emitted from the agent-edit surface (v1 scope)."""

    # Root agent
    CREATED: Final[str] = "agent.created"
    UPDATED: Final[str] = "agent.updated"
    DELETED: Final[str] = "agent.deleted"

    # Config content (prompt, model/voice/stt settings, etc.)
    CONFIG_UPDATED: Final[str] = "agent.config.updated"

    # Versioning
    VERSION_CREATED: Final[str] = "agent.version.created"
    VERSION_UPDATED: Final[str] = "agent.version.updated"
    VERSION_SWITCHED: Final[str] = "agent.version.switched"
    VERSION_DELETED: Final[str] = "agent.version.deleted"

    # Attachments — one row per resource diff
    TOOL_ATTACHED: Final[str] = "agent.tool.attached"
    TOOL_DETACHED: Final[str] = "agent.tool.detached"
    MCP_ATTACHED: Final[str] = "agent.mcp.attached"
    MCP_DETACHED: Final[str] = "agent.mcp.detached"
    KB_ATTACHED: Final[str] = "agent.knowledge_base.attached"
    KB_DETACHED: Final[str] = "agent.knowledge_base.detached"
    PHONE_ATTACHED: Final[str] = "agent.phone_number.attached"
    PHONE_DETACHED: Final[str] = "agent.phone_number.detached"
    WEB_CHANNEL_ATTACHED: Final[str] = "agent.web_channel.attached"
    WEB_CHANNEL_DETACHED: Final[str] = "agent.web_channel.detached"


class AuditResourceType:
    """Values for ``audit_logs.target_resource_type``."""

    TOOL: Final[str] = "tool"
    MCP_SERVER: Final[str] = "mcp_server"
    KNOWLEDGE_BASE: Final[str] = "knowledge_base"
    PHONE_NUMBER: Final[str] = "phone_number"
    WEB_CHANNEL: Final[str] = "web_channel"
    AGENT_CONFIG: Final[str] = "agent_config"
