import uuid

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel, SoftDeleteMixin


class Agent(SoftDeleteMixin, OrgScopedModel):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_agents_org_name"),
    )

    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    agent_type = Column(String(20), nullable=False)  # inbound | outbound | both
    published_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="SET NULL", use_alter=True), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # Per-agent log level (TRACE/DEBUG/INFO/…). NULL = inherit the organization's
    # level, then the env baseline. Resolved by core/services/log_level_resolver.py
    # and applied to this agent's call subprocess. Most specific override wins.
    log_level = Column(String(20), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "published_config_id": str(self.published_config_id) if self.published_config_id else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "is_active": self.is_active,
            "log_level": self.log_level,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
