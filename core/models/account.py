from sqlalchemy import Column, BigInteger, String, Boolean, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.models.base import OrgScopedModel


class Account(OrgScopedModel):
    __tablename__ = 'accounts'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    service_provider_id = Column(BigInteger, ForeignKey('service_providers.id', ondelete='CASCADE'), nullable=True)
    model_provider_menu_id = Column(BigInteger, ForeignKey('model_providers_menu.id'), nullable=True)
    hosting_provider_id = Column(BigInteger, ForeignKey('hosting_providers.id', ondelete='SET NULL'), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    service_type = Column(String, nullable=False)
    config = Column(JSONB, nullable=False, default={})
    status = Column(String, default='active')
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    tags = Column(JSONB)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(BigInteger)
    created_by = Column(BigInteger, ForeignKey('users.id'))
