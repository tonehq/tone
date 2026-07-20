from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class AgentContact(OrgScopedModel):
    """Join between an agent and a contact assigned to it (no scheduling gate).

    Populated by assigning contacts/directories to an agent (or by a sync's auto-assign
    ``agent_id``). Both FKs CASCADE so the row is auto-removed when either side is
    deleted; unique ``(agent_id, contact_id)`` keeps assignment idempotent.
    """

    __tablename__ = "agent_contacts"
    __table_args__ = (
        UniqueConstraint("agent_id", "contact_id", name="uq_agent_contacts_agent_contact"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "contact_id": str(self.contact_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
