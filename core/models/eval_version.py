from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class EvalVersion(OrgScopedModel):
    """One version of a KB upload's eval question set.

    Each generation (or manual/imported set) is a version. Questions
    (``Eval`` rows) point at a version via ``eval_version_id``; a version is the
    unit the user reviews and approves. Versions are numbered per upload
    (``version_number`` = 1, 2, 3 …).

    ``status`` lifecycle: ``generating`` (async job running) → ``draft``
    (questions ready, under review) → ``finalized`` (reviewed). Evals are a
    QA/testing artifact only — nothing here is used at live agent runtime.
    """

    __tablename__ = "eval_versions"
    __table_args__ = (
        UniqueConstraint("upload_id", "version_number", name="uq_eval_versions_upload_number"),
        Index("ix_eval_versions_upload", "upload_id"),
    )

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    # 'generated' (LLM) | 'manual' | 'imported'
    source = Column(String(32), nullable=False, default="generated")
    # 'generating' | 'draft' | 'finalized'
    status = Column(String(16), nullable=False, default="draft")
    # The user's custom generation instructions for this version (nullable).
    generation_instructions = Column(Text, nullable=True)
    generated_by_model = Column(String(120), nullable=True)
    generation_prompt_hash = Column(String(64), nullable=True)

    evals = relationship(
        "Eval",
        back_populates="version",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "upload_id": str(self.upload_id),
            "knowledge_base_id": str(self.knowledge_base_id),
            "version_number": self.version_number,
            "source": self.source,
            "status": self.status,
            "generation_instructions": self.generation_instructions,
            "generated_by_model": self.generated_by_model,
            "generation_prompt_hash": self.generation_prompt_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
