import uuid

from sqlalchemy import Boolean, Column, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Tool(OrgScopedModel):
    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_tools_org_name"),
    )

    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    tool_type = Column(String(80), nullable=False)
    parameters = Column(JSONB, nullable=True)
    url = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True, default="POST")
    auth_type = Column(String(50), nullable=True, default="none")
    auth_config = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    is_template = Column(Boolean, nullable=False, default=False)
    mcp_server_id = Column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=True)
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)
    app_integration_id = Column(UUID(as_uuid=True), ForeignKey("app_integrations.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "parameters": self.parameters,
            "url": self.url,
            "method": self.method,
            "auth_type": self.auth_type,
            "auth_config": self.auth_config,
            "meta_data": self.meta_data,
            "is_template": self.is_template,
            "mcp_server_id": str(self.mcp_server_id) if self.mcp_server_id else None,
            "oauth_connection_id": str(self.oauth_connection_id) if self.oauth_connection_id else None,
            "app_integration_id": str(self.app_integration_id) if self.app_integration_id else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
