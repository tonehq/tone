import uuid

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class Upload(OrgScopedModel):
    __tablename__ = "uploads"

    container_name = Column(String(120), nullable=False)
    file_path = Column(String(1000), nullable=True)
    file_name = Column(String(512), nullable=True)
    file_type = Column(String(50), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    purpose = Column(String(50), nullable=False)  # kb_document | recording | ...
    status = Column(String(32), nullable=False, default="ready")  # ready | processing | failed
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "file_name": self.file_name,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "purpose": self.purpose,
            "status": self.status,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
