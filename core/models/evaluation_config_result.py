from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class EvaluationConfigResult(OrgScopedModel):
    """One re-graded question for one (config, source run) pass.

    Grading a source run with a config produces N of these rows (one per
    question), all sharing a ``config_run_id`` so a pass is addressable as a
    unit for compare / summary. ``source_run_id`` is the ``eval_results.run_id``
    whose frozen answers (``actual_answer`` + ``retrieved_chunks``) were
    re-judged — no retrieval or answer generation happens here.

    Standalone from ``eval_results`` on purpose: a source run stays an
    immutable single-config artifact; a config-result is a distinct concept
    (many per source run).
    """

    __tablename__ = "evaluation_config_results"
    __table_args__ = (
        Index("ix_evaluation_config_results_config_run", "config_run_id"),
        Index("ix_evaluation_config_results_source_run", "source_run_id"),
        Index(
            "ix_evaluation_config_results_config_run_number",
            "evaluation_config_id",
            "config_run_number",
        ),
    )

    # SET NULL so results survive if the config is later deleted.
    evaluation_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # The eval_results.run_id whose frozen answers were re-graded.
    source_run_id = Column(UUID(as_uuid=True), nullable=False)
    eval_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Batch id shared by all rows of one grading pass.
    config_run_id = Column(UUID(as_uuid=True), nullable=False)
    # Monotonic per (evaluation_config_id, source_run_id).
    config_run_number = Column(Integer, nullable=False)
    triggered_by = Column(String(32), nullable=False, default="manual")
    status = Column(String(16), nullable=False, default="completed")
    verdict = Column(String(16), nullable=True)
    judge_reasoning = Column(Text, nullable=True)
    # Full per-metric scorecard from the DeepEval judge.
    metric_scores = Column(JSONB, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "evaluation_config_id": (
                str(self.evaluation_config_id) if self.evaluation_config_id else None
            ),
            "source_run_id": str(self.source_run_id),
            "eval_id": str(self.eval_id),
            "config_run_id": str(self.config_run_id),
            "config_run_number": self.config_run_number,
            "triggered_by": self.triggered_by,
            "status": self.status,
            "verdict": self.verdict,
            "judge_reasoning": self.judge_reasoning,
            "metric_scores": self.metric_scores or {},
            "latency_ms": self.latency_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
