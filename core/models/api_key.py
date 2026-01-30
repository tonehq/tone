from sqlalchemy import Column, BigInteger, String, Boolean, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.models.base import TimestampModel


class ApiKey(TimestampModel):
    __tablename__ = 'api_keys'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    service_provider_id = Column(BigInteger, ForeignKey('service_providers.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    api_key_encrypted = Column(Text, nullable=False)
    api_key_hint = Column(String)
    additional_credentials = Column(JSONB)
    status = Column(String, default='active')
    is_valid = Column(Boolean, default=False)
    last_validated_at = Column(BigInteger)
    validation_error = Column(Text)
    last_used_at = Column(BigInteger)
    usage_count = Column(Integer, default=0)
    rate_limit_config = Column(JSONB)
    created_by = Column(BigInteger, ForeignKey('users.id'))
    expires_at = Column(BigInteger)

