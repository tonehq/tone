import uuid

from sqlalchemy import Boolean, Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class McpServer(OrgScopedModel):
    __tablename__ = "mcp_servers"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_mcp_servers_org_name"),
    )

    name = Column(String(120), nullable=False)
    description = Column(String(200), nullable=True)
    server_url = Column(String(500), nullable=False)
    endpoint = Column(String(500), nullable=True)
    icon = Column(String(255), nullable=True)
    transport_type = Column(String(50), nullable=False, default="streamable_http")
    auth_type = Column(String(50), nullable=True, default="none")
    auth_config = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)
    app_integration_id = Column(UUID(as_uuid=True), ForeignKey("app_integrations.id", ondelete="SET NULL"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "name": self.name,
            "description": self.description,
            "server_url": self.server_url,
            "endpoint": self.endpoint,
            "icon": self.icon,
            "transport_type": self.transport_type,
            "auth_type": self.auth_type,
            "auth_config": self.auth_config,
            "meta_data": self.meta_data,
            "is_active": self.is_active,
            "oauth_connection_id": str(self.oauth_connection_id) if self.oauth_connection_id else None,
            "app_integration_id": str(self.app_integration_id) if self.app_integration_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
