from sqlalchemy import Column, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentLlmEvalFolder(OrgScopedModel):
    """First-class folder row for grouping ``agent_llm_eval_scenarios``.

    Replaces the derived VARCHAR ``folder`` column on scenarios: a folder now
    exists as its own row so it survives after its last scenario is deleted
    and can be renamed with a single-row UPDATE. Every agent gets a seeded
    ``Default`` folder at creation time so the UI never faces a
    "no folders" empty state.

    ``agent_llm_eval_results.folder`` is still a text snapshot column so
    historical runs preserve the folder name they were scored under even
    after the source folder is renamed or deleted.
    """

    __tablename__ = "agent_llm_eval_folders"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "name",
            name="uq_agent_llm_eval_folders_agent_name",
        ),
        Index("ix_agent_llm_eval_folders_agent", "agent_id"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
