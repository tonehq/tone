from sqlalchemy import Column, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

from core.models.base import OrgScopedModel


class AuditLog(OrgScopedModel):
    """Append-only audit trail for agent-configuration changes.

    Scoped to agent edits in v1: root agent updates, config field updates,
    version lifecycle, and attach/detach of tools, MCP servers, knowledge
    bases, phone numbers, and web channels. One row per logical sub-change;
    rows sharing the same ``request_id`` belong to a single user action and
    can be grouped in the UI.

    Actor and target references are stored as plain UUIDs (no FKs) so the
    audit trail survives hard deletes of the underlying resources — the
    same pattern already used by ``organization_id`` on ``OrgScopedModel``.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_org_agent_created", "organization_id", "agent_id", "created_at"),
        Index("ix_audit_logs_org_created", "organization_id", "created_at"),
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_action", "action"),
    )

    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(64), nullable=False)

    agent_id = Column(UUID(as_uuid=True), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), nullable=True)

    target_resource_type = Column(String(32), nullable=True)
    target_resource_id = Column(String(64), nullable=True)

    changes = Column(JSONB, nullable=True)

    request_id = Column(String(64), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
