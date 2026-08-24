from typing import Any, Dict

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class SipTrunk(OrgScopedModel):
    __tablename__ = "sip_trunks"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_sip_trunks_org_name"),
        UniqueConstraint("channel_id", name="uq_sip_trunks_channel_id"),
        Index("ix_sip_trunks_auth_username", "auth_username"),
    )

    name = Column(String(120), nullable=False)
    carrier = Column(String(50), nullable=False, default="telnyx")
    channel_id = Column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    gateways = Column(JSONB, nullable=False, default=list)
    inbound_enabled = Column(Boolean, nullable=False, default=True)
    outbound_enabled = Column(Boolean, nullable=False, default=True)
    auth_mode = Column(String(20), nullable=False, default="ip_acl")
    auth_username = Column(String(128), nullable=True)
    encrypted_auth = Column(JSONB, nullable=True)
    register_enabled = Column(Boolean, nullable=False, default=False)
    tech_prefix = Column(String(32), nullable=True)
    sip_diversion_header = Column(Boolean, nullable=False, default=False)
    outbound_leading_plus_enabled = Column(Boolean, nullable=False, default=True)
    number_e164_check_enabled = Column(Boolean, nullable=False, default=True)
    transfer_enabled = Column(Boolean, nullable=False, default=True)
    media_encryption = Column(String(20), nullable=False, default="none")
    carrier_config = Column(JSONB, nullable=True)
    status = Column(String(30), nullable=False, default="draft")
    status_detail = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "carrier": self.carrier,
            "channel_id": str(self.channel_id),
            "gateways": self.gateways or [],
            "inbound_enabled": self.inbound_enabled,
            "outbound_enabled": self.outbound_enabled,
            "auth_mode": self.auth_mode,
            "auth_username": self.auth_username,
            "register_enabled": self.register_enabled,
            "tech_prefix": self.tech_prefix,
            "sip_diversion_header": self.sip_diversion_header,
            "outbound_leading_plus_enabled": self.outbound_leading_plus_enabled,
            "number_e164_check_enabled": self.number_e164_check_enabled,
            "transfer_enabled": self.transfer_enabled,
            "media_encryption": self.media_encryption,
            "status": self.status,
            "status_detail": self.status_detail,
            "carrier_config": self.carrier_config or {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
