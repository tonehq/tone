import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Call(OrgScopedModel):
    __tablename__ = "calls"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False)
    direction = Column(String(10), nullable=False)  # inbound | outbound
    from_phone_number_id = Column(UUID(as_uuid=True), ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True)
    to_phone_number_id = Column(UUID(as_uuid=True), ForeignKey("phone_numbers.id", ondelete="SET NULL"), nullable=True)
    from_number_raw_by_provider = Column(String(50), nullable=True)
    provider_call_id = Column(String(120), nullable=True)
    # Correlates this call to its server logs (format: {short_uuid}-{agent_id}-{call_id}).
    trace_id = Column(String(120), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    recording_upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True)
    recording_duration_seconds = Column(Integer, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
