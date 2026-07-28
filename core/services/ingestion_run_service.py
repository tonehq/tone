"""Ingestion pipeline run lifecycle. Every RAG ingest — and every ad-hoc
re-ingest (parser swap, model swap, store swap) — flows through this service so
there is exactly one place that stamps the run identity, flips ``is_active``,
records terminal status, and keeps the parent KB's active-run pointer in sync.

Transport-agnostic: methods take a SQLAlchemy session + plain args and return
ORM objects. Raises are typed subclasses of ``RagError`` — no HTTPException.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple
from uuid import UUID

from fastapi import HTTPException, status as http_status
from loguru import logger
from sqlalchemy import cast, func
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.services.common.list_query import apply_search_sort_pagination
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
    def begin_pending_run(
        db: Session,
        *,
        upload_id: Any,
        knowledge_base_id: Any,
        org_id: Any,
        config: dict,
        procrastinate_job_id: Optional[int] = None,
    ) -> IngestionPipelineRun:
        """Insert a run row in ``pending`` status BEFORE the Procrastinate job
        is deferred. The row exists so the router can stamp the returned
        ``procrastinate_job_id`` onto it, and the worker can flip it to
        ``running`` at start of processing. Auto-assigns the next per-upload
        ``run_number``. Does NOT flip ``is_active`` on the previous run — that
        happens only in ``complete_run`` so a failed re-ingest leaves the
        previous ready run serving retrieval."""
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
            status="pending",
            is_active=False,
            started_at=None,
            procrastinate_job_id=procrastinate_job_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        logger.info(
            "[ingestion] pending run {} (upload={}, run_number={}, parser={}, "
            "tokeniser={}, provider={}, model={}, dims={}, store={})",
            run.id, upload_id, run.run_number,
            run.parser, run.tokeniser,
            run.embedding_provider, run.embedding_model,
            run.embedding_dimensions, run.vector_store,
        )
        return run

    @staticmethod
    def set_procrastinate_job_id(
        db: Session, run_id: Any, job_id: int
    ) -> None:
        """Stamp the Procrastinate job id on a pending run. Called by the
        router immediately after ``defer_async`` returns, since ``defer_async``
        can't be executed before the run row exists (we need ``run.id`` in the
        task payload)."""
        (
            db.query(IngestionPipelineRun)
            .filter(IngestionPipelineRun.id == run_id)
            .update(
                {"procrastinate_job_id": job_id},
                synchronize_session=False,
            )
        )
        db.commit()

    @staticmethod
    def mark_running(db: Session, run_id: Any) -> IngestionPipelineRun:
        """Flip a pending run to ``running`` and stamp ``started_at``. Called
        by the worker at the start of ``process_document``. The run row was
        created earlier by the router in ``begin_pending_run``."""
        run = db.query(IngestionPipelineRun).filter(IngestionPipelineRun.id == run_id).first()
        if run is None:
            raise ValueError(f"IngestionPipelineRun {run_id} not found")
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.info(
            "[ingestion] running run {} (upload={}, run_number={})",
            run.id, run.upload_id, run.run_number,
        )
        return run

    @staticmethod
    def complete_run(
        db: Session, run_id: Any, *, chunk_count: int
    ) -> IngestionPipelineRun:
        """Mark a run ready + flip any previously-active run for the same upload
        to inactive so retrieval switches over atomically. The partial unique
        index ``uq_ingestion_pipeline_runs_upload_active`` enforces the
        one-active-per-upload invariant. Also updates the parent KB's
        ``active_ingestion_pipeline_run_id`` pointer to this run."""
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

        # Repoint the parent KB at this run.
        (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == run.knowledge_base_id)
            .update(
                {"active_ingestion_pipeline_run_id": run.id},
                synchronize_session=False,
            )
        )

        db.commit()
        db.refresh(run)
        logger.info(
            "[ingestion] complete run {} (chunks={})", run.id, chunk_count
        )

        # Auto-run the RAG eval against this recipe. Enqueue-only — the queue
        # worker does the real work; a queue outage or an eval failure must
        # never fail the ingestion (log + swallow).
        if settings.EVAL_AUTO_RUN_ENABLED:
            try:
                from core.services.ingestion_queue import (
                    enqueue_eval_for_ingestion_run_sync,
                )

                enqueue_eval_for_ingestion_run_sync(run.id)
                logger.info("[eval] enqueued auto-run for ingestion_run={}", run.id)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "[eval] failed to enqueue auto-run for ingestion_run={} "
                    "(swallowed — ingestion unaffected)",
                    run.id,
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
        (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == run.knowledge_base_id)
            .update(
                {"active_ingestion_pipeline_run_id": run.id},
                synchronize_session=False,
            )
        )
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

    # ── list + resolver + agent-KB override ────────────────────────────────

    _LIST_SORT_MAP = {
        "run_number": IngestionPipelineRun.run_number,
        "created_at": IngestionPipelineRun.created_at,
        "completed_at": IngestionPipelineRun.completed_at,
        "status": IngestionPipelineRun.status,
        "chunk_count": IngestionPipelineRun.chunk_count,
    }

    @staticmethod
    def list_runs_paginated(
        db: Session,
        *,
        org_id: Any,
        upload_id: Any,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        page_no: int = 1,
        page_size: int = 20,
        status_filter: Optional[Sequence[str]] = None,
        is_active_only: bool = False,
    ) -> Tuple[List[IngestionPipelineRun], int]:
        """Paginated + searchable list of pipeline runs for one upload. Uses
        the canonical ``apply_search_sort_pagination`` helper so the router
        stays a 5-line transport. Search covers parser / tokeniser / provider
        / model / procrastinate_job_id / error."""
        base = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.organization_id == org_id,
                IngestionPipelineRun.upload_id == upload_id,
            )
        )
        if status_filter:
            base = base.filter(IngestionPipelineRun.status.in_(list(status_filter)))
        if is_active_only:
            base = base.filter(IngestionPipelineRun.is_active.is_(True))

        return apply_search_sort_pagination(
            base,
            search=search,
            search_fields=[
                IngestionPipelineRun.parser,
                IngestionPipelineRun.tokeniser,
                IngestionPipelineRun.embedding_provider,
                IngestionPipelineRun.embedding_model,
                # ``procrastinate_job_id`` is BIGINT; cast so ilike works.
                cast(IngestionPipelineRun.procrastinate_job_id, String),
                IngestionPipelineRun.error,
            ],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map=IngestionRunService._LIST_SORT_MAP,
            page_no=page_no,
            page_size=page_size,
        )

    @staticmethod
    def resolve_active_run_id(
        db: Session,
        *,
        org_id: Any,
        upload_id: Any,
        agent_id: Optional[Any] = None,
    ) -> Optional[UUID]:
        """The ONE place that answers "which run should retrieval query?" for a
        given (upload, optionally agent) pair. Resolution order:

        1. If ``agent_id`` is given, look up the agent's published
           ``AgentKnowledgeBase`` row for this KB. If its
           ``active_ingestion_pipeline_run_id`` is set, return that.
        2. Look up the KB attached to ``upload_id`` and return its
           ``active_ingestion_pipeline_run_id`` if set.
        3. Fall back to any org-scoped run with ``is_active=True`` for this
           upload. Returns ``None`` if nothing is ready.

        Every retrieval path (pgvector, evals, tools) MUST route through this
        method so the resolution rule is not duplicated. Callers that already
        have an explicit ``ingestion_run_id`` filter should bypass this.
        """
        # 1) Per-agent pin scoped to the agent's published config.
        if agent_id is not None:
            pinned = (
                db.query(AgentKnowledgeBase.active_ingestion_pipeline_run_id)
                .join(
                    KnowledgeBase,
                    KnowledgeBase.id == AgentKnowledgeBase.knowledge_base_id,
                )
                .join(Agent, Agent.id == AgentKnowledgeBase.agent_id)
                .filter(
                    AgentKnowledgeBase.agent_id == agent_id,
                    AgentKnowledgeBase.organization_id == org_id,
                    AgentKnowledgeBase.agent_config_id == Agent.published_config_id,
                    KnowledgeBase.upload_id == upload_id,
                    AgentKnowledgeBase.active_ingestion_pipeline_run_id.isnot(None),
                )
                .scalar()
            )
            if pinned is not None:
                return pinned

        # 2) KB-level default pointer.
        kb_default = (
            db.query(KnowledgeBase.active_ingestion_pipeline_run_id)
            .filter(
                KnowledgeBase.upload_id == upload_id,
                KnowledgeBase.organization_id == org_id,
                KnowledgeBase.active_ingestion_pipeline_run_id.isnot(None),
            )
            .scalar()
        )
        if kb_default is not None:
            return kb_default

        # 3) Legacy fallback — any run with is_active=True. Pre-migration KBs
        # won't have the pointer set until the next complete_run/activate_run.
        legacy = (
            db.query(IngestionPipelineRun.id)
            .filter(
                IngestionPipelineRun.upload_id == upload_id,
                IngestionPipelineRun.organization_id == org_id,
                IngestionPipelineRun.is_active.is_(True),
            )
            .scalar()
        )
        return legacy

    @staticmethod
    def set_agent_kb_active_run(
        db: Session,
        *,
        org_id: Any,
        agent_id: Any,
        knowledge_base_id: Any,
        run_id: Optional[Any],
    ) -> AgentKnowledgeBase:
        """Set (or clear when ``run_id`` is None) the per-agent run pin for one
        AgentKnowledgeBase row. Validates:

        * the AgentKnowledgeBase row exists on the agent's *published* config
          (per-version scoping — draft rows aren't pinnable),
        * the run belongs to the SAME KB (no cross-KB pinning),
        * the run status is ``ready`` (pending / failed runs are unpinnable).

        Router callers surface 400/404s from the raised HTTPExceptions here so
        a CLI script gets the same guardrails.
        """
        published_config_id = (
            db.query(Agent.published_config_id)
            .filter(Agent.id == agent_id, Agent.organization_id == org_id)
            .scalar()
        )
        if published_config_id is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Agent has no published configuration.",
            )

        akb = (
            db.query(AgentKnowledgeBase)
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.knowledge_base_id == knowledge_base_id,
                AgentKnowledgeBase.agent_config_id == published_config_id,
                AgentKnowledgeBase.organization_id == org_id,
            )
            .first()
        )
        if akb is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Knowledge base is not attached to this agent.",
            )

        if run_id is not None:
            run = (
                db.query(IngestionPipelineRun)
                .filter(
                    IngestionPipelineRun.id == run_id,
                    IngestionPipelineRun.organization_id == org_id,
                )
                .first()
            )
            if run is None:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Ingestion run not found.",
                )
            if run.knowledge_base_id != akb.knowledge_base_id:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Ingestion run does not belong to this knowledge base.",
                )
            if run.status != "ready":
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot pin a run with status={run.status!r}; "
                        "only 'ready' runs are pinnable."
                    ),
                )

        akb.active_ingestion_pipeline_run_id = run_id
        db.commit()
        db.refresh(akb)
        logger.info(
            "[ingestion] agent {} kb {} pinned run {}",
            agent_id, knowledge_base_id, run_id,
        )
        return akb
