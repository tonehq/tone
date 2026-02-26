import uuid
from sqlalchemy import Column, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class ChannelPhoneNumbers(TimestampModel):
    __tablename__ = 'channel_phone_numbers'
    __table_args__ = (
        UniqueConstraint('channel_id', 'phone_number', name='channel_phone_numbers_channel_phone_unique'),
    )

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    channel_id = Column(BigInteger, ForeignKey('channels.id'), nullable=True)
    phone_number = Column(String, nullable=False)
    phone_number_sid = Column(String, nullable=False)
    phone_number_auth_token = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    country_code = Column(String, nullable=True)
    number_type = Column(String, nullable=True)
    capabilities = Column(JSONB, nullable=True)
    status = Column(String, default='active', nullable=True)


    channel = relationship("Channel", back_populates="phone_numbers")
