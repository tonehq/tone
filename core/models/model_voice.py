import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class ModelVoice(TimestampModel):
    __tablename__ = "model_voices"

    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    accent = Column(String(120), nullable=True)
    name = Column(String(200), nullable=True)
    gender = Column(String(200), nullable=True)
    description = Column(String(200), nullable=True)
    language_list = Column(JSONB, nullable=True)
    sample_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # relationships
    model = relationship("Model", back_populates="voices")
