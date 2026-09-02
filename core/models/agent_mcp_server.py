from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentMcpServer(OrgScopedModel):
    __tablename__ = "agent_mcp_servers"
    __table_args__ = (
        UniqueConstraint("agent_config_id", "mcp_server_id", name="uq_agent_mcp_config_server"),
        Index("ix_agent_mcp_servers_agent_id", "agent_id"),
        Index("ix_agent_mcp_servers_mcp_server_id", "mcp_server_id"),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=False)
    mcp_server_id = Column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "agent_config_id": str(self.agent_config_id) if self.agent_config_id else None,
            "mcp_server_id": str(self.mcp_server_id) if self.mcp_server_id else None,
            "oauth_connection_id": str(self.oauth_connection_id) if self.oauth_connection_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
