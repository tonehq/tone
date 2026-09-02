"""Ingestion pipeline run lifecycle. Every RAG ingest — and every ad-hoc
re-ingest (parser swap, model swap, store swap) — flows through this service so
there is exactly one place that stamps the run identity, flips ``is_active``,
records terminal status, and keeps the parent KB's active-run pointer in sync.

Transport-agnostic: methods take a SQLAlchemy session + plain args and return
ORM objects. Raises are typed exceptions from ``core.services.ingestion_errors``
— never ``HTTPException``. The router layer converts them to HTTP responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import cast, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from core.logging import start_ingestion_trace
from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.services.common.list_query import apply_search_sort_pagination
from core.services.ingestion_errors import (
    AgentHasNoPublishedConfigError,
    AgentKnowledgeBaseNotFoundError,
    IngestionConfigInactiveError,
    IngestionRunActiveError,
    IngestionRunInProgressError,
    IngestionRunKbMismatchError,
    IngestionRunNotFoundError,
    IngestionRunNotReadyError,
    UnknownRagComponentError,
)
from core.services.rag.component_registry import ensure_rag_component
from core.services.rag.embedder_factory import EMBEDDERS
from core.services.rag.factory import VECTOR_STORES
from core.services.rag.parser_factory import PARSERS
from core.services.rag.tokeniser_factory import TOKENISERS
from shared.config import settings


def _ensure_saved_config_slug_still_registered(
    kind_display: str, slug: str, registry: dict
) -> None:
    """The saved-config path (``resolve_run_config`` when
    ``ingestion_config_id`` is passed) uses a different message than the
    write-time ``ensure_rag_component`` check — "no longer available"
    signals to the user that the config WAS valid when saved but the
    referenced parser/tokeniser/embedder/store has since been removed. The
    message is kept byte-for-byte identical to the previous inline
    HTTPException wording so any FE code that string-matches keeps working."""
    if slug not in registry:
        exc = UnknownRagComponentError(kind_display, slug, list(registry.keys()))
        # Replace the auto-built message with the exact "no longer available"
        # wording. Router does ``detail=str(exc)`` so this is what the FE sees.
        exc.args = (
            f"Config {kind_display} '{slug}' is no longer available. "
            f"Available: {', '.join(sorted(registry.keys()))}.",
        )
        raise exc


# BC re-export: prior consumers imported ``IngestionRunNotFoundError`` from
# this module. The typed exception now lives in ``ingestion_errors`` so the
# router can catch every ingestion error uniformly, but the alias here keeps
# ``from core.services.ingestion_run_service import IngestionRunNotFoundError``
# working without touching call sites.
__all__ = ["IngestionRunService", "IngestionRunNotFoundError"]


class IngestionRunService:

    @staticmethod
    def resolve_run_config(
        db: Session,
        org_id: Any,
        knowledge_base_id: Any,
        request_config: Optional[dict] = None,
        *,
        ingestion_config_id: Optional[Any] = None,
    ) -> dict:
        """Merge system defaults (from ``shared/config.py``) with either a
        saved ``IngestionConfig`` (snapshot mode, wins over any request map)
        or an optional request-supplied override map. This is the single
        place defaults are applied — nothing else in the pipeline bakes them
        in.

        When ``ingestion_config_id`` is provided, the config's fields are
        snapshotted onto the result and ``request_config`` is IGNORED (per
        product decision: a saved config is a fixed recipe, no per-field
        overrides). The config is fetched org-scoped, so an id belonging to
        another org raises 404 exactly like the CRUD endpoints.
        """
        cfg = {
            "parser": settings.DEFAULT_PARSER,
            "parser_config": None,
            "tokeniser": settings.DEFAULT_TOKENISER,
            "tokeniser_config": None,
            "embedding_provider": settings.DEFAULT_EMBEDDING_PROVIDER,
            "embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
            "embedding_dimensions": settings.DEFAULT_EMBEDDING_DIMENSIONS,
            "embedding_version": None,
            "embedding_config": None,
            "vector_store": settings.DEFAULT_VECTOR_STORE,
            "vector_store_ref": None,
        }
        if ingestion_config_id is not None:
            # Local import — avoid an import cycle between
            # IngestionRunService and IngestionConfigService.
            from core.services.ingestion_config_service import IngestionConfigService

            ic = IngestionConfigService(db, org_id=org_id).get_config(ingestion_config_id)
            # is_active=false configs are user-hidden — refuse at run time so
            # a stale UI / script can't dial a retired recipe.
            if not ic.is_active:
                raise IngestionConfigInactiveError(
                    "Ingestion config is inactive and cannot be used for new runs."
                )
            # Re-validate slugs against the LIVE registries: a config saved
            # months ago may reference a parser/tokeniser/embedder/store
            # that has since been removed. Surface a 400 at the endpoint
            # instead of enqueuing a run that crashes mid-ingest. Message
            # says "no longer available" (not "unknown") to signal to the
            # user that the config was valid when saved — preserved
            # byte-for-byte for FE compatibility.
            _ensure_saved_config_slug_still_registered(
                "parser", ic.parser, PARSERS,
            )
            _ensure_saved_config_slug_still_registered(
                "tokeniser", ic.tokeniser, TOKENISERS,
            )
            _ensure_saved_config_slug_still_registered(
                "embedding provider", ic.embedding_provider, EMBEDDERS,
            )
            _ensure_saved_config_slug_still_registered(
                "vector store", ic.vector_store, VECTOR_STORES,
            )
            cfg.update({
                "parser": ic.parser,
                "parser_config": ic.parser_config,
                "tokeniser": ic.tokeniser,
                "tokeniser_config": ic.tokeniser_config,
                "embedding_provider": ic.embedding_provider,
                "embedding_model": ic.embedding_model,
                "embedding_dimensions": ic.embedding_dimensions,
                "embedding_version": ic.embedding_version,
                "embedding_config": ic.embedding_config,
                "vector_store": ic.vector_store,
                "vector_store_ref": ic.vector_store_ref,
            })
            return cfg
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
        ingestion_config_id: Optional[Any] = None,
    ) -> IngestionPipelineRun:
        """Insert a run row in ``pending`` status BEFORE the Procrastinate job
        is deferred. The row exists so the router can stamp the returned
        ``procrastinate_job_id`` onto it, and the worker can flip it to
        ``running`` at start of processing. Auto-assigns the next per-upload
        ``run_number``. Does NOT flip ``is_active`` on the previous run — that
        happens only in ``complete_run`` so a failed re-ingest leaves the
        previous ready run serving retrieval.

        ``ingestion_config_id`` (optional) is stamped on the row in the SAME
        INSERT so audit joins always know which saved config produced the
        run — no split-write window where a pending row exists without its
        source id.

        Auto-retries the INSERT once on a ``(upload_id, run_number)`` unique
        violation so two concurrent ``POST /runs`` for the same upload don't
        both crash with a 500."""
        last_exc: Optional[Exception] = None
        for attempt in (1, 2):
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
                embedding_config=config.get("embedding_config"),
                vector_store=config["vector_store"],
                vector_store_ref=config.get("vector_store_ref"),
                status="pending",
                is_active=False,
                started_at=None,
                procrastinate_job_id=procrastinate_job_id,
                ingestion_config_id=ingestion_config_id,
            )
            db.add(run)
            try:
                db.commit()
                db.refresh(run)
                break
            except IntegrityError as exc:
                last_exc = exc
                db.rollback()
                if attempt == 2:
                    logger.exception(
                        "[ingestion] begin_pending_run: run_number race persisted "
                        "after retry upload={} tried_run_number={}",
                        upload_id, next_run_number,
                    )
                    raise
                logger.info(
                    "[ingestion] begin_pending_run: run_number race upload={} "
                    "tried={} — retrying once",
                    upload_id, next_run_number,
                )

        logger.info(
            "[ingestion] pending run {} (upload={}, run_number={}, parser={}, "
            "tokeniser={}, provider={}, model={}, dims={}, store={}, config_id={})",
            run.id, upload_id, run.run_number,
            run.parser, run.tokeniser,
            run.embedding_provider, run.embedding_model,
            run.embedding_dimensions, run.vector_store,
            ingestion_config_id,
        )
        return run

    @staticmethod
    def set_procrastinate_job_id(
        db: Session, run_id: Any, job_id: int
    ) -> None:
        """Stamp the Procrastinate job id on a pending run. Called by the
        router immediately after ``defer_async`` returns, since ``defer_async``
        can't be executed before the run row exists (we need ``run.id`` in the
        task payload).

        Explicitly stamps ``updated_at`` because bulk ``.update({...})``
        bypasses the ORM's Python-side ``onupdate`` on ``TimestampModel``,
        which would otherwise leave lists sorted by ``updated_at`` looking
        stale after a run transitions."""
        (
            db.query(IngestionPipelineRun)
            .filter(IngestionPipelineRun.id == run_id)
            .update(
                {
                    "procrastinate_job_id": job_id,
                    "updated_at": datetime.now(timezone.utc),
                },
                synchronize_session=False,
            )
        )
        db.commit()

    @staticmethod
    async def start_ingestion_run(
        db: Session,
        *,
        upload,
        kb: KnowledgeBase,
        org_id: Any,
        request_config: Optional[dict],
        delete_existing: bool,
        ingestion_config_id: Optional[Any] = None,
    ) -> Tuple[IngestionPipelineRun, int]:
        """Create a pending IngestionPipelineRun, defer the Procrastinate job, and
        stamp the returned job id on the run. Shared by every KB write path
        (upload / replace / reprocess / custom /runs) so the "create-run → enqueue
        → stamp" trio lives in exactly one place.

        When ``ingestion_config_id`` is set, the run row's recipe columns are
        snapshotted from that saved config (``request_config`` is ignored, per
        product decision) and the id is stamped on the run for audit.

        On defer failure the pending run is marked ``failed`` (not orphaned) and
        the exception is re-raised for the caller to translate to an HTTP error.
        """
        # Local import — ``ingestion_queue`` imports this service (locally), so
        # keep the enqueue import inside the method to avoid an import cycle.
        from core.services.ingestion_queue import enqueue_reprocess, enqueue_upload

        cfg = IngestionRunService.resolve_run_config(
            db, org_id, kb.id, request_config, ingestion_config_id=ingestion_config_id
        )
        run = IngestionRunService.begin_pending_run(
            db,
            upload_id=upload.id,
            knowledge_base_id=kb.id,
            org_id=org_id,
            config=cfg,
            ingestion_config_id=ingestion_config_id,
        )
        enqueue = enqueue_reprocess if delete_existing else enqueue_upload
        try:
            job_id = await enqueue(upload.id, org_id, run.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "[ingestion] enqueue failed for upload {} run {}", upload.id, run.id
            )
            IngestionRunService.fail_run(db, run.id, error=f"enqueue failed: {exc}")
            raise
        IngestionRunService.set_procrastinate_job_id(db, run.id, job_id)
        logger.info(
            "[ingestion] enqueued upload={} run={} job_id={} reprocess={} config_id={}",
            upload.id, run.id, job_id, delete_existing, ingestion_config_id,
        )
        return run, job_id

    @staticmethod
    async def create_pipeline_run(
        db: Session,
        *,
        org_id: Any,
        upload,
        raw_body: dict,
    ) -> dict:
        """Kick off a NEW custom ingestion run for an existing upload (parser /
        tokeniser / embedder / vector store overrides, or a saved
        ``ingestion_config_id``) and return the response payload the
        ``POST /{upload_id}/runs`` route echoes back.

        Business logic relocated verbatim from the router: validate the upload
        has a stored blob, parse the optional ``ingestion_config_id``, whitelist
        the per-field overrides, fail fast on mis-typed slugs, resolve the KB,
        start the run, then build the EFFECTIVE recipe snapshot for the client.

        Raises ``HTTPException`` (400) for a missing blob / malformed
        ``ingestion_config_id`` and the typed ingestion errors
        (``UnknownRagComponentError`` / ``IngestionConfigNotFoundError`` /
        ``IngestionConfigInactiveError`` / ``IngestionValidationError``) for bad
        slugs / configs — the router maps the latter to HTTP status codes.
        """
        from fastapi import HTTPException, status

        if not upload.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload has no stored file to reprocess",
            )

        raw_body = raw_body or {}

        # Parse the optional ingestion_config_id up front (backend enforces
        # even if the frontend omits validation).
        ingestion_config_id: Optional[UUID] = None
        raw_config_id = raw_body.get("ingestion_config_id")
        if raw_config_id:
            try:
                ingestion_config_id = UUID(str(raw_config_id))
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid ingestion_config_id",
                )

        allowed = {
            "parser", "parser_config",
            "tokeniser", "tokeniser_config",
            "embedding_provider", "embedding_model",
            "embedding_dimensions", "embedding_version", "embedding_config",
            "vector_store", "vector_store_ref",
        }
        run_config = {k: v for k, v in raw_body.items() if k in allowed}

        # When a saved config is picked, ignore any per-field overrides in
        # the body — the recipe is fixed by the config (product decision).
        # Skip the slug validation too: those fields were validated when the
        # config was created, and the snapshot happens in resolve_run_config.
        if ingestion_config_id is None:
            # Fail fast on obvious mis-typed slugs (unknown parser / tokeniser
            # / provider / store) so the queued job doesn't error mid-ingest.
            # ``ensure_rag_component`` raises ``UnknownRagComponentError`` —
            # the router-level ``_raise_http_for_ingestion_error`` maps it to
            # a 400 with the same "Available: [...]" hint as before.
            for kind in (
                "parser", "tokeniser", "embedding_provider", "vector_store",
            ):
                if kind in run_config:
                    ensure_rag_component(kind, run_config[kind])
        else:
            # Discard any per-field entries silently when a config was chosen
            # so the response reflects what was actually applied.
            run_config = {}

        # Local import — ``upload_service`` imports this service at module level,
        # so keep the KB resolver import inside the method to avoid a cycle.
        from core.services.upload_service import UploadService

        kb = UploadService.kb_for_upload(db, org_id, upload.id)
        run, job_id = await IngestionRunService.start_ingestion_run(
            db,
            upload=upload,
            kb=kb,
            org_id=org_id,
            request_config=run_config or None,
            delete_existing=False,
            ingestion_config_id=ingestion_config_id,
        )
        logger.info(
            "[ingestion] enqueued custom run for upload {} (run={}, job={}, "
            "config_id={}, overrides={})",
            upload.id, run.id, job_id, ingestion_config_id, sorted(run_config.keys()),
        )
        # Echo the EFFECTIVE recipe snapshotted onto the run row (not the
        # request's raw run_config, which is intentionally empty when a saved
        # config was picked). This way the client can verify what was actually
        # applied without a follow-up GET.
        effective_config = {
            "parser": run.parser,
            "parser_config": run.parser_config,
            "tokeniser": run.tokeniser,
            "tokeniser_config": run.tokeniser_config,
            "embedding_provider": run.embedding_provider,
            "embedding_model": run.embedding_model,
            "embedding_dimensions": run.embedding_dimensions,
            "embedding_version": run.embedding_version,
            "embedding_config": run.embedding_config,
            "vector_store": run.vector_store,
            "vector_store_ref": run.vector_store_ref,
        }
        return {
            "upload_id": str(upload.id),
            "ingestion_run_id": str(run.id),
            "job_id": job_id,
            "ingestion_config_id": (
                str(ingestion_config_id) if ingestion_config_id else None
            ),
            "run_config": effective_config,
            "status": "queued",
        }

    @staticmethod
    def ensure_trace_id(db: Session, run_id: Any) -> Optional[str]:
        """Resolve the run's trace_id — read existing off the row (retry case)
        or mint + persist a new one — and stamp it onto the loguru contextvar
        so every subsequent log line in this task's context carries it.

        Called at the very top of the Procrastinate worker task
        (``ingest_upload``) so 100% of ingestion logs — including the
        pre-``mark_running`` steps (upload load, R2 download) and the
        failure-path logs — are filterable by ONE value. This is the single
        point-of-truth that stamps an ingestion trace_id; format lives in
        ``core.logging.make_ingestion_trace_id``.

        Idempotent: on retries the row already carries a trace_id, so
        ``start_ingestion_trace(existing=)`` reuses it and no UPDATE is issued.
        Returns None if the run row is missing (the worker's own upload-load
        error handling will surface that); the contextvar is left untouched so
        no misleading id is stamped onto unrelated logs.
        """
        row = (
            db.query(IngestionPipelineRun.trace_id)
            .filter(IngestionPipelineRun.id == run_id)
            .first()
        )
        if row is None:
            return None
        existing = row[0]
        if existing:
            return start_ingestion_trace(run_id, existing=existing)
        tid = start_ingestion_trace(run_id, existing=None)
        (
            db.query(IngestionPipelineRun)
            .filter(IngestionPipelineRun.id == run_id)
            .update(
                {"trace_id": tid, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
        )
        db.commit()
        return tid

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
        db: Session,
        run_id: Any,
        *,
        chunk_count: int,
        ingestion_stats: Optional[dict] = None,
    ) -> IngestionPipelineRun:
        """Mark a run ready + flip any previously-active run for the same upload
        to inactive so retrieval switches over atomically. The partial unique
        index ``uq_ingestion_pipeline_runs_upload_active`` enforces the
        one-active-per-upload invariant. Also updates the parent KB's
        ``active_ingestion_pipeline_run_id`` pointer to this run.

        ``ingestion_stats`` is the parser/routing metrics dict produced by
        ``PdfRoutingService.build().metrics()`` (image / table / page counts,
        parse timings, pipeline selected). Left NULL on the row when the
        caller has no metrics (non-docling parsers on non-PDF inputs), so
        existing behavior is preserved for every caller that omits it.
        """
        run = db.query(IngestionPipelineRun).filter(IngestionPipelineRun.id == run_id).first()
        if run is None:
            raise ValueError(f"IngestionPipelineRun {run_id} not found")

        # Deactivate the previous active run BEFORE flipping this one, otherwise
        # both rows are momentarily active and the partial-unique index rejects.
        deactivated = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == run.upload_id,
                IngestionPipelineRun.is_active.is_(True),
                IngestionPipelineRun.id != run.id,
            )
            .update(
                {"is_active": False, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
        )
        db.flush()
        if deactivated:
            logger.info(
                "[ingestion] deactivated {} prior active run(s) upload={} new_run={}",
                deactivated, run.upload_id, run.id,
            )

        run.status = "ready"
        run.is_active = True
        run.completed_at = datetime.now(timezone.utc)
        run.chunk_count = chunk_count
        run.error = None
        # Only stamp when the caller actually has metrics — otherwise leave
        # the column at its persisted value (usually NULL for a first-ready
        # run). Prevents wiping a prior run's metrics on activate/repoint
        # paths that reuse this method, and mirrors "if data is there, add
        # it; else keep the key empty".
        if ingestion_stats is not None:
            run.ingestion_stats = ingestion_stats

        # Repoint the parent KB at this run.
        try:
            (
                db.query(KnowledgeBase)
                .filter(KnowledgeBase.id == run.knowledge_base_id)
                .update(
                    {"active_ingestion_pipeline_run_id": run.id},
                    synchronize_session=False,
                )
            )
            db.commit()
        except Exception:
            logger.exception(
                "[ingestion] complete_run commit failed kb={} run={} chunks={}",
                run.knowledge_base_id, run.id, chunk_count,
            )
            raise
        db.refresh(run)
        logger.info(
            "[ingestion] complete run {} kb={} (chunks={})",
            run.id, run.knowledge_base_id, chunk_count,
        )

        # Auto-run the RAG eval against this recipe. Enqueue-only — the queue
        # worker does the real work; a queue outage or an eval failure must
        # never fail the ingestion (log + swallow).
        #
        # Per-org toggle: an admin can turn this OFF for their org from the
        # Settings → Evaluations page (persisted in ``organizations.eval_settings``).
        # Env ``EVAL_AUTO_RUN_ENABLED`` stays as the fallback when the org key
        # is unset so existing installs continue to auto-run.
        from core.services.org_settings import load_eval_settings_for_org

        if run.organization_id is None:
            # Should be impossible — ingestion_pipeline_runs.organization_id
            # is NOT NULL in the schema (see model + migration). Log loudly if
            # we ever see it so an operator investigates instead of silently
            # inheriting env-only defaults on a mystery row.
            logger.warning(
                "[eval] run {} has NULL organization_id — falling back to "
                "env-only eval settings for the auto-run check",
                run.id,
            )
        eval_cfg = load_eval_settings_for_org(db, run.organization_id)
        if eval_cfg.auto_run_enabled:
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
        logger.warning(
            "[ingestion] marking run failed run={} error={}", run_id, error,
        )
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
    def list_runs(
        db: Session, upload_id: Any, org_id: Any
    ) -> List[IngestionPipelineRun]:
        # ``org_id`` is REQUIRED and ALWAYS applied so the query is tenant-scoped
        # (defense-in-depth against IDOR). The only caller — the KB router's
        # runs-list endpoint — already passes it.
        return (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == upload_id,
                IngestionPipelineRun.organization_id == org_id,
            )
            .order_by(IngestionPipelineRun.run_number.asc())
            .all()
        )

    @staticmethod
    def get_active_run(
        db: Session, upload_id: Any, org_id: Optional[Any] = None
    ) -> Optional[IngestionPipelineRun]:
        # ``org_id`` intentionally stays OPTIONAL: there is no router-reachable
        # path to this method — the only callers are the trusted-scope
        # ``rag-testing`` CLI scripts (run_eval.py / run_all.py) which invoke it
        # WITHOUT an org_id. Making it required would break those scripts.
        # When an org_id IS supplied the tenant filter is applied.
        q = db.query(IngestionPipelineRun).filter(
            IngestionPipelineRun.upload_id == upload_id,
            IngestionPipelineRun.is_active.is_(True),
        )
        if org_id is not None:
            q = q.filter(IngestionPipelineRun.organization_id == org_id)
        return q.first()

    @staticmethod
    def activate_run(
        db: Session, run_id: Any, org_id: Any
    ) -> IngestionPipelineRun:
        # ``org_id`` is REQUIRED and ALWAYS applied so the run is resolved
        # tenant-scoped (no cross-tenant activate). The only caller — the KB
        # router's activate endpoint — already passes it.
        run = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.id == run_id,
                IngestionPipelineRun.organization_id == org_id,
            )
            .first()
        )
        if run is None:
            raise ValueError(f"IngestionPipelineRun {run_id} not found")
        (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == run.upload_id,
                IngestionPipelineRun.is_active.is_(True),
                IngestionPipelineRun.id != run.id,
            )
            .update(
                {"is_active": False, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
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
    def delete_run(db: Session, run_id: Any, org_id: Any) -> None:
        """Cascades to chunks + embeddings via FK ON DELETE CASCADE.

        ``org_id`` is REQUIRED and ALWAYS applied so a run is only ever deleted
        within the caller's tenant (no cross-tenant delete). The only caller —
        the KB router's delete endpoint — already passes it.
        """
        run = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.id == run_id,
                IngestionPipelineRun.organization_id == org_id,
            )
            .first()
        )
        if run is None:
            return
        db.delete(run)
        db.commit()

    @staticmethod
    def get_deletable_run(
        db: Session, *, upload_id: Any, run_id: Any, org_id: Any
    ) -> IngestionPipelineRun:
        """Resolve one ingestion run for deletion, org+upload scoped, and refuse
        to delete the ACTIVE run.

        Raises :class:`IngestionRunNotFoundError` (→ 404) when the run doesn't
        exist for this (org, upload, id), and :class:`IngestionRunActiveError`
        (→ 409) when it's the live run driving retrieval — the caller must
        activate another run first. Read-only: does NOT delete; the caller then
        removes the run's eval results + the run itself.
        """
        run = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.id == run_id,
                IngestionPipelineRun.upload_id == upload_id,
                IngestionPipelineRun.organization_id == org_id,
            )
            .first()
        )
        if run is None:
            raise IngestionRunNotFoundError(
                f"Ingestion run {run_id} not found for this upload"
            )
        if run.is_active:
            raise IngestionRunActiveError(
                "This ingestion run is active and serving live retrieval. "
                "Activate another run first, then delete this one."
            )
        # Only terminal runs are deletable — a pending/running run's worker may
        # still be writing chunks, so deleting now would race the ingestion.
        if run.status not in ("ready", "failed"):
            raise IngestionRunInProgressError(
                f"This ingestion run is still {run.status!r}. Wait for it to "
                "finish (or fail) before deleting."
            )
        return run

    @staticmethod
    def reap_stuck_runs(db: Session, older_than_seconds: int = 3600) -> int:
        """Safety net for ingestion runs stranded in ``running`` because their
        worker was killed mid-ingestion (pod reclaim, OOM, deploy that outran
        the job). Without this the run sits ``running`` and the document shows
        "Processing" forever with no way to recover but a manual retry.

        Marks every ``running`` run whose ``started_at`` is older than the
        cutoff as ``failed`` (with a user-safe message), and flips its parent
        ``Upload`` to ``failed`` so the UI shows Failed + Retry. Idempotent —
        only touches rows past the cutoff; a still-alive slow run finishes
        normally as long as ``older_than_seconds`` is set above the longest
        real ingestion. ``is_active`` is left untouched so the previously-active
        run keeps serving retrieval.
        """
        from datetime import timedelta

        from core.models.upload import Upload

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
        stuck = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.status == "running",
                IngestionPipelineRun.started_at.isnot(None),
                IngestionPipelineRun.started_at < cutoff,
            )
            .all()
        )
        if not stuck:
            return 0

        message = (
            "Ingestion was interrupted (worker restart or timeout) and did not "
            "finish. Please retry."
        )
        now = datetime.now(timezone.utc)
        for run in stuck:
            run.status = "failed"
            run.error = message
            run.completed_at = now
            upload = (
                db.query(Upload)
                .filter(
                    Upload.id == run.upload_id,
                    Upload.organization_id == run.organization_id,
                )
                .first()
            )
            if upload is not None and upload.status == "processing":
                upload.status = "failed"
                upload.meta_data = {**(upload.meta_data or {}), "error": message}
        db.commit()
        logger.warning(
            "[reaper] marked {} stuck ingestion run(s) failed (older than {}s)",
            len(stuck), older_than_seconds,
        )
        return len(stuck)

    @staticmethod
    def delete_runs_for_upload(db: Session, *, upload_id: Any, org_id: Any) -> int:
        """Delete EVERY ingestion pipeline run for one upload (org-scoped),
        cascading to that run's chunks + embeddings via FK ``ON DELETE
        CASCADE``. The KB-level and per-agent ``active_ingestion_pipeline_run_id``
        pins that referenced a deleted run are reset to NULL by their own FK
        ``ON DELETE SET NULL``, so no dangling pointer remains.

        Returns the number of runs removed. Used by the file-replace flow to
        wipe the stale content of the previous file before re-ingesting; the
        ``Upload`` and ``KnowledgeBase`` rows themselves are left intact (the
        document identity is preserved — only its ingested content is cleared).
        """
        n = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.upload_id == upload_id,
                IngestionPipelineRun.organization_id == org_id,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "[ingestion] purged {} pipeline run(s) (+chunks/embeddings) for upload={} org={}",
            n, upload_id, org_id,
        )
        return n

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
    def list_chunks_paginated(
        db: Session,
        *,
        org_id: Any,
        upload_id: Any,
        run_id: Any,
        search: Optional[str] = None,
        page_no: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[KnowledgeBaseChunk], int]:
        """Paginated list of chunks produced by one ingestion run, ordered by
        ``chunk_index`` ascending so the drawer reads in the same order the
        chunker emitted them.

        Validates the run belongs to the caller's org + the supplied upload
        (the router already resolved the upload, but re-checking on the run
        avoids leaking chunks from another org's run that happens to share an
        id). Raises ``ValueError`` when the run does not exist for the
        (org, upload) pair — the router converts that into a 404.

        Search matches ``chunk_text`` case-insensitively.
        """
        run_exists = (
            db.query(IngestionPipelineRun.id)
            .filter(
                IngestionPipelineRun.id == run_id,
                IngestionPipelineRun.organization_id == org_id,
                IngestionPipelineRun.upload_id == upload_id,
            )
            .first()
        )
        if run_exists is None:
            raise IngestionRunNotFoundError(
                f"IngestionPipelineRun {run_id} not found for upload {upload_id}"
            )

        base = (
            db.query(KnowledgeBaseChunk)
            .filter(
                KnowledgeBaseChunk.organization_id == org_id,
                KnowledgeBaseChunk.upload_id == upload_id,
                KnowledgeBaseChunk.ingestion_run_id == run_id,
            )
        )
        return apply_search_sort_pagination(
            base,
            search=search,
            search_fields=[KnowledgeBaseChunk.chunk_text],
            sort_by="chunk_index",
            sort_order="asc",
            sort_map={"chunk_index": KnowledgeBaseChunk.chunk_index},
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

        Raises typed exceptions from ``core.services.ingestion_errors`` on
        every business-rule failure (missing published config, unattached
        KB, cross-KB pin, unready run). The router maps them to 400/404 so
        a CLI script gets the same guardrails.
        """
        published_config_id = (
            db.query(Agent.published_config_id)
            .filter(Agent.id == agent_id, Agent.organization_id == org_id)
            .scalar()
        )
        if published_config_id is None:
            raise AgentHasNoPublishedConfigError(
                "Agent has no published configuration."
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
            raise AgentKnowledgeBaseNotFoundError(
                "Knowledge base is not attached to this agent."
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
                raise IngestionRunNotFoundError("Ingestion run not found.")
            if run.knowledge_base_id != akb.knowledge_base_id:
                raise IngestionRunKbMismatchError(
                    "Ingestion run does not belong to this knowledge base."
                )
            if run.status != "ready":
                # Preserve the exact original wording so any FE code that
                # string-matches on the detail keeps working. The
                # ``IngestionRunNotReadyError`` default message is generic
                # ("only 'ready' is allowed"); the pin path historically
                # said "only 'ready' runs are pinnable" — so we override
                # the args to that verbatim.
                exc = IngestionRunNotReadyError(run.status, action="pin")
                exc.args = (
                    f"Cannot pin a run with status={run.status!r}; "
                    "only 'ready' runs are pinnable.",
                )
                raise exc

        akb.active_ingestion_pipeline_run_id = run_id
        db.commit()
        db.refresh(akb)
        logger.info(
            "[ingestion] agent {} kb {} pinned run {}",
            agent_id, knowledge_base_id, run_id,
        )
        return akb
