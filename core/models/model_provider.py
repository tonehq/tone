import uuid

from sqlalchemy import Column, String, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import TimestampModel


class ModelProvider(TimestampModel):
    __tablename__ = "model_providers"
    __table_args__ = (
        UniqueConstraint("provider_id", name="uq_model_providers_provider_id"),
    )

    provider_id = Column(String(50), nullable=False)
    slug = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    website_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
