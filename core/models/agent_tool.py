import uuid

from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentTool(OrgScopedModel):
    __tablename__ = "agent_tools"
    __table_args__ = (
        UniqueConstraint("agent_config_id", "tool_id", name="uq_agent_tools_config_tool"),
        Index("ix_agent_tools_agent_id", "agent_id"),
        Index("ix_agent_tools_tool_id", "tool_id"),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=True)
    # Per-version OAuth override. When set, runtime resolution uses this in
    # preference to ``tools.oauth_connection_id`` (the default from the Tools
    # page). See ``core/utils/oauth_resolution.py``.
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tool_id": str(self.tool_id) if self.tool_id else None,
            "agent_config_id": str(self.agent_config_id) if self.agent_config_id else None,
            "oauth_connection_id": str(self.oauth_connection_id) if self.oauth_connection_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
