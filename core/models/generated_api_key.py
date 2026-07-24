from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel, SoftDeleteMixin


class GeneratedApiKey(OrgScopedModel, SoftDeleteMixin):
    """Customer-facing API key for programmatic access to the Tone API.

    Distinct from ``ApiKey`` (which stores provider credentials for LLM/STT/TTS
    services). A row here represents one Bearer token a customer can send in
    ``Authorization: Bearer tone_sk_...`` to hit the API on behalf of their org.

    We store only the SHA-256 hash of the full key; the plaintext is returned
    exactly once on creation and is never recoverable. ``key_prefix`` is safe to
    show in the UI so users can tell keys apart.
    """

    __tablename__ = "generated_api_keys"

    name = Column(String(120), nullable=False)
    key_hash = Column(String(64), nullable=False)
    key_prefix = Column(String(20), nullable=False)
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    def status(self) -> str:
        if self.revoked_at is not None or not self.is_active:
            return "revoked"
        if self.expires_at is not None and self.expires_at <= datetime.now(timezone.utc):
            return "expired"
        return "active"

    def masked(self) -> str:
        return f"{self.key_prefix}{'•' * 20}"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "key_prefix": self.key_prefix,
            "masked": self.masked(),
            "status": self.status(),
            "created_by_user_id": str(self.created_by_user_id)
            if self.created_by_user_id
            else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
