import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import TimestampModel


class ModelLanguage(TimestampModel):
    __tablename__ = "model_languages"
    __table_args__ = (
        # One language per (model, name). Matches the seed's dedup key (it skips
        # a language whose (model_id, name) already exists).
        UniqueConstraint("model_id", "name", name="uq_model_languages_model_name"),
    )

    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # relationships
    model = relationship("Model", back_populates="languages")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "model_id": str(self.model_id) if self.model_id else None,
            "name": self.name,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
