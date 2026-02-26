from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.models.base import TimestampModel


class GeneratedApiKey(TimestampModel):
    __tablename__ = 'generated_api_keys'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String, nullable=False)
    key_value = Column(Text, nullable=False)
    domains = Column(JSONB, nullable=True)
    abuse_prevention = Column(JSONB, nullable=True)
    fraud_protection = Column(Boolean, nullable=True)
