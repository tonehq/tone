from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.models.base import OrgScopedModel


class KnowledgeBase(OrgScopedModel):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_knowledge_base_org_name"),
    )

    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(String(32), nullable=False, default="ready")
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True, index=True)
    meta_data = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "meta_data": self.meta_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
