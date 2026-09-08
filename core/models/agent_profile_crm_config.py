from sqlalchemy import Boolean, Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentProfileCrmConfig(OrgScopedModel):
    """Per-agent settings for filling empty profile variables from a CRM.

    One row per agent (``UNIQUE(agent_id)``). Holds the "where + how" of the
    lookup — which attached CRM (MCP) server to query, which tool to call, and
    which tool argument the caller's phone number is passed as — plus a master
    on/off switch. The "what" (which response field fills each variable) lives
    per-variable on ``AgentProfileVariable.crm_field``.

    Resolved at call start by ``load_profile_crm_plan`` /
    ``ProfileCrmEnrichmentService``; disabled or misconfigured rows degrade to
    a no-op so a call never fails.
    """

    __tablename__ = "agent_profile_crm_config"
    # UNIQUE(agent_id) already creates a supporting index — no separate agent_id
    # index needed (one row per agent).
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_agent_profile_crm_config_agent"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The attached CRM (MCP) server to query. SET NULL if the server is deleted
    # so the config row survives (enrichment simply no-ops until re-pointed).
    mcp_server_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mcp_servers.id", ondelete="SET NULL"),
        nullable=True,
    )
    lookup_tool_name = Column(String(200), nullable=True)
    phone_argument = Column(String(120), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "mcp_server_id": str(self.mcp_server_id) if self.mcp_server_id else None,
            "lookup_tool_name": self.lookup_tool_name,
            "phone_argument": self.phone_argument,
            "is_enabled": bool(self.is_enabled),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
