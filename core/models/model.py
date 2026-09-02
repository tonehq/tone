import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class Model(TimestampModel):
    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("provider_id", "name", name="uq_models_provider_name"),
    )

    provider_id = Column(UUID(as_uuid=True), ForeignKey("model_providers.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(10), nullable=False)  # llm | stt | tts | embedding
    name = Column(String(120), nullable=False)
    display_name = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    meta_data = Column(JSONB, nullable=True)
    meta_data_schema = Column(JSONB, nullable=True)
    base_url = Column(String(500), nullable=True)

    # relationships
    provider = relationship("ModelProvider", backref="models", lazy="select")
    voices = relationship("ModelVoice", back_populates="model", cascade="all, delete-orphan")
    languages = relationship("ModelLanguage", back_populates="model", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "provider_id": str(self.provider_id) if self.provider_id else None,
            "kind": self.kind,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "is_active": self.is_active,
            "meta_data": self.meta_data,
            "meta_data_schema": self.meta_data_schema,
            "base_url": self.base_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
