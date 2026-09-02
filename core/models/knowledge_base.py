from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

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
    # Denormalized pointer to the currently-serving ingestion run. Kept in sync
    # by IngestionRunService.complete_run/activate_run so KB → active run is a
    # single FK lookup instead of an in-Python scan over kb.runs.
    active_ingestion_pipeline_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    doc_type = Column(String(32), nullable=True)
    ingestion_stats = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    runs = relationship(
        "IngestionPipelineRun",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        foreign_keys="IngestionPipelineRun.knowledge_base_id",
    )
    # post_update because knowledge_bases ↔ ingestion_pipeline_runs have a mutual
    # FK cycle (KB → active run and run → KB). Without post_update SQLAlchemy
    # can't order the two INSERTs; with it, the second FK is written as a
    # separate UPDATE after both rows exist.
    active_run_ref = relationship(
        "IngestionPipelineRun",
        foreign_keys=[active_ingestion_pipeline_run_id],
        post_update=True,
    )

    def active_run(self):
        if self.active_run_ref is not None:
            return self.active_run_ref
        # Fallback: pre-migration rows won't have the FK set yet; keep serving
        # from the in-Python scan until complete_run/activate_run stamps the FK.
        for run in self.runs or []:
            if run.is_active:
                return run
        return None

    def to_dict(self) -> dict:
        active = self.active_run()
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "doc_type": self.doc_type,
            "ingestion_stats": self.ingestion_stats or {},
            "meta_data": self.meta_data or {},
            "active_ingestion_pipeline_run_id": (
                str(self.active_ingestion_pipeline_run_id)
                if self.active_ingestion_pipeline_run_id
                else None
            ),
            "active_run": {
                "id": str(active.id),
                "parser": active.parser,
                "tokeniser": active.tokeniser,
                "embedding_provider": active.embedding_provider,
                "embedding_model": active.embedding_model,
                "embedding_dimensions": active.embedding_dimensions,
                "vector_store": active.vector_store,
                "procrastinate_job_id": active.procrastinate_job_id,
            } if active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
