from typing import Any, Dict

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel
from core.utils.encryption import decrypt_json


class Channel(OrgScopedModel):
    __tablename__ = "channels"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_channels_org_name"),
    )

    name = Column(String(120), nullable=False)
    channel_type = Column(String(50), nullable=False)  # twilio | telnyx | exotel | daily | websocket
    encrypted_config = Column(JSONB, nullable=True)

    def to_dict(self, include_config: bool = False) -> Dict[str, Any]:
        """List/preview response shape. Pass ``include_config=True`` to decrypt
        the credential payload (only used when editing a single record)."""
        data: Dict[str, Any] = {
            "id": str(self.id),
            "name": self.name,
            "channel_type": self.channel_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_config:
            data["config"] = decrypt_json(self.encrypted_config)
        return data
