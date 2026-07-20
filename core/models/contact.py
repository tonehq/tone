from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Contact(OrgScopedModel):
    """A dial target that belongs to exactly one ``ContactDirectory``.

    The dialed number lives in the dedicated, indexed ``phone_number`` column (E.164)
    — NOT in ``contact_metadata`` — so scheduling can join/dial it directly. Any extra
    columns from the source land in ``contact_metadata`` (including an optional per-row
    ``scheduled_at`` used to override a batch schedule time).

    Contacts are deduplicated per DIRECTORY on ``external_id`` (synthesized by the
    ingestion layer when a source row has none), so re-importing the same file upserts
    rather than duplicating. ``directory_id`` is RESTRICT so a directory can only be
    removed via the explicit hard-delete path (which deletes its contacts first);
    ``sync_id`` records the sync run that last wrote the contact (SET NULL on sync loss).
    """

    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("directory_id", "external_id", name="uq_contacts_directory_external_id"),
        Index("ix_contacts_org_phone_number", "organization_id", "phone_number"),
    )

    directory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_directories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    # Primary dial target, E.164 (e.g. +14155550123). Nullable so a contact can be
    # imported without a number yet (it just can't be scheduled until one is set).
    phone_number = Column(String(20), nullable=True, index=True)
    contact_metadata = Column(JSONB, nullable=False, default=dict)
    sync_id = Column(
        UUID(as_uuid=True), ForeignKey("contact_syncs.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "directory_id": str(self.directory_id) if self.directory_id else None,
            "external_id": self.external_id,
            "name": self.name,
            "phone_number": self.phone_number,
            "contact_metadata": self.contact_metadata or {},
            "sync_id": str(self.sync_id) if self.sync_id else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
