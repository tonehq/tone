import uuid

from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel, TimestampModel


class McpServer(OrgScopedModel):
    __tablename__ = 'mcp_servers'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    server_url = Column(String, nullable=False)
    transport_type = Column(String, nullable=False, default='streamable_http')
    auth_config = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    # timeout


class AgentMcpServer(TimestampModel):
    __tablename__ = 'agent_mcp_servers'

    agent_id = Column(BigInteger, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    mcp_server_id = Column(BigInteger, ForeignKey('mcp_servers.id', ondelete='CASCADE'), nullable=False, index=True)
    selected_tools = Column(JSONB, nullable=True)
