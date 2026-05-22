import uuid

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Channel(OrgScopedModel):
    __tablename__ = "channels"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_channels_org_name"),
    )

    name = Column(String(120), nullable=False)
    channel_type = Column(String(50), nullable=False)  # daily | twilio | vonage | websocket
    encrypted_config = Column(JSONB, nullable=True)
