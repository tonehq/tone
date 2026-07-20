import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class ScheduledCall(OrgScopedModel):
    """A future outbound call, queued via Procrastinate.

    Kept separate from ``calls`` so the call-logs table holds only real call logs
    (created when a call actually connects). A scheduled call produces a ``calls``
    log only after it fires and connects; ``call_id`` links to that log.
    """

    __tablename__ = "scheduled_calls"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    # The contact this call targets, when scheduled from the Contacts page. SET NULL so
    # deleting a contact doesn't cascade-delete its scheduled-call history.
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    # scheduled | processing | dispatched | completed | busy | no_answer | failed | canceled
    status = Column(String(20), nullable=False, default="scheduled", index=True)
    provider = Column(String(20), nullable=False, default="twilio")
    provider_call_sid = Column(String(120), nullable=True)
    # The resulting call-log row, set once the scheduled call connects.
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True)
    queue_job_id = Column(Integer, nullable=True)
    error = Column(String(500), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
