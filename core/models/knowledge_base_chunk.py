from sqlalchemy import Column, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class KnowledgeBaseChunk(OrgScopedModel):
    """A chunk of text extracted from an Upload during a specific ingestion
    pipeline run. Vectors live in ``knowledge_base_chunk_embeddings`` — the
    chunk row itself holds only text + parser-provided metadata so external
    vector stores can skip the embeddings table entirely."""

    __tablename__ = "knowledge_base_chunks"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_run_id", "chunk_index", name="uq_kb_chunks_run_index"
        ),
        Index("ix_kb_chunks_upload_run", "upload_id", "ingestion_run_id"),
    )

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingestion_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)

    upload = relationship("Upload")
    run = relationship("IngestionPipelineRun", back_populates="chunks")
    embeddings = relationship(
        "KnowledgeBaseChunkEmbedding",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "upload_id": str(self.upload_id) if self.upload_id else None,
            "ingestion_run_id": str(self.ingestion_run_id) if self.ingestion_run_id else None,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "chunk_metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
