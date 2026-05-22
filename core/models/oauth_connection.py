import uuid

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
