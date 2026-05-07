import uuid

from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel, TimestampModel


class Tool(OrgScopedModel):
    __tablename__ = 'tools'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    tool_type = Column(String, nullable=False, default='custom')
    parameters = Column(JSONB, nullable=True, default=dict)
    url = Column(String, nullable=True)
    method = Column(String, nullable=True, default='POST')
    auth_type = Column(String, nullable=True, default='none')
    auth_config = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)


class AgentTool(TimestampModel):
    __tablename__ = 'agent_tools'

    agent_id = Column(BigInteger, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    tool_id = Column(BigInteger, ForeignKey('tools.id', ondelete='CASCADE'), nullable=False, index=True)
