import uuid

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class PhoneNumber(OrgScopedModel):
    __tablename__ = "phone_numbers"
    __table_args__ = (
        UniqueConstraint("organization_id", "number", name="uq_phone_numbers_org_number"),
    )

    number = Column(String(20), nullable=False)  # E.164
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    label = Column(String(200), nullable=True)
