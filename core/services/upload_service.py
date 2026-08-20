"""UploadService — the single entry point for creating an ``Upload`` + backing
``KnowledgeBase`` from a local file path OR a request stream, so the customer
KB upload route AND the benchmark-dataset CLI both flow through one implementation.

Extracted from ``knowledge_base_routes.upload_document`` per the reuse rule in
CLAUDE.md: R2 upload + Upload insert + KB insert + optional agent link +
optional ingestion-run defer live here exactly once. Callers pick between two
sources (``file_path=`` for CLI / ``fileobj=`` for HTTP) and choose whether the
ingestion job should be deferred inline (``enqueue_ingestion=True``, default)
or deferred later by the caller (``enqueue_ingestion=False``, used by the
benchmark CLI so it can pre-seed a gold ``Eval`` row before the auto-run task
observes the upload)."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Optional, Tuple, Union
from uuid import UUID, uuid4

from loguru import logger

from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.audit_actions import AgentAuditAction, AuditResourceType
from core.services.base import BaseService
from core.services.ingestion_queue import enqueue_upload
from core.services.ingestion_run_service import IngestionRunService
from core.services.r2_storage_service import KB_DOCUMENT, R2StorageService, build_r2_object_key
from shared.config import settings


class UploadService(BaseService):
    """Create-side lifecycle for KB uploads. Read/list/delete stay in the route
    (thin transports) until a second caller needs them."""

    def __init__(
        self,
        db,
        user_id: Optional[Union[str, UUID]] = None,
        org_id: Optional[Union[str, UUID]] = None,
        r2_service: Optional[R2StorageService] = None,
    ):
        super().__init__(db, user_id=user_id, org_id=org_id)
        self._r2 = r2_service

    async def create_upload_from_file(
        self,
        *,
        file_path: Optional[Union[str, Path]] = None,
        fileobj: Any = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        kb_name: Optional[str] = None,
        kb_meta_data: Optional[dict] = None,
        upload_meta_data: Optional[dict] = None,
        agent_id: Optional[UUID] = None,
        agent_config_id: Optional[UUID] = None,
        enqueue_ingestion: bool = True,
        request_config: Optional[dict] = None,
        ingestion_config_id: Optional[UUID] = None,
    ) -> Tuple[Upload, KnowledgeBase, Optional[IngestionPipelineRun]]:
        """Upload bytes to R2, insert ``Upload`` + ``KnowledgeBase`` (+ optional
        AgentKnowledgeBase link and audit log) in one transaction, and — unless
        ``enqueue_ingestion=False`` — begin a pending ``IngestionPipelineRun``
        and defer the Procrastinate job.

        Exactly one of ``file_path`` or ``fileobj`` must be provided. When
        ``fileobj`` is used, ``size_bytes`` may be passed pre-computed to avoid
        seeking the stream a second time (the HTTP route already sizes it).

        Returns ``(Upload, KnowledgeBase, IngestionPipelineRun | None)``. The
        run is ``None`` only when ``enqueue_ingestion=False`` was passed AND
        no pending run was requested — otherwise a pending run row exists so
        the caller can defer the job themselves.

        On R2 upload success followed by a DB write failure, the R2 blob is
        best-effort deleted so we don't leak orphan objects. The DB is rolled
        back and the original exception is re-raised."""
        if (file_path is None) == (fileobj is None):
            raise ValueError(
                "create_upload_from_file requires exactly one of file_path or fileobj"
            )
        if self.org_id is None:
            raise ValueError("UploadService requires org_id (via constructor or context)")

        resolved_name, resolved_type, stream, resolved_size = self._resolve_source(
            file_path=file_path,
            fileobj=fileobj,
            file_name=file_name,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        if not resolved_size:
            raise ValueError("Empty file — refusing to create an upload for a zero-byte source")

        r2 = self._r2 or R2StorageService()
        object_key = build_r2_object_key(
            org_id=self.org_id,
            kind=KB_DOCUMENT,
            subpath=f"{uuid4()}/{resolved_name}",
        )
        logger.info(
            "[upload] uploading to R2 org={} key={} content_type={} size={}",
            self.org_id, object_key, resolved_type, resolved_size,
        )
        t_r2 = time.monotonic()
        try:
            r2.upload_fileobj(stream, object_key, content_type=resolved_type)
        except Exception:
            logger.exception(
                "[upload] R2 upload failed org={} key={}",
                self.org_id, object_key,
            )
            raise
        logger.info(
            "[upload] R2 upload ok key={} elapsed_s={:.1f}",
            object_key, time.monotonic() - t_r2,
        )

        try:
            upload = Upload(
                organization_id=self.org_id,
                container_name=settings.R2_BUCKET_NAME,
                file_path=object_key,
                file_name=resolved_name,
                file_type=resolved_type,
                size_bytes=resolved_size,
                purpose="kb_document",
                status="processing",
                meta_data=dict(upload_meta_data or {}),
                created_by_user_id=_as_uuid(self.user_id),
                is_active=True,
            )
            self.db.add(upload)
            self.db.flush()

            kb = KnowledgeBase(
                organization_id=self.org_id,
                name=(kb_name or resolved_name),
                status="processing",
                upload_id=upload.id,
                meta_data=dict(kb_meta_data or {}),
            )
            self.db.add(kb)
            self.db.flush()

            if agent_id is not None and agent_config_id is not None:
                self.db.add(
                    AgentKnowledgeBase(
                        organization_id=self.org_id,
                        agent_id=agent_id,
                        knowledge_base_id=kb.id,
                        agent_config_id=agent_config_id,
                    )
                )
                self.audit.log(
                    AgentAuditAction.KB_ATTACHED,
                    agent_id=agent_id,
                    agent_config_id=agent_config_id,
                    target_resource_type=AuditResourceType.KNOWLEDGE_BASE,
                    target_resource_id=str(upload.id),
                )

            self.db.commit()
            self.db.refresh(upload)
            self.db.refresh(kb)
        except Exception:
            logger.exception(
                "[upload] DB write failed after R2 upload; rolling back and cleaning up R2 blob {}",
                object_key,
            )
            self.db.rollback()
            try:
                r2.delete_file(object_key)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Best-effort R2 cleanup failed for {}: {}", object_key, exc)
            raise

        logger.info(
            "[upload] created upload={} kb={} org={} agent={} name={}",
            upload.id, kb.id, self.org_id, agent_id, resolved_name,
        )

        run = self._begin_ingestion_run(
            upload=upload,
            kb=kb,
            request_config=request_config,
            ingestion_config_id=ingestion_config_id,
        )
        if enqueue_ingestion and run is not None:
            try:
                job_id = await enqueue_upload(upload.id, self.org_id, run.id)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "[upload] ingestion enqueue failed for upload {} run {}",
                    upload.id, run.id,
                )
                IngestionRunService.fail_run(self.db, run.id, error=f"enqueue failed: {exc}")
                raise
            IngestionRunService.set_procrastinate_job_id(self.db, run.id, job_id)
            logger.info(
                "[upload] ingestion enqueued upload={} run={} job_id={}",
                upload.id, run.id, job_id,
            )

        return upload, kb, run

    def _begin_ingestion_run(
        self,
        *,
        upload: Upload,
        kb: KnowledgeBase,
        request_config: Optional[dict],
        ingestion_config_id: Optional[UUID] = None,
    ) -> IngestionPipelineRun:
        """Always create the pending run — the benchmark CLI still wants the row
        so it can pass ``run.id`` into its own ``enqueue_upload`` call after
        pre-seeding the gold eval."""
        cfg = IngestionRunService.resolve_run_config(
            self.db,
            self.org_id,
            kb.id,
            request_config,
            ingestion_config_id=ingestion_config_id,
        )
        return IngestionRunService.begin_pending_run(
            self.db,
            upload_id=upload.id,
            knowledge_base_id=kb.id,
            org_id=self.org_id,
            config=cfg,
            ingestion_config_id=ingestion_config_id,
        )

    def _resolve_source(
        self,
        *,
        file_path: Optional[Union[str, Path]],
        fileobj: Any,
        file_name: Optional[str],
        content_type: Optional[str],
        size_bytes: Optional[int],
    ) -> Tuple[str, str, Any, int]:
        """Normalize both source shapes into ``(name, content_type, stream, size)``."""
        if fileobj is not None:
            name = file_name or "upload.bin"
            ctype = content_type or _guess_content_type(name)
            if size_bytes is None:
                fileobj.seek(0, 2)
                size = fileobj.tell()
                fileobj.seek(0)
            else:
                size = int(size_bytes)
            return name, ctype, fileobj, size

        path = Path(file_path)  # type: ignore[arg-type]
        if not path.is_file():
            raise FileNotFoundError(f"Source file does not exist: {path}")
        name = file_name or path.name
        ctype = content_type or _guess_content_type(name)
        size = int(size_bytes) if size_bytes is not None else path.stat().st_size
        # Callers of the CLI path own the file — open in binary mode for R2 streaming.
        stream = path.open("rb")
        return name, ctype, stream, size


def _guess_content_type(name: str) -> str:
    ctype, _ = mimetypes.guess_type(name)
    if ctype:
        return ctype
    ext = Path(name).suffix.lower()
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".html": "text/html",
    }.get(ext, "application/octet-stream")


def _as_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
