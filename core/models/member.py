import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from core.database.base import Base


class Member(Base):
    """Organization membership — mirrors tone-test's OrganizationMember.

    Table name kept as ``members`` (rather than ``organization_members``) to
    avoid breaking the rest of the tone codebase that already references
    ``Member`` / ``members``.
    """

    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_members_user_org"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False, default="developer")
    is_default = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    joined_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("timezone('utc', now())"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "organization_id": str(self.organization_id),
            "role": self.role,
            "is_default": self.is_default,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }
