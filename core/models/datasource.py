from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Datasource(OrgScopedModel):
    """A source that feeds contacts into a directory through the sync pipeline.

    CSV-only at launch (auto-provisioned one-per-directory). ``config`` (JSONB) is
    reserved for future ``rest`` datasources (base_url + AES-encrypted creds).
    ``directory_id`` is nullable/SET NULL: auto-provisioned CSV datasources are
    directory-owned, while future org-level REST datasources leave it null and survive
    a directory delete.
    """

    __tablename__ = "datasources"

    directory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_directories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(120), nullable=False)
    # 'csv' now; 'rest'/... later
    type = Column(String(20), nullable=False, default="csv")
    config = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "directory_id": str(self.directory_id) if self.directory_id else None,
            "name": self.name,
            "type": self.type,
            "config": self.config or {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
