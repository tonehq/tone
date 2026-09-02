import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class ModelVoice(TimestampModel):
    __tablename__ = "model_voices"

    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    voice_id = Column(String(200), nullable=True)
    accent = Column(String(120), nullable=True)
    name = Column(String(200), nullable=True)
    gender = Column(String(200), nullable=True)
    description = Column(String(200), nullable=True)
    language_list = Column(JSONB, nullable=True)
    sample_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # relationships
    model = relationship("Model", back_populates="voices")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "model_id": str(self.model_id) if self.model_id else None,
            "voice_id": self.voice_id,
            "accent": self.accent,
            "name": self.name,
            "gender": self.gender,
            "description": self.description,
            "language_list": self.language_list,
            "sample_url": self.sample_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
