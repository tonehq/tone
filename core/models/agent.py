from decimal import Decimal
from sqlalchemy import Column, BigInteger, String, Boolean, Enum, UniqueConstraint, Integer, Numeric
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.database.base import Base
from sqlalchemy import ForeignKey, Text
from core.models.base import TimestampModel
from core.models.enums import AgentType

class Agent(TimestampModel):
    __tablename__ = 'agents'
    __table_args__ = (
        UniqueConstraint('name', name='agent_name_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    is_public = Column(Boolean, default=False)
    tags = Column(JSONB, nullable=True)
    total_calls = Column(Integer, default=0)
    total_minutes = Column(Numeric(10, 2), default=0)
    average_rating = Column(Numeric(3, 2), default=0)
    created_by = Column(BigInteger, ForeignKey('users.id'))
    meta_data = Column(JSONB, nullable=True, default={})
    status = Column(String, nullable=True, default='active')
    agent_type = Column(Enum(AgentType, name="agenttype", values_callable=lambda e: [i.name for i in e]))

