"""Ingestion pipeline run lifecycle. Every RAG ingest — and every ad-hoc
re-ingest (parser swap, model swap, store swap) — flows through this service so
there is exactly one place that stamps the run identity, flips ``is_active``,
and records terminal status.

Transport-agnostic: methods take a SQLAlchemy session + plain args and return
ORM objects. Raises are typed subclasses of ``RagError`` — no HTTPException.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models.ingestion_pipeline_run import IngestionPipelineRun
from shared.config import settings


class IngestionRunService:

    @staticmethod
    def resolve_run_config(
        db: Session,
        org_id: Any,
        knowledge_base_id: Any,
        request_config: Optional[dict] = None,
    ) -> dict:
        """Merge system defaults (from ``shared/config.py``) with an optional
        request-supplied override map. This is the single place defaults are
        applied — nothing else in the pipeline bakes them in."""
        cfg = {
            "parser": settings.DEFAULT_PARSER,
            "parser_config": None,
            "tokeniser": settings.DEFAULT_TOKENISER,
            "tokeniser_config": None,
            "embedding_provider": settings.DEFAULT_EMBEDDING_PROVIDER,
            "embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
            "embedding_dimensions": settings.DEFAULT_EMBEDDING_DIMENSIONS,
            "embedding_version": None,
            "vector_store": settings.DEFAULT_VECTOR_STORE,
            "vector_store_ref": None,
        }
        if request_config:
            for key in list(cfg.keys()):
                if key in request_config and request_config[key] is not None:
                    cfg[key] = request_config[key]
        return cfg

    @staticmethod
    def begin_run(
        db: Session,
        *,
        upload_id: Any,
        knowledge_base_id: Any,
        org_id: Any,
        config: dict,
    ) -> IngestionPipelineRun:
        """Insert a new run row (status=running) for this upload. Auto-assigns
        the next per-upload ``run_number``. Does NOT flip ``is_active`` on the
        previous run — that happens in ``complete_run`` so a failed re-ingest
        leaves the previous ready run serving retrieval."""
        next_run_number = (
            db.query(func.coalesce(func.max(IngestionPipelineRun.run_number), 0) + 1)
            .filter(IngestionPipelineRun.upload_id == upload_id)
            .scalar()
        )
        run = IngestionPipelineRun(
            organization_id=org_id,
            upload_id=upload_id,
            knowledge_base_id=knowledge_base_id,
            run_number=next_run_number,
            parser=config["parser"],
            parser_config=config.get("parser_config"),
            tokeniser=config["tokeniser"],
            tokeniser_config=config.get("tokeniser_config"),
            embedding_provider=config["embedding_provider"],
            embedding_model=config["embedding_model"],
            embedding_dimensions=config["embedding_dimensions"],
            embedding_version=config.get("embedding_version"),
            vector_store=config["vector_store"],
            vector_store_ref=config.get("vector_store_ref"),
            status="running",
            is_active=False,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        logger.info(
            "[ingestion] begin run {} (upload={}, run_number={}, parser={}, "
            "tokeniser={}, provider={}, model={}, dims={}, store={})",
            run.id, upload_id, run.run_number,
            run.parser, run.tokeniser,
            run.embedding_provider, run.embedding_model,
            run.embedding_dimensions, run.vector_store,
        )
        return run

    @staticmethod
    def complete_run(
        db: Session, run_id: Any, *, chunk_count: int
    ) -> IngestionPipelineRun:
        """Mark a run ready + flip any previously-active run for the same upload
        to inactive so retrieval switches over atomically. The partial unique
        index ``uq_ingestion_pipeline_runs_upload_active`` enforces the
        one-active-per-upload invariant."""
        run = db.query(IngestionPipelineRun).filter(IngestionPipelineRun.id == run_id).first()
        if run is None:
            raise ValueError(f"IngestionPipelineRun {run_id} not found")

        # Deactivate the previous active run BEFORE flipping this one, otherwise
        # both rows are momentarily active and the partial-unique index rejects.
        (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == run.upload_id,
                IngestionPipelineRun.is_active.is_(True),
                IngestionPipelineRun.id != run.id,
            )
            .update({"is_active": False}, synchronize_session=False)
        )
        db.flush()

        run.status = "ready"
        run.is_active = True
        run.completed_at = datetime.now(timezone.utc)
        run.chunk_count = chunk_count
        run.error = None
        db.commit()
        db.refresh(run)
        logger.info(
            "[ingestion] complete run {} (chunks={})", run.id, chunk_count
        )
        return run

    @staticmethod
    def fail_run(db: Session, run_id: Any, *, error: str) -> IngestionPipelineRun:
        run = db.query(IngestionPipelineRun).filter(IngestionPipelineRun.id == run_id).first()
        if run is None:
            raise ValueError(f"IngestionPipelineRun {run_id} not found")
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error = error
        db.commit()
        db.refresh(run)
        logger.info("[ingestion] fail run {} ({})", run.id, error)
        return run

    @staticmethod
    def list_runs(db: Session, upload_id: Any) -> List[IngestionPipelineRun]:
        return (
            db.query(IngestionPipelineRun)
            .filter(IngestionPipelineRun.upload_id == upload_id)
            .order_by(IngestionPipelineRun.run_number.asc())
            .all()
        )

    @staticmethod
    def get_active_run(db: Session, upload_id: Any) -> Optional[IngestionPipelineRun]:
        return (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == upload_id,
                IngestionPipelineRun.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def activate_run(db: Session, run_id: Any) -> IngestionPipelineRun:
        run = db.query(IngestionPipelineRun).filter(IngestionPipelineRun.id == run_id).first()
        if run is None:
            raise ValueError(f"IngestionPipelineRun {run_id} not found")
        (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == run.upload_id,
                IngestionPipelineRun.is_active.is_(True),
                IngestionPipelineRun.id != run.id,
            )
            .update({"is_active": False}, synchronize_session=False)
        )
        db.flush()
        run.is_active = True
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def delete_run(db: Session, run_id: Any) -> None:
        """Cascades to chunks + embeddings via FK ON DELETE CASCADE."""
        run = db.query(IngestionPipelineRun).filter(IngestionPipelineRun.id == run_id).first()
        if run is None:
            return
        db.delete(run)
        db.commit()
