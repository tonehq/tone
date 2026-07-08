import uuid

from sqlalchemy import Column, Index, String, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class PhoneNumber(OrgScopedModel):
    __tablename__ = "phone_numbers"
    __table_args__ = (
        UniqueConstraint("organization_id", "number", name="uq_phone_numbers_org_number"),
        # A number can be ASSIGNED to only one agent globally — inbound calls route by
        # number alone, so a cross-org duplicate assignment routes non-deterministically.
        # Partial (agent_id IS NOT NULL) so unassigned numbers may still exist per-org.
        Index(
            "uq_phone_numbers_assigned_number",
            "number",
            unique=True,
            postgresql_where=text("agent_id IS NOT NULL"),
        ),
    )

    number = Column(String(20), nullable=False)  # E.164
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    label = Column(String(200), nullable=True)
