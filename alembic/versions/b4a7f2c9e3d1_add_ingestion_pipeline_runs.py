"""RAG refactor: ingestion_pipeline_runs + knowledge_base_chunk_embeddings

Splits the RAG pipeline identity (parser, tokeniser, embedding provider/model/
dimensions, vector store) into a first-class ``ingestion_pipeline_runs`` row so
one upload can carry multiple runs (A/B, re-embed, swap store). Chunks + vectors
FK to a run; retrieval reads whichever run is currently active.

Migration steps
1. Create ``ingestion_pipeline_runs``.
2. Create ``knowledge_base_chunk_embeddings`` with per-dimension vector columns
   (1024 / 1536 / 3072) — pgvector needs a fixed dimension per column/index.
3. On ``knowledge_base_chunks``:
   - Add ``ingestion_run_id`` FK + ``chunk_metadata`` JSONB.
   - Copy legacy ``embedding`` (1536-D, produced by
     text-embedding-3-small + docling + docling_hybrid + pgvector) into
     ``knowledge_base_chunk_embeddings.embedding_1536`` under a synthetic run #1
     per knowledge base, so retrieval keeps working with no re-index.
   - Drop the legacy ``embedding`` column and its HNSW index.

Downgrade recreates ``knowledge_base_chunks.embedding`` + its HNSW index, copies
the active-run 1536-D vectors back, then drops the new tables.

Revision ID: b4a7f2c9e3d1
Revises: 2178f950024d
Create Date: 2026-07-24 12:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b4a7f2c9e3d1"
down_revision = "2178f950024d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "upload_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("uploads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "knowledge_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("parser", sa.String(50), nullable=False),
        sa.Column("parser_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tokeniser", sa.String(50), nullable=False),
        sa.Column("tokeniser_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_provider", sa.String(50), nullable=False),
        sa.Column("embedding_model", sa.String(120), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_version", sa.String(50), nullable=True),
        sa.Column("vector_store", sa.String(32), nullable=False),
        sa.Column("vector_store_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "upload_id", "run_number", name="uq_ingestion_pipeline_runs_upload_run_number"
        ),
    )
    op.create_index(
        "uq_ingestion_pipeline_runs_upload_active",
        "ingestion_pipeline_runs",
        ["upload_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "knowledge_base_chunk_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_base_chunks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_1024", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("embedding_1536", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("embedding_3072", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.UniqueConstraint(
            "chunk_id", "ingestion_run_id", name="uq_kb_chunk_embeddings_chunk_run"
        ),
        sa.CheckConstraint(
            "("
            "(embedding_1024 IS NOT NULL)::int + "
            "(embedding_1536 IS NOT NULL)::int + "
            "(embedding_3072 IS NOT NULL)::int"
            ") = 1",
            name="ck_kb_chunk_embeddings_exactly_one_vector",
        ),
    )
    # Swap the Float[] placeholder columns (needed because sqlalchemy alembic autogen
    # doesn't understand pgvector natively at all sites) for real pgvector columns.
    # 1024 / 1536 use the plain `vector` type; 3072 uses `halfvec` because pgvector's
    # HNSW index tops out at 2000 dims on `vector` — halfvec (fp16) supports HNSW up
    # to 4000 dims via `halfvec_cosine_ops`, at ~½ storage and negligible recall loss.
    op.execute("ALTER TABLE knowledge_base_chunk_embeddings ALTER COLUMN embedding_1024 TYPE vector(1024) USING NULL")
    op.execute("ALTER TABLE knowledge_base_chunk_embeddings ALTER COLUMN embedding_1536 TYPE vector(1536) USING NULL")
    op.execute("ALTER TABLE knowledge_base_chunk_embeddings ALTER COLUMN embedding_3072 TYPE halfvec(3072) USING NULL")

    op.execute(
        "CREATE INDEX ix_kb_chunk_embeddings_1024_hnsw ON knowledge_base_chunk_embeddings "
        "USING hnsw (embedding_1024 vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_kb_chunk_embeddings_1536_hnsw ON knowledge_base_chunk_embeddings "
        "USING hnsw (embedding_1536 vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_kb_chunk_embeddings_3072_hnsw ON knowledge_base_chunk_embeddings "
        "USING hnsw (embedding_3072 halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    # knowledge_base_chunks: additive columns first (so the backfill below can run).
    op.add_column(
        "knowledge_base_chunks",
        sa.Column(
            "ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.add_column(
        "knowledge_base_chunks",
        sa.Column("chunk_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_kb_chunks_run",
        "knowledge_base_chunks",
        "ingestion_pipeline_runs",
        ["ingestion_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_knowledge_base_chunks_ingestion_run_id",
        "knowledge_base_chunks",
        ["ingestion_run_id"],
    )

    # Data migration: one synthetic run #1 per KB that has chunks, pinned to the
    # historical defaults (docling + docling_hybrid + text-embedding-3-small 1536-D
    # pgvector), then FK every existing chunk to that run, then copy each chunk's
    # legacy 1536-D vector into knowledge_base_chunk_embeddings.embedding_1536.
    op.execute(
        """
        INSERT INTO ingestion_pipeline_runs (
            id, created_at, updated_at, organization_id, upload_id, knowledge_base_id,
            run_number, parser, tokeniser,
            embedding_provider, embedding_model, embedding_dimensions,
            vector_store, status, is_active,
            started_at, completed_at
        )
        SELECT
            gen_random_uuid(), now(), now(), kb.organization_id, kb.upload_id, kb.id,
            1, 'docling', 'docling_hybrid',
            'openai', 'text-embedding-3-small', 1536,
            'pgvector', 'ready', true,
            kb.created_at, kb.updated_at
        FROM knowledge_bases kb
        WHERE kb.upload_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM knowledge_base_chunks c WHERE c.upload_id = kb.upload_id)
        """
    )
    op.execute(
        """
        UPDATE knowledge_base_chunks c
        SET ingestion_run_id = r.id
        FROM ingestion_pipeline_runs r
        WHERE r.upload_id = c.upload_id AND r.run_number = 1
        """
    )
    op.execute(
        """
        INSERT INTO knowledge_base_chunk_embeddings (
            id, created_at, updated_at, organization_id,
            chunk_id, ingestion_run_id, embedding_dimensions, embedding_1536
        )
        SELECT
            gen_random_uuid(), now(), now(), c.organization_id,
            c.id, c.ingestion_run_id, 1536, c.embedding
        FROM knowledge_base_chunks c
        WHERE c.embedding IS NOT NULL AND c.ingestion_run_id IS NOT NULL
        """
    )

    # Rows that had no vector (partially processed) get deleted so ingestion_run_id can be NOT NULL.
    op.execute("DELETE FROM knowledge_base_chunks WHERE ingestion_run_id IS NULL")
    op.alter_column("knowledge_base_chunks", "ingestion_run_id", nullable=False)

    op.create_unique_constraint(
        "uq_kb_chunks_run_index",
        "knowledge_base_chunks",
        ["ingestion_run_id", "chunk_index"],
    )
    op.create_index(
        "ix_kb_chunks_upload_run",
        "knowledge_base_chunks",
        ["upload_id", "ingestion_run_id"],
    )

    # Drop legacy embedding + its HNSW index (vector now lives on the new table).
    op.execute("DROP INDEX IF EXISTS ix_knowledge_base_chunks_embedding_hnsw")
    op.drop_column("knowledge_base_chunks", "embedding")


def downgrade() -> None:
    # Recreate the legacy embedding column + HNSW index, then copy the ACTIVE run's
    # 1536-D vectors back so retrieval keeps working after a rollback.
    op.execute(
        "ALTER TABLE knowledge_base_chunks ADD COLUMN embedding vector(1536)"
    )
    op.execute(
        """
        UPDATE knowledge_base_chunks c
        SET embedding = e.embedding_1536
        FROM knowledge_base_chunk_embeddings e
        JOIN ingestion_pipeline_runs r ON r.id = e.ingestion_run_id
        WHERE e.chunk_id = c.id
          AND r.is_active
          AND e.embedding_1536 IS NOT NULL
        """
    )
    op.execute(
        "CREATE INDEX ix_knowledge_base_chunks_embedding_hnsw "
        "ON knowledge_base_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    op.drop_index("ix_kb_chunks_upload_run", table_name="knowledge_base_chunks")
    op.drop_constraint("uq_kb_chunks_run_index", "knowledge_base_chunks", type_="unique")
    op.drop_index(
        "ix_knowledge_base_chunks_ingestion_run_id", table_name="knowledge_base_chunks"
    )
    op.drop_constraint("fk_kb_chunks_run", "knowledge_base_chunks", type_="foreignkey")
    op.drop_column("knowledge_base_chunks", "chunk_metadata")
    op.drop_column("knowledge_base_chunks", "ingestion_run_id")

    op.execute("DROP INDEX IF EXISTS ix_kb_chunk_embeddings_3072_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_kb_chunk_embeddings_1536_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_kb_chunk_embeddings_1024_hnsw")
    op.drop_table("knowledge_base_chunk_embeddings")

    op.drop_index(
        "uq_ingestion_pipeline_runs_upload_active",
        table_name="ingestion_pipeline_runs",
    )
    op.drop_table("ingestion_pipeline_runs")
