from sqlalchemy import Column, BigInteger, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.models.base import TimestampModel


class HostingProvider(TimestampModel):
    __tablename__ = 'hosting_providers'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    logo_url = Column(String)
    website_url = Column(String)
    status = Column(String, default='active')
    is_system = Column(Boolean, default=False)
