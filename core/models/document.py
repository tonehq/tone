from sqlalchemy import BigInteger, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class Document(OrgScopedModel):
    """Knowledge-base document. One Document = one Upload (one file).
    Multi-file uploads create one Document per file. No version history."""

    __tablename__ = "documents"

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name = Column(String(512), nullable=False)
    content_type = Column(String(128), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="ready")  # ready | processing | failed
    meta_data = Column(JSONB, nullable=False, default=dict)

    upload = relationship("Upload")
    agent = relationship("Agent")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "upload_id": str(self.upload_id),
            "file_name": self.file_name,
            "content_type": self.content_type,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status,
            "meta_data": self.meta_data or {},
            "created_at": int(self.created_at.timestamp()) if self.created_at else None,
            "updated_at": int(self.updated_at.timestamp()) if self.updated_at else None,
        }
