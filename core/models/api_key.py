import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class ApiKey(OrgScopedModel):
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider_id", "label", name="uq_api_keys_org_provider_label"),
    )

    provider_id = Column(UUID(as_uuid=True), ForeignKey("model_providers.id"), nullable=False)
    label = Column(String(80), nullable=True)
    encrypted_key = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
