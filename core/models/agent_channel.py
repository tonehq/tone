from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentChannel(OrgScopedModel):
    __tablename__ = "agent_channels"
    __table_args__ = (
        UniqueConstraint("agent_id", "channel_id", name="uq_agent_channels_agent_channel"),
        UniqueConstraint("slug", name="uq_agent_channels_slug"),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(64), nullable=False)
