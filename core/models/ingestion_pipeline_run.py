from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class IngestionPipelineRun(OrgScopedModel):
    """One ingestion of an upload with a specific pipeline (parser, tokeniser,
    embedder, vector store). The same upload can have many runs (A/B, re-embed,
    swap store) — chunks + embeddings are FK'd to a run so an upload can serve
    retrieval from whichever run is currently active."""

    __tablename__ = "ingestion_pipeline_runs"
    __table_args__ = (
        UniqueConstraint(
            "upload_id", "run_number", name="uq_ingestion_pipeline_runs_upload_run_number"
        ),
        Index(
            "uq_ingestion_pipeline_runs_upload_active",
            "upload_id",
            unique=True,
            postgresql_where="is_active",
        ),
    )

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_number = Column(Integer, nullable=False)

    parser = Column(String(50), nullable=False)
    parser_config = Column(JSONB, nullable=True)
    tokeniser = Column(String(50), nullable=False)
    tokeniser_config = Column(JSONB, nullable=True)
    embedding_provider = Column(String(50), nullable=False)
    embedding_model = Column(String(120), nullable=False)
    embedding_dimensions = Column(Integer, nullable=False)
    embedding_version = Column(String(50), nullable=True)
    vector_store = Column(String(32), nullable=False)
    vector_store_ref = Column(JSONB, nullable=True)

    status = Column(String(32), nullable=False, default="pending")
    is_active = Column(Boolean, nullable=False, default=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=True)

    upload = relationship("Upload")
    knowledge_base = relationship("KnowledgeBase", back_populates="runs")
    chunks = relationship(
        "KnowledgeBaseChunk",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "upload_id": str(self.upload_id),
            "knowledge_base_id": str(self.knowledge_base_id),
            "run_number": self.run_number,
            "parser": self.parser,
            "parser_config": self.parser_config,
            "tokeniser": self.tokeniser,
            "tokeniser_config": self.tokeniser_config,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "embedding_version": self.embedding_version,
            "vector_store": self.vector_store,
            "vector_store_ref": self.vector_store_ref,
            "status": self.status,
            "is_active": bool(self.is_active),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
