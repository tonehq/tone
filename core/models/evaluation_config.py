from sqlalchemy import Boolean, Column, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from core.models.base import OrgScopedModel, SoftDeleteMixin


class EvaluationConfig(OrgScopedModel, SoftDeleteMixin):
    """A reusable, org-wide judge recipe for re-grading a frozen RAG eval run.

    The answered dataset (an ``eval_results`` run) is the fixed source; a
    config is the controlled variable — a different judge model, an optional
    custom rubric prompt, and a metric set — so the same answers can be
    scored many ways and compared (LangSmith's Evaluator concept).

    Only *judge* knobs live here — never retrieval/answer knobs (``top_k`` /
    ``answer_model``): the source run's answers are frozen, so re-retrieving
    or re-answering is meaningless. ``judge_prompt`` is threaded to the
    GEval ``correctness`` metric as its criterion (the one DeepEval hook that
    accepts free text); it runs alongside the ticked built-in metrics.
    """

    __tablename__ = "evaluation_configs"
    __table_args__ = (
        # Unique per org among live rows only — a soft-deleted name can be reused.
        Index(
            "uq_evaluation_configs_org_name_active",
            "organization_id",
            "name",
            unique=True,
            postgresql_where="is_active",
        ),
    )

    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    judge_model = Column(String(120), nullable=False)
    judge_engine = Column(String(32), nullable=False, default="deepeval")
    # Custom rubric text (GEval criterion). NULL = built-in metrics only.
    judge_prompt = Column(Text, nullable=True)
    # Subset of metric_registry.SUPPORTED_METRICS (RAG-safe ones).
    metrics_enabled = Column(JSONB, nullable=False, default=list)
    # The single v1 pass/fail bar applied to every metric (DeepEval takes one
    # scalar today).
    metric_threshold = Column(Float, nullable=False, default=0.7)
    # Reserved for per-metric thresholds later — stored, not yet applied.
    metric_thresholds = Column(JSONB, nullable=False, default=dict)
    is_default = Column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "name": self.name,
            "description": self.description,
            "judge_model": self.judge_model,
            "judge_engine": self.judge_engine,
            "judge_prompt": self.judge_prompt,
            "metrics_enabled": self.metrics_enabled or [],
            "metric_threshold": self.metric_threshold,
            "metric_thresholds": self.metric_thresholds or {},
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
