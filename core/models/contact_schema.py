from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class ContactSchema(OrgScopedModel):
    """An ORG-LEVEL, reusable contact-shape template (parent of ``SchemaField``).

    Replaces the old flat ``contact_field_definitions``: a schema groups a set of
    ``schema_fields`` and can be referenced by MANY directories (as a directory's
    ``default_schema_id`` — its manual-Add form + validation shape) and by MANY syncs
    (as the external→target mapping). It carries NO ``directory_id`` / ``datasource_id``
    / ``is_default`` — those bindings live on the referencing directory/sync.
    """

    __tablename__ = "contact_schemas"
    __table_args__ = (
        Index("ix_contact_schemas_org_name", "organization_id", "name"),
    )

    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
