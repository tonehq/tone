from sqlalchemy import (
    BigInteger,
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
    # Per-provider embedder kwargs snapshotted from the source
    # ingestion_config at run creation. Consumed by build_embedder_from_run.
    embedding_config = Column(JSONB, nullable=True)
    vector_store = Column(String(32), nullable=False)
    vector_store_ref = Column(JSONB, nullable=True)

    status = Column(String(32), nullable=False, default="pending")
    is_active = Column(Boolean, nullable=False, default=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    # The Procrastinate job that will (or did) execute this run. The FK to
    # ``procrastinate_jobs.id`` (ON DELETE SET NULL — Procrastinate may prune
    # completed jobs; the run row must survive that pruning) is declared only
    # at the DB level via the Alembic migration, NOT here. ``procrastinate_jobs``
    # is managed by Procrastinate's own schema tool and has no SQLAlchemy
    # model, so declaring ``ForeignKey(...)`` on the column would make the ORM
    # look up an unknown table during flush's table-sort pass and raise
    # ``NoReferencedTableError``. Mirrors the prior ``KnowledgeBase.procrastinate_job_id``
    # setup for the same reason.
    procrastinate_job_id = Column(BigInteger, nullable=True, index=True)
    # Optional source recipe. Nullable so runs created before this column
    # existed and ad-hoc "Custom" runs (no saved config) remain valid. ON
    # DELETE SET NULL keeps the run row (and its snapshotted config columns)
    # alive if the source ingestion_config is later removed.
    ingestion_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Stable per-run id stamped onto every log line during the run so the full
    # log stream for one ingestion can be filtered by a single value (mirrors
    # ``calls.trace_id`` for voice calls). Format: "{short_uuid}-ing-{run_id}",
    # minted + persisted by ``IngestionRunService.ensure_trace_id`` at the top
    # of the ``ingest_upload`` Procrastinate task (so pre-``mark_running`` logs
    # also carry it); format itself lives in
    # ``core.logging.make_ingestion_trace_id``. Nullable because rows created
    # before this column existed have no id; the migration does not backfill
    # (historical runs never emitted a trace_id in their logs anyway).
    trace_id = Column(String(128), nullable=True, index=True)
    # Per-run parser/routing metrics — image / table / page counts, parse
    # timings, pipeline selected, etc. Populated in ``complete_run`` from
    # ``PdfRoutingService.build().metrics()`` (see
    # ``core/services/rag/pdf_router.py``). NULL when the parser did not
    # produce metrics (e.g. non-docling parsers on non-PDF inputs). Same
    # shape is also written to ``uploads.meta_data["routing"]`` and
    # ``knowledge_bases.ingestion_stats`` (latest run); this per-run copy is
    # the audit trail across re-ingests with different parser configs.
    ingestion_stats = Column(JSONB, nullable=True)

    upload = relationship("Upload")
    knowledge_base = relationship(
        "KnowledgeBase",
        back_populates="runs",
        foreign_keys=[knowledge_base_id],
    )
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
            "embedding_config": self.embedding_config,
            "vector_store": self.vector_store,
            "vector_store_ref": self.vector_store_ref,
            "status": self.status,
            "is_active": bool(self.is_active),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "chunk_count": self.chunk_count,
            "procrastinate_job_id": self.procrastinate_job_id,
            "ingestion_config_id": (
                str(self.ingestion_config_id) if self.ingestion_config_id else None
            ),
            "trace_id": self.trace_id,
            "ingestion_stats": self.ingestion_stats,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
