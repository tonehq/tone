from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from pgvector.sqlalchemy import HALFVEC, Vector

from core.models.base import OrgScopedModel


class KnowledgeBaseChunkEmbedding(OrgScopedModel):
    """Embedding vectors for a chunk, one row per (chunk, run). Split from
    ``knowledge_base_chunks`` so the same chunk text can carry embeddings from
    multiple ingestion runs (different models / dimensions) without duplicating
    the text — and so external vector stores (Pinecone, Qdrant, …) can skip
    this table entirely (chunk row still exists, vector lives remote).

    pgvector needs a fixed dimension per column + per HNSW index, so common
    embedding sizes each get their own column. Adding a new dimension is a
    one-column follow-up migration; the code picks the column from
    ``embedding_dimensions``.
    """

    __tablename__ = "knowledge_base_chunk_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id", "ingestion_run_id",
            name="uq_kb_chunk_embeddings_chunk_run",
        ),
        CheckConstraint(
            "("
            "(embedding_1024 IS NOT NULL)::int + "
            "(embedding_1536 IS NOT NULL)::int + "
            "(embedding_3072 IS NOT NULL)::int"
            ") = 1",
            name="ck_kb_chunk_embeddings_exactly_one_vector",
        ),
        Index(
            "ix_kb_chunk_embeddings_1024_hnsw",
            "embedding_1024",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding_1024": "vector_cosine_ops"},
        ),
        Index(
            "ix_kb_chunk_embeddings_1536_hnsw",
            "embedding_1536",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding_1536": "vector_cosine_ops"},
        ),
        # pgvector's HNSW index tops out at 2000 dimensions on the plain `vector`
        # type. For 3072-D (OpenAI text-embedding-3-large etc.) we store the vector
        # as `halfvec` (fp16, ~½ the storage, negligible recall loss) which HNSW
        # supports up to 4000 dimensions via `halfvec_cosine_ops`.
        Index(
            "ix_kb_chunk_embeddings_3072_hnsw",
            "embedding_3072",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding_3072": "halfvec_cosine_ops"},
        ),
    )

    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_base_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingestion_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_dimensions = Column(Integer, nullable=False)
    embedding_1024 = Column(Vector(1024), nullable=True)
    embedding_1536 = Column(Vector(1536), nullable=True)
    embedding_3072 = Column(HALFVEC(3072), nullable=True)

    chunk = relationship("KnowledgeBaseChunk", back_populates="embeddings")

    def to_dict(self) -> dict:
        # Deliberately omits the raw vector arrays (embedding_1024/1536/3072) —
        # they are huge and not JSON-useful. Callers get ids + dimension + which
        # vector column is populated instead.
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "chunk_id": str(self.chunk_id) if self.chunk_id else None,
            "ingestion_run_id": str(self.ingestion_run_id) if self.ingestion_run_id else None,
            "embedding_dimensions": self.embedding_dimensions,
            "has_embedding_1024": self.embedding_1024 is not None,
            "has_embedding_1536": self.embedding_1536 is not None,
            "has_embedding_3072": self.embedding_3072 is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def column_for_dimension(dimensions: int):
        """Map a run's ``embedding_dimensions`` → the SQLAlchemy Column on this
        table that stores that vector shape. Used by ``PgVectorStore`` to pick
        the write column at ingest and the similarity column at query."""
        if dimensions == 1024:
            return KnowledgeBaseChunkEmbedding.embedding_1024
        if dimensions == 1536:
            return KnowledgeBaseChunkEmbedding.embedding_1536
        if dimensions == 3072:
            return KnowledgeBaseChunkEmbedding.embedding_3072
        from core.services.rag.errors import EmbeddingDimensionUnsupportedError

        raise EmbeddingDimensionUnsupportedError(
            f"No pgvector column for {dimensions}-D embeddings. "
            "Add a knowledge_base_chunk_embeddings.embedding_<dim> column + HNSW index."
        )
