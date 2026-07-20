from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class ContactSync(OrgScopedModel):
    """One run of the datasource-driven import pipeline into a directory.

    Records the mapping schema, optional CSV upload, optional auto-assign ``agent_id``,
    lifecycle ``status`` (pending|processing|completed|failed), per-run ``counts``
    ({created,updated,skipped,failed}) and per-row ``row_errors`` for a downloadable
    partial-failure report. ``directory_id``/``datasource_id`` are SET NULL so a sync
    survives as detached audit when its directory is hard-deleted.
    """

    __tablename__ = "contact_syncs"

    directory_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_directories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    datasource_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    schema_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contact_schemas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # pending | processing | completed | failed
    status = Column(String(20), nullable=False, default="pending", index=True)
    counts = Column(JSONB, nullable=False, default=dict)  # {created,updated,skipped,failed}
    row_errors = Column(JSONB, nullable=False, default=list)  # [{row,field,message}]
    error = Column(String(500), nullable=True)  # hard-failure message
    # Optional external integration references (e.g. a future REST/app datasource sync).
    app_id = Column(String(255), nullable=True)
    connection_id = Column(String(255), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "directory_id": str(self.directory_id) if self.directory_id else None,
            "datasource_id": str(self.datasource_id) if self.datasource_id else None,
            "schema_id": str(self.schema_id) if self.schema_id else None,
            "upload_id": str(self.upload_id) if self.upload_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "app_id": self.app_id,
            "connection_id": self.connection_id,
            "status": self.status,
            "counts": self.counts or {},
            "row_errors": self.row_errors or [],
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
