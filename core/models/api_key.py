from sqlalchemy import Boolean, Column, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class ApiKey(OrgScopedModel):
    """Per-org credential for a global ModelProvider. Doubles as the "Service"
    entity on the Services page — the four nullable/defaulted columns
    (service_type, description, is_default, config) hold the per-row metadata
    the UI needs without forcing a separate ``services`` table."""

    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider_id", "label", name="uq_api_keys_org_provider_label"
        ),
    )

    provider_id = Column(
        UUID(as_uuid=True), ForeignKey("model_providers.id"), nullable=False
    )
    label = Column(String(80), nullable=True)
    encrypted_key = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    service_type = Column(String(20), nullable=True)  # llm | stt | tts
    description = Column(String(500), nullable=True)
    is_default = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    config = Column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    provider = relationship("ModelProvider", lazy="joined")

    def to_dict(self, kinds: list[str] | None = None) -> dict:
        """Serialize for API responses. NEVER includes encrypted_key.

        ``kinds`` is an optional list of distinct ``Model.kind`` values for the
        joined provider — passed in by the controller after a batched lookup
        to avoid N+1 queries on list endpoints.
        """
        provider_dict = None
        if self.provider is not None:
            provider_dict = {
                "id": str(self.provider.id),
                "slug": self.provider.slug,
                "display_name": self.provider.display_name,
            }
        return {
            "id": str(self.id),
            "label": self.label,
            "service_type": self.service_type,
            "description": self.description,
            "is_default": bool(self.is_default),
            "is_active": bool(self.is_active),
            "config": self.config or {},
            "provider": provider_dict,
            "kinds": kinds or [],
            "created_at": int(self.created_at.timestamp()) if self.created_at else None,
            "updated_at": int(self.updated_at.timestamp()) if self.updated_at else None,
        }
