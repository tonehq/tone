from sqlalchemy import Column, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel, SoftDeleteMixin


class IngestionConfig(SoftDeleteMixin, OrgScopedModel):
    """A named, reusable ingestion pipeline recipe (parser / tokeniser /
    embedder / vector store) that users save once and pick when starting a
    ``POST /knowledge-base/{upload_id}/runs``. Selecting one snapshots every
    field onto the resulting ``IngestionPipelineRun`` row — the run continues
    to be the source of truth for the pipeline, so a config can be renamed,
    edited, or (soft-)deleted without affecting historical runs.

    Every recipe column mirrors ``ingestion_pipeline_runs`` 1:1 so the
    snapshot is a direct field copy.
    """

    __tablename__ = "ingestion_configs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_ingestion_configs_org_name"
        ),
        Index(
            "ix_ingestion_configs_org_active",
            "organization_id",
            "is_active",
        ),
    )

    name = Column(String(120), nullable=False)
    description = Column(String(500), nullable=True)

    parser = Column(String(50), nullable=False)
    parser_config = Column(JSONB, nullable=True)
    tokeniser = Column(String(50), nullable=False)
    tokeniser_config = Column(JSONB, nullable=True)
    embedding_provider = Column(String(50), nullable=False)
    embedding_model = Column(String(120), nullable=False)
    embedding_dimensions = Column(Integer, nullable=False)
    embedding_version = Column(String(50), nullable=True)
    # Per-provider embedder kwargs (batch_size / max_retries /
    # tokens_per_minute / …). Snapshotted onto ingestion_pipeline_runs on
    # run creation and passed through build_embedder_from_run.
    embedding_config = Column(JSONB, nullable=True)
    vector_store = Column(String(32), nullable=False)
    vector_store_ref = Column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
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
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
