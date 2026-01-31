from sqlalchemy import Column, BigInteger, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.models.base import TimestampModel


class ServiceProvider(TimestampModel):
    __tablename__ = 'service_providers'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    provider_type = Column(String, nullable=False)
    logo_url = Column(String)
    website_url = Column(String)
    documentation_url = Column(String)
    base_url = Column(String)
    auth_type = Column(String, nullable=False)
    supports_streaming = Column(Boolean, default=False)
    config_schema = Column(JSONB)
    status = Column(String, default='active')
    is_system = Column(Boolean, default=False)

