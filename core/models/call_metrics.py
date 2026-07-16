from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class CallMetrics(OrgScopedModel):
    __tablename__ = "call_metrics"

    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    ttfb = Column(JSONB, nullable=True)
    processing = Column(JSONB, nullable=True)
    llm_usage = Column(JSONB, nullable=True)
    tts_usage = Column(JSONB, nullable=True)
    stt_usage = Column(JSONB, nullable=True)
    user_bot_latency = Column(JSONB, nullable=True)
    turns = Column(JSONB, nullable=True)
    turn_metrics = Column(JSONB, nullable=True)

    # Persisted avg/p50/p99 for TTFB + user-bot latency, computed at write
    # time from the raw arrays above. Read path prefers this over recomputing.
    computed_stats = Column(JSONB, nullable=True)

    # Per-call, per-series 3×3 stat blocks materialized by the post-call
    # ``compute_call_metrics_aggregates`` job. Each stores
    # ``{"unit": ..., "avg": {...}, "p50": {...}, "p99": {...}}``.
    # Read path (``CallMetricsAnalyticsService.summarize``) reads these
    # directly and falls back to inline compute from ``turn_metrics`` when
    # a row was written before the job ran.
    llm_series_stats = Column(JSONB, nullable=True)
    stt_series_stats = Column(JSONB, nullable=True)
    tts_series_stats = Column(JSONB, nullable=True)
    end_to_end_series_stats = Column(JSONB, nullable=True)

    call = relationship("Call", back_populates="metrics_record")
