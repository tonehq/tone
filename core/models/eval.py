from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class Eval(OrgScopedModel):
    """The Q&A dataset for one KB upload — one eval per upload
    (``UNIQUE(upload_id)``); regeneration replaces the row in-place."""

    __tablename__ = "evals"
    __table_args__ = (
        UniqueConstraint("upload_id", name="uq_evals_upload_id"),
    )

    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    question_count = Column(Integer, nullable=False, default=0)
    questions = Column(JSONB, nullable=False, default=dict)
    generated_by_model = Column(String(120), nullable=True)
    generation_prompt_hash = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="ready")
    error = Column(Text, nullable=True)

    results = relationship(
        "EvalResult",
        back_populates="eval",
        cascade="all, delete-orphan",
        order_by="EvalResult.run_number",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "knowledge_base_id": str(self.knowledge_base_id),
            "upload_id": str(self.upload_id),
            "name": self.name,
            "question_count": self.question_count,
            "generated_by_model": self.generated_by_model,
            "generation_prompt_hash": self.generation_prompt_hash,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
