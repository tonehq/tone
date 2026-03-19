import uuid
from sqlalchemy import Column, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class AgentChannelPhoneNumbers(OrgScopedModel):
    __tablename__ = 'agent_channel_phone_numbers'
    __table_args__ = (
        UniqueConstraint('organization_id', 'channel_id', 'phone_number', name='agent_channel_phone_org_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    channel_id = Column(BigInteger, ForeignKey('channels.id'), nullable=True)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=True)
    phone_number = Column(String, nullable=False)
    phone_number_sid = Column(String, nullable=False)
    phone_number_auth_token = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    country_code = Column(String, nullable=True)
    number_type = Column(String, nullable=True)
    capabilities = Column(JSONB, nullable=True)
    status = Column(String, default='active', nullable=True)

    channel = relationship("Channel", back_populates="agent_phone_numbers")
