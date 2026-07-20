from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class SchemaField(OrgScopedModel):
    """A single field within a ``ContactSchema`` (replaces ``contact_field_definitions``).

    A field names a **target** (``field_name`` — a reserved contact column or a
    ``contact_metadata`` key) and reads from an optional external ``source_key`` (the
    CSV/API header; ``null`` = identity mapping, used by a directory's default schema).
    ``validators`` holds a constrained JSON-Schema subset (minLength/maxLength/pattern/
    minimum/maximum) applied — with ``type`` and ``is_mandatory`` — on contact
    create/update and per-row on sync.
    """

    __tablename__ = "schema_fields"
    __table_args__ = (
        UniqueConstraint("schema_id", "field_name", name="uq_schema_fields_schema_field_name"),
    )

    schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_schemas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(64), nullable=False)  # the target contact column / metadata key
    label = Column(String(120), nullable=True)  # human label for the form
    is_mandatory = Column(Boolean, nullable=False, default=False)
    # string | number | integer | boolean | enum
    type = Column(String(20), nullable=False, default="string")
    format = Column(String(32), nullable=True)  # optional: email | date | uri ...
    validators = Column(JSONB, nullable=False, default=dict)  # JSON-Schema-subset
    options = Column(JSONB, nullable=True)  # enum choices [{value,label}] for type=enum
    # External header this field reads from when used as a sync mapping. NULL = identity
    # (the target column/metadata key is also the source key).
    source_key = Column(String(120), nullable=True)
    field_metadata = Column(JSONB, nullable=False, default=dict)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "schema_id": str(self.schema_id),
            "field_name": self.field_name,
            "label": self.label,
            "is_mandatory": self.is_mandatory,
            "type": self.type,
            "format": self.format,
            "validators": self.validators or {},
            "options": self.options,
            "source_key": self.source_key,
            "field_metadata": self.field_metadata or {},
            "display_order": self.display_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
