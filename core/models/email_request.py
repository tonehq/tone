import uuid

from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class EmailRequest(OrgScopedModel):
    __tablename__ = "email_requests"

    to_email = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    purpose = Column(String(50), nullable=False)  # verification | invite | reset | ...
    template_context = Column(JSONB, nullable=True)
    delivery_status = Column(String(50), nullable=False, default="pending")  # pending | sent | failed | bounced
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(500), nullable=True)
    token_hash = Column(String(255), nullable=True, unique=True)
    created_by_user_id = Column(String(50), nullable=True)  # human | system | automated | webhook
    expires_at = Column(DateTime(timezone=True), nullable=True)
