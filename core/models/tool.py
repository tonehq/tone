import uuid

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Tool(OrgScopedModel):
    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_tools_org_name"),
    )

    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    tool_type = Column(String(80), nullable=False)
    action_params_schema = Column(JSONB, nullable=True)
    trigger_phrases = Column(JSONB, nullable=True)
    entity = Column(JSONB, nullable=True)
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)
