from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentMcpServer(OrgScopedModel):
    __tablename__ = "agent_mcp_servers"
    __table_args__ = (
        UniqueConstraint("agent_config_id", "mcp_server_id", name="uq_agent_mcp_config_server"),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=False)
    mcp_server_id = Column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    oauth_connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)

    # ``selected_tools`` used to live as a JSONB column here. The v2 schema
    # revamp (alembic ``a0b1c2d3e4f5``) dropped it and we now treat the
    # attribute as a no-op runtime field so existing call sites keep
    # compiling while sending no data to the DB. Reads always return None.
    @property
    def selected_tools(self):  # noqa: D401
        return None

    @selected_tools.setter
    def selected_tools(self, _value):  # noqa: D401
        # Intentionally a no-op — the column does not exist in the DB and we
        # do not want callers to think they've persisted a value.
        return None
