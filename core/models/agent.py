import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class Agent(OrgScopedModel):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_agents_org_name"),
    )

    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    agent_type = Column(String(20), nullable=False)  # inbound | outbound | both
    llm_model = Column(String, nullable=True)
    published_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="SET NULL", use_alter=True), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    # Per-agent log level (TRACE/DEBUG/INFO/…). NULL = inherit the organization's
    # level, then the env baseline. Resolved by core/services/log_level_resolver.py
    # and applied to this agent's call subprocess. Most specific override wins.
    log_level = Column(String(20), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
