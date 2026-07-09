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
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False)
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
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    recording_upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True)
    recording_duration_seconds = Column(Integer, nullable=True)
    pod_id = Column(UUID(as_uuid=True), ForeignKey("pods.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    pipeline_config = Column(JSONB, nullable=True)

    pod = relationship("Pod", back_populates="calls")

    metrics_record = relationship(
        "CallMetrics",
        uselist=False,
        back_populates="call",
        cascade="all, delete-orphan",
    )
