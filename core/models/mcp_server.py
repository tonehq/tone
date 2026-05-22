import uuid

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
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
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)
