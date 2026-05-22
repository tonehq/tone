import uuid

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class Invite(OrgScopedModel):
    __tablename__ = "invites"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_invites_org_email"),
    )

    email = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | accepted | expired | revoked
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email_request_id = Column(UUID(as_uuid=True), ForeignKey("email_requests.id", ondelete="SET NULL"), nullable=True)
