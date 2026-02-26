from uuid import UUID


import uuid

from sqlalchemy import Column, BigInteger, String, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel
from core.models.enums import ChannelType


class Channel(TimestampModel):
    __tablename__ = 'channels'

    uuid = Column[UUID](UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column[str](String, nullable=False)
    type = Column(Enum(ChannelType, name="channeltype", values_callable=lambda e: [i.name for i in e]), nullable=False)
    created_by = Column(BigInteger, nullable=True)
    meta_data = Column(JSONB, nullable=True, default={})

    phone_numbers = relationship("ChannelPhoneNumbers", back_populates="channel")
    agents = relationship("Agent", secondary="agent_channels", back_populates="channels")
