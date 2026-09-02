import uuid

from sqlalchemy import Column, String, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

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
    meta_data_schema = Column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "provider_id": self.provider_id,
            "slug": self.slug,
            "display_name": self.display_name,
            "description": self.description,
            "website_url": self.website_url,
            "is_active": self.is_active,
            "meta_data_schema": self.meta_data_schema,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
