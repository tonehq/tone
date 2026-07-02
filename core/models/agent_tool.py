import uuid

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentTool(OrgScopedModel):
    __tablename__ = "agent_tools"
    __table_args__ = (
        UniqueConstraint("agent_config_id", "tool_id", name="uq_agent_tools_config_tool"),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=True)
    # Per-version OAuth override. When set, runtime resolution uses this in
    # preference to ``tools.oauth_connection_id`` (the default from the Tools
    # page). See ``core/utils/oauth_resolution.py``.
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)
