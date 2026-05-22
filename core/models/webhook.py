import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Webhook(OrgScopedModel):
    __tablename__ = "webhooks"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    webhook_type = Column(String(50), nullable=False)  # call | status | ...
    trigger_events = Column(String(200), nullable=True)
    endpoint_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
