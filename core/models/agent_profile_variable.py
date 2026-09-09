from sqlalchemy import Column, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentProfileVariable(OrgScopedModel):
    """One reusable ``{{profile.<key>}}`` placeholder for an agent.

    Referenced from prompts / workflow nodes as ``{{profile.<key>}}``. Resolved
    at call time by ``build_call_context`` in
    ``core/services/pipeline/prompt_variables.py`` (same code path as system
    variables — never a parallel resolver).

    Hard-delete: variables are user-authored config, not audit-critical.
    Deleting one leaves any ``{{profile.<key>}}`` reference in a prompt to
    render verbatim (existing "unknown key → literal" fallback in
    ``substitute_variables``), so a stale reference never crashes a call.
    """

    __tablename__ = "agent_profile_variables"
    __table_args__ = (
        UniqueConstraint(
            "agent_id", "key", name="uq_agent_profile_variables_agent_key"
        ),
        Index("ix_agent_profile_variables_agent", "agent_id"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    key = Column(String(64), nullable=False)
    value = Column(Text, nullable=False, default="")
    description = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "key": self.key,
            "value": self.value or "",
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
