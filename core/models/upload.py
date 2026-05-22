import uuid

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID

from core.models.base import OrgScopedModel


class Upload(OrgScopedModel):
    __tablename__ = "uploads"

    container_name = Column(String(120), nullable=False)
    file_path = Column(String(1000), nullable=True)
    file_type = Column(String(50), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    purpose = Column(String(50), nullable=False)  # kb_document | recording | ...
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
