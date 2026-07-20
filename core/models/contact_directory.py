from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class ContactDirectory(OrgScopedModel):
    """A user-created contact directory — the container that owns its contacts and a
    CSV datasource, and references one reusable org-level schema as its default shape.

    An org has MANY directories. Each directory auto-provisions a CSV datasource on
    create and points ``default_schema_id`` at a ``ContactSchema`` (the manual-Add form
    + validation shape). ``default_schema_id`` is SET NULL so deleting a shared schema
    never cascades into directories.
    """

    __tablename__ = "contact_directories"
    __table_args__ = (
        Index("ix_contact_directories_org_name", "organization_id", "name"),
    )

    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    default_schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_schemas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "default_schema_id": str(self.default_schema_id) if self.default_schema_id else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
