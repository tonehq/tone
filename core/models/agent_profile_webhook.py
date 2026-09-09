from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class AgentProfileWebhook(OrgScopedModel):
    """One HTTP webhook data source per agent for profile-variable enrichment.

    At call start the runner calls ``endpoint_url`` (GET/POST) with the caller's
    phone, parses the JSON response, and fills the agent's webhook-sourced
    profile variables (``AgentProfileVariable.source == "webhook"``) from each
    variable's ``source_path``. The generic replacement for the removed CRM
    lookup — same runtime seam, arbitrary user endpoint instead of an MCP tool.

    One row per agent (``UniqueConstraint(agent_id)``). ``headers`` is stored
    AES-encrypted via ``encrypt_json`` (``{"data": "<fernet>"}``); ``to_dict``
    NEVER emits decrypted header values (see the service's ``webhook_response``
    for the owner-editing view that does decrypt).
    """

    __tablename__ = "agent_profile_webhooks"
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_agent_profile_webhooks_agent"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint_url = Column(String(500), nullable=False)
    http_method = Column(String(10), nullable=False, default="POST")
    # Encrypted: encrypt_json(headers) → {"data": "<fernet>"}. Never logged.
    headers = Column(JSONB, nullable=True)
    # [{"identifier": "phone", "param": "<name>", "in": "query"|"body"}, ...]
    request_identifiers = Column(JSONB, nullable=True)
    # {"inbound": true, "outbound": false} — true = runs for that direction.
    directions = Column(JSONB, nullable=True)
    timeout_seconds = Column(Integer, nullable=False, default=3)
    is_enabled = Column(Boolean, nullable=False, default=True)

    def to_dict(self) -> dict:
        """Secret-safe serialization (for logs / audit): header VALUES are
        never included — only whether headers are set. The owner-editing view
        that returns decrypted headers lives in the service."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "endpoint_url": self.endpoint_url,
            "http_method": self.http_method,
            "has_headers": bool(self.headers and self.headers.get("data")),
            "request_identifiers": self.request_identifiers or [],
            "directions": self.directions or {},
            "timeout_seconds": self.timeout_seconds,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
