import uuid

from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentChannel(OrgScopedModel):
    __tablename__ = 'agent_channels'
    __table_args__ = (
        UniqueConstraint('organization_id', 'agent_id', 'channel_id', name='agent_channel_org_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=False)
    channel_id = Column(BigInteger, ForeignKey('channels.id'), nullable=False)
