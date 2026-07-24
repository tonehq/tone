from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class EvalResult(OrgScopedModel):
    """One run of an eval. ``ingestion_run_id`` pins the specific pipeline
    recipe (parser / tokeniser / embedder / vector-store) under test so a
    regression can be attributed to that recipe."""

    __tablename__ = "eval_results"
    __table_args__ = (
        UniqueConstraint("eval_id", "run_number", name="uq_eval_results_eval_run"),
        Index("ix_eval_results_ingestion_run_status", "ingestion_run_id", "status"),
        Index("ix_eval_results_eval_run_desc", "eval_id", text("run_number DESC")),
    )

    eval_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evals.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_number = Column(Integer, nullable=False)
    ingestion_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    triggered_by = Column(String(32), nullable=False)  # 'auto' | 'manual' | 'cli'
    top_k = Column(Integer, nullable=False)
    answer_model = Column(String(120), nullable=True)
    judge_model = Column(String(120), nullable=True)
    status = Column(String(32), nullable=False, default="running")
    summary = Column(JSONB, nullable=True)
    per_question = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    eval = relationship("Eval", back_populates="results")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "eval_id": str(self.eval_id),
            "run_number": self.run_number,
            "ingestion_run_id": str(self.ingestion_run_id) if self.ingestion_run_id else None,
            "triggered_by": self.triggered_by,
            "top_k": self.top_k,
            "answer_model": self.answer_model,
            "judge_model": self.judge_model,
            "status": self.status,
            "summary": self.summary,
            "per_question": self.per_question,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
