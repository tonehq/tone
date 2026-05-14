from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, JSONB

from core.models.base import TimestampModel


class ModelMenu(TimestampModel):
    __tablename__ = 'model_menu'

    model_provider_menu_id = Column(BigInteger, ForeignKey('model_providers_menu.id'), nullable=False)
    name = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    status = Column(String, default='active')
    service_type = Column(String, nullable=True)
    meta_data_schema = Column(JSONB, nullable=True)
    auth_meta_data = Column(JSON, nullable=True)
    endpoint_url = Column(String, nullable=True)
