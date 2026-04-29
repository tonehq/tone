import uuid

from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB

from core.models.base import TimestampModel


class Model(TimestampModel):
    __tablename__ = "models"

    service_provider_id = Column(BigInteger, ForeignKey("service_providers.id"), nullable=False)
    name = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    status = Column(String, default='active')
    service_type = Column(String, nullable=True)
    meta_data_schema = Column(JSONB, nullable=True)
    auth_meta_data = Column(JSON, nullable=True)
    endpoint_url = Column(String, nullable=True)
