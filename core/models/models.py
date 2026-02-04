import uuid

from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON

from core.database.base import Base
from core.models.base import TimestampModel


class Model(TimestampModel):
    __tablename__ = "models"

    service_provider_id = Column(BigInteger, ForeignKey("service_providers.id"), nullable=False)
    name = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    api_key_id = Column(BigInteger, ForeignKey('api_keys.id', ondelete='SET NULL'))
    status = Column(String, default='active')
    service_type = Column(String, nullable=True)
