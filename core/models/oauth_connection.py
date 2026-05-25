from typing import Any, Dict

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class OAuthConnection(OrgScopedModel):
    __tablename__ = "oauth_connections"

    provider_slug = Column(String(80), nullable=False)
    label = Column(String(80), nullable=True)
    auth_type = Column(String(30), nullable=False)  # oauth | api_key | bearer
    encrypted_credentials = Column(JSONB, nullable=True)
    public_metadata = Column(JSONB, nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Public response shape. Never includes ``encrypted_credentials``."""
        return {
            "id": str(self.id),
            "provider_slug": self.provider_slug,
            "label": self.label,
            "auth_type": self.auth_type,
            "public_metadata": self.public_metadata or {},
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
