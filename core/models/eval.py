from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class Eval(OrgScopedModel):
    """One question in a KB upload's Q&A dataset — a doc that yields 50
    generator questions becomes 50 rows here. Regeneration replaces the set:
    delete rows matching ``upload_id``, insert the new batch.

    Row identity for a "set" of questions is the pair
    ``(upload_id, generation_prompt_hash)``; the generator-level metadata
    (``generated_by_model`` / ``generation_prompt_hash``) is denormalized on
    every row so filtering by "questions produced by gpt-4o" is a single
    scan with no join.
    """

    __tablename__ = "evals"
    __table_args__ = (
        UniqueConstraint("upload_id", "external_id", name="uq_evals_upload_external_id"),
        Index("ix_evals_upload_ord", "upload_id", "question_ord"),
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
        index=True,
    )
    external_id = Column(String(64), nullable=False)
    question_ord = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    expected_source_snippet = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    generated_by_model = Column(String(120), nullable=True)
    generation_prompt_hash = Column(String(64), nullable=True)
    extras = Column(JSONB, nullable=True)

    results = relationship(
        "EvalResult",
        back_populates="eval",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "knowledge_base_id": str(self.knowledge_base_id),
            "upload_id": str(self.upload_id),
            "external_id": self.external_id,
            "question_ord": self.question_ord,
            "question": self.question,
            "expected_answer": self.expected_answer,
            "expected_source_snippet": self.expected_source_snippet,
            "category": self.category,
            "generated_by_model": self.generated_by_model,
            "generation_prompt_hash": self.generation_prompt_hash,
            "extras": self.extras,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
