import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, UUID

from core.database.base import Base


class UserSession(Base):
    """A single login from a single device.

    One row per ``/login``. Stays alive across ``/refresh`` calls (token
    rotates, row stays). Soft-deleted via ``revoked_at`` on logout and
    password change so the user-visible "recent activity" list keeps its
    history.

    The raw refresh token is never stored; only ``sha256`` of it lives in
    ``refresh_token_hash`` — that hash is the lookup handle for ``/refresh``
    and ``/logout``.

    The allowed values for ``revoked_reason`` live next to where they are
    set in ``SessionService`` (``user_logout``, ``user_logout_others``,
    ``password_change``, ``password_reset``, ``rotation_reuse``).
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "revoked_at"),
        Index("ix_user_sessions_user_last_used", "user_id", "last_used_at"),
        Index("ix_user_sessions_family", "refresh_token_family"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    refresh_token_hash = Column(String(64), nullable=False, unique=True)
    refresh_token_family = Column(UUID(as_uuid=True), nullable=False)

    issued_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(50), nullable=True)

    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(20), nullable=True)
    device_name = Column(String(120), nullable=True)
    browser = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    country = Column(String(2), nullable=True)
    city = Column(String(120), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def status(self) -> str:
        if self.revoked_at is not None:
            return "revoked"
        if self.expires_at and self.expires_at <= datetime.now(timezone.utc):
            return "expired"
        return "active"

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "status": self.status,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_reason": self.revoked_reason,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "device_type": self.device_type,
            "device_name": self.device_name,
            "browser": self.browser,
            "os": self.os,
            "country": self.country,
            "city": self.city,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
