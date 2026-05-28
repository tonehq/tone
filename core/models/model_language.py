import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class ModelLanguage(TimestampModel):
    __tablename__ = "model_languages"

    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # relationships
    model = relationship("Model", back_populates="languages")
