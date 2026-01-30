import uuid
from sqlalchemy import Column, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database.base import Base
from core.models.base import TimestampModel


class AgentPhoneNumbers(TimestampModel):
    __tablename__ = 'agent_phone_numbers'
    __table_args__ = (
        UniqueConstraint('agent_id', 'phone_number', name='agent_phone_numbers_agent_phone_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    agent_id = Column(BigInteger, ForeignKey('agents.id'), nullable=False)
    phone_number = Column(String, nullable=False, unique=True)
    phone_number_sid = Column(String, nullable=False)
    phone_number_auth_token = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    country_code = Column(String, nullable=True)
    number_type = Column(String, nullable=True)
    capabilities = Column(JSONB, nullable=True)
    status = Column(String, default='active', nullable=True)
