from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class EvalResult(OrgScopedModel):
    """One scored answer for one question — a run over 50 questions writes 50
    rows here. All rows of the same run share ``run_id`` (a UUID stamped by
    the service) and the same ``run_number`` so the batch is addressable
    as a unit for compare / summary queries.

    ``ingestion_run_id`` pins the parser / tokeniser / embedder / vector-store
    recipe under test so a regression is attributable to that recipe.
    ``run_number`` is a per-``(upload_id, ingestion_run_id)`` monotonic
    counter — the ``EvalService`` computes it before the batch begins.
    """

    __tablename__ = "eval_results"
    __table_args__ = (
        UniqueConstraint("run_id", "eval_id", name="uq_eval_results_run_question"),
        Index("ix_eval_results_run_id", "run_id"),
        Index("ix_eval_results_ingestion_run_number", "ingestion_run_id", "run_number"),
        Index("ix_eval_results_ingestion_run_verdict", "ingestion_run_id", "verdict"),
        Index("ix_eval_results_eval_run_desc", "eval_id", text("run_number DESC")),
    )

    eval_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingestion_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_id = Column(UUID(as_uuid=True), nullable=False)
    run_number = Column(Integer, nullable=False)
    triggered_by = Column(String(32), nullable=False)  # 'auto' | 'manual' | 'cli'
    top_k = Column(Integer, nullable=False)
    answer_model = Column(String(120), nullable=True)
    judge_model = Column(String(120), nullable=True)
    status = Column(String(16), nullable=False, default="completed")
    actual_answer = Column(Text, nullable=True)
    retrieval_hit = Column(Boolean, nullable=False, default=False)
    retrieved_chunks = Column(JSONB, nullable=True)
    verdict = Column(String(16), nullable=True)
    correctness = Column(Float, nullable=True)
    groundedness = Column(Float, nullable=True)
    relevance = Column(Float, nullable=True)
    judge_reasoning = Column(Text, nullable=True)
    # Full per-metric scorecard from the DeepEval judge (one entry per enabled
    # metric: {"score", "verdict", "reason"}). NULL for legacy-judge rows.
    metric_scores = Column(JSONB, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    retrieval_error = Column(Text, nullable=True)
    answer_error = Column(Text, nullable=True)
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
            "ingestion_run_id": str(self.ingestion_run_id) if self.ingestion_run_id else None,
            "run_id": str(self.run_id),
            "run_number": self.run_number,
            "triggered_by": self.triggered_by,
            "top_k": self.top_k,
            "answer_model": self.answer_model,
            "judge_model": self.judge_model,
            "status": self.status,
            "actual_answer": self.actual_answer,
            "retrieval_hit": self.retrieval_hit,
            "retrieved_chunks": self.retrieved_chunks,
            "verdict": self.verdict,
            "correctness": self.correctness,
            "groundedness": self.groundedness,
            "relevance": self.relevance,
            "judge_reasoning": self.judge_reasoning,
            "metric_scores": self.metric_scores or {},
            "latency_ms": self.latency_ms,
            "retrieval_error": self.retrieval_error,
            "answer_error": self.answer_error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
