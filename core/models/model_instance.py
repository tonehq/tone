from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.models.base import TimestampModel


class ModelInstance(TimestampModel):
    __tablename__ = 'model_instance'

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    model_menu_id = Column(BigInteger, ForeignKey('model_menu.id'), nullable=False)
    account_id = Column(BigInteger, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=True)
    host_region = Column(String, nullable=True)
    endpoint_url = Column(String, nullable=True)
    status = Column(String, default='active')
    meta_data = Column(JSONB, nullable=True)
