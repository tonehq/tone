import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class Call(OrgScopedModel):
    __tablename__ = "calls"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    agent_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Nullable at the schema level, but every real call log sets it: a `calls` row is
    # only created once the media stream connects (inbound and outbound alike), at which
    # point the channel is resolved. Unconnected outbound attempts live in scheduled_calls.
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=True)
    direction = Column(String(10), nullable=False)  # inbound | outbound
    from_phone_number_id = Column(UUID(as_uuid=True), ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True)
    to_phone_number_id = Column(UUID(as_uuid=True), ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True)
    from_number_raw_by_provider = Column(String(50), nullable=True)
    # Immutable snapshot of the dialed number at call time. Preserves history when
    # the linked PhoneNumber row is later reassigned or deleted (which SETs NULL on
    # to_phone_number_id via the FK). Read paths prefer this over the join.
    to_number = Column(String(50), nullable=True)
    provider_call_id = Column(String(120), nullable=True)
    # Correlates this call to its server logs (format: {short_uuid}-{agent_id}-{call_id}).
    trace_id = Column(String(120), nullable=True, index=True)
    # Nullable at the schema level for historical reasons; in practice it is always set
    # when the media stream starts (which is also when the row is created). Unconnected
    # outbound attempts never reach this table — they live in scheduled_calls.
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    recording_upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True)
    recording_duration_seconds = Column(Integer, nullable=True)
    pod_id = Column(UUID(as_uuid=True), ForeignKey("pods.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    pipeline_config = Column(JSONB, nullable=True)
    overlapped_calls = Column(JSONB, nullable=False, server_default="[]")
    # Derived per-turn view merging transcript + tool_executions + turn latency
    # (see ConsolidatedTranscriptService). Written by the ``consolidate_transcript``
    # post-call action; safe to recompute at any time.
    consolidated_transcript = Column(JSONB, nullable=True)

    pod = relationship("Pod", back_populates="calls")

    metrics_record = relationship(
        "CallMetrics",
        uselist=False,
        back_populates="call",
        cascade="all, delete-orphan",
    )
