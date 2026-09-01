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
import re
import time
from pathlib import Path
from typing import Any, Optional, Tuple, Union
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.audit_actions import AgentAuditAction, AuditResourceType
from core.services.base import BaseService
from core.services.ingestion_errors import IngestionValidationError
from core.services.ingestion_queue import enqueue_upload
from core.services.ingestion_run_service import IngestionRunService
from core.services.r2_storage_service import KB_DOCUMENT, R2StorageService, build_r2_object_key
from core.utils.faceted_query import apply_filters, apply_sort
from shared.config import settings

# Fallback ceiling when ``settings.MAX_KB_FILE_SIZE_BYTES`` is unset (0). 100 MB
# mirrors the frontend ``MAX_FILE_SIZE`` in DocumentUpload.tsx so a valid upload
# in the UI is never rejected by the backend for a different reason.
DEFAULT_MAX_KB_FILE_SIZE_BYTES = 100 * 1024 * 1024

# Allowed KB document extensions — mirrors the frontend ``ACCEPTED_EXTENSIONS``
# allowlist so the backend enforces the same contract for direct API / CLI
# callers that bypass the UI. Validated by extension (not the browser-supplied
# content-type, which is unreliable for csv/json), matching the frontend check.
ALLOWED_KB_EXTENSIONS = frozenset({"pdf", "txt", "csv", "html", "json", "docx"})

# Longest KB document name we accept. Bound by ``KnowledgeBase.name``
# (``String(255)``), the tighter of the two columns a name lands in (the other
# being ``Upload.file_name``, ``String(512)``). Enforcing it up front turns a
# would-be DB ``DataError`` (opaque HTTP 500) into a clean validation error.
MAX_KB_FILE_NAME_LENGTH = 255


def _sanitize_kb_file_name(name: str) -> str:
    """Reduce a client-supplied filename to a safe basename before it is used
    as an R2 object-key segment or stored as the KB name.

    Strips any directory components (so ``../`` or path separators can't leak
    into the object key) and drops non-printable / control characters. Normal
    filenames pass through unchanged; falls back to ``upload.bin`` when nothing
    usable remains.
    """
    base = re.split(r"[\\/]+", name.strip())[-1].strip()
    base = "".join(ch for ch in base if ch.isprintable())
    return base or "upload.bin"


class UploadService(BaseService):
    """Create-side lifecycle for KB uploads. Read/list/delete stay in the route
    (thin transports) until a second caller needs them."""

    @staticmethod
    def validate_upload_file(
        *,
        file_name: str,
        size_bytes: int,
        max_name_length: int = MAX_KB_FILE_NAME_LENGTH,
    ) -> None:
        """Enforce the KB upload contract (name length + size ceiling + type
        allowlist) on the backend, independent of any frontend validation.
        Raises the transport-agnostic :class:`IngestionValidationError`
        (routers map it to HTTP 400) so HTTP upload, file-replace, and the CLI
        share ONE rule.

        ``max_name_length`` defaults to the create-path limit (bound by
        ``KnowledgeBase.name``); the replace path passes the wider
        ``Upload.file_name`` limit. Zero-byte files are handled by the caller's
        own empty-file check; this method owns the name/size/type gates only.
        """
        if len(file_name) > max_name_length:
            raise IngestionValidationError(
                f"File name is too long ({len(file_name)} characters). "
                f"Maximum allowed is {max_name_length}."
            )
        limit = settings.MAX_KB_FILE_SIZE_BYTES or DEFAULT_MAX_KB_FILE_SIZE_BYTES
        if size_bytes > limit:
            raise IngestionValidationError(
                f"File is too large ({size_bytes / 1024 / 1024:.1f} MB). "
                f"Maximum allowed is {limit // (1024 * 1024)} MB."
            )
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in ALLOWED_KB_EXTENSIONS:
            raise IngestionValidationError(
                f"Unsupported file type '.{ext}'. Supported types: "
                f"{', '.join(sorted(ALLOWED_KB_EXTENSIONS))}."
            )

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

        # Reduce to a safe basename before it becomes an R2 key segment / the
        # stored KB name (defeats path separators; normal names unchanged).
        resolved_name = _sanitize_kb_file_name(resolved_name)

        # Backend enforcement of the name + size + type contract — runs BEFORE
        # the R2 write so a rejected file never leaves an orphan blob. Applies
        # to the HTTP upload route AND any CLI caller that flows through this
        # service. Uses the default (create-path) name-length limit.
        self.validate_upload_file(file_name=resolved_name, size_bytes=resolved_size)

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

    # ── Read / list / mutate for existing KB uploads ─────────────────────
    # Extracted from ``knowledge_base_routes`` so the org-scoped list query,
    # rename, file-replace, and delete logic lives here exactly once and can
    # be reused by any transport (HTTP route, CLI, worker). Routers stay thin:
    # parse/validate/authorize the request, then call one of these.

    @staticmethod
    def kb_column_map() -> dict:
        """Scalar columns exposed for filtering / sorting / faceting on documents."""
        return {
            "file_name": Upload.file_name,
            "status": Upload.status,
            "size_bytes": Upload.size_bytes,
            "created_at": Upload.created_at,
            "updated_at": Upload.updated_at,
        }

    @staticmethod
    def kb_base_query(db: Session, org_id: UUID):
        """Org-scoped base query for kb documents (excludes soft-deleted rows)."""
        return db.query(Upload).filter(
            Upload.organization_id == org_id,
            Upload.purpose == "kb_document",
            Upload.deleted_at.is_(None),
        )

    def _get_org_upload(self, upload_id: UUID) -> Upload:
        """Fetch an org-scoped ``Upload`` or raise ``ValueError`` (routers map
        it to a 404). No purpose/soft-delete filter — matches the inline
        lookups the KB router previously used for rename/replace/delete."""
        if self.org_id is None:
            raise ValueError("UploadService requires org_id (via constructor or context)")
        upload = (
            self.db.query(Upload)
            .filter(Upload.id == upload_id, Upload.organization_id == self.org_id)
            .first()
        )
        if upload is None:
            raise ValueError("Upload not found")
        return upload

    def list_kb_documents(
        self,
        *,
        search: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        filters: Any = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[list, int, dict]:
        """Org-scoped, searchable/filterable/sortable/paginated list of KB
        documents. Returns ``(items, total, agents_by_upload)`` where
        ``agents_by_upload`` maps each upload id to its distinct linked agent
        ids (single batched query — no N+1). The caller shapes the HTTP
        response envelope + signed URLs; this method owns the query semantics.
        """
        if self.org_id is None:
            raise ValueError("UploadService requires org_id (via constructor or context)")

        column_map = self.kb_column_map()
        query = self.kb_base_query(self.db, self.org_id)

        # Named params (back-compat): free-text search, owning-agent and status.
        if search:
            query = query.filter(Upload.file_name.ilike(f"%{search}%"))
        if agent_id:
            upload_ids_q = (
                self.db.query(KnowledgeBase.upload_id)
                .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
                .filter(
                    AgentKnowledgeBase.agent_id == agent_id,
                    AgentKnowledgeBase.organization_id == self.org_id,
                )
            )
            query = query.filter(Upload.id.in_(upload_ids_q))
        if status_filter:
            query = query.filter(Upload.status == status_filter)

        # Generic faceted filters + sort.
        query = apply_filters(query, filters, column_map)
        total = query.count()
        query = apply_sort(query, column_map, sort_by, sort_order, Upload.updated_at)

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        # Map each upload to its linked agents (if any) so the UI can show
        # every owning agent. Uploads created from the agent form before save
        # are standalone and have no link yet.
        upload_ids = [i.id for i in items]
        agents_by_upload: dict[UUID, list[str]] = {}
        seen_pairs: set[tuple[UUID, str]] = set()
        if upload_ids:
            links = (
                self.db.query(KnowledgeBase.upload_id, AgentKnowledgeBase.agent_id)
                .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
                .filter(
                    KnowledgeBase.upload_id.in_(upload_ids),
                    AgentKnowledgeBase.organization_id == self.org_id,
                )
                .all()
            )
            for link_upload_id, link_agent_id in links:
                agent_str = str(link_agent_id)
                key = (link_upload_id, agent_str)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                agents_by_upload.setdefault(link_upload_id, []).append(agent_str)

        return items, total, agents_by_upload

    def rename_upload(self, upload_id: UUID, new_name: str) -> Upload:
        """Rename a KB document. Assumes ``new_name`` is already validated by
        the caller (non-empty, length-bounded). Raises ``ValueError`` when the
        upload is missing for the org (routers map it to a 404)."""
        upload = self._get_org_upload(upload_id)
        upload.file_name = new_name
        self.db.commit()
        self.db.refresh(upload)
        return upload

    def delete_upload(self, upload_id: UUID) -> None:
        """Delete a KB document: remove its ``KnowledgeBase`` row(s), the
        ``Upload`` row, and best-effort delete the backing R2 blob. Org-scoped;
        raises ``ValueError`` when the upload is missing (routers → 404)."""
        upload = self._get_org_upload(upload_id)
        file_path = upload.file_path

        self.db.query(KnowledgeBase).filter(
            KnowledgeBase.upload_id == upload_id,
            KnowledgeBase.organization_id == self.org_id,
        ).delete(synchronize_session=False)
        self.db.delete(upload)
        self.db.commit()

        if file_path:
            r2 = self._r2 or R2StorageService()
            try:
                r2.delete_file(file_path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Best-effort R2 delete of {} failed: {}", file_path, exc)

    def replace_upload_file(
        self,
        *,
        upload_id: UUID,
        fileobj: Any,
        file_name: Optional[str],
        content_type: Optional[str],
        size_bytes: int,
    ) -> Upload:
        """Swap the backing blob of an existing KB document: validate the new
        file, upload it to R2, point the ``Upload`` row at the new object and
        flip status back to ``processing`` so the caller re-runs ingestion.

        Preserves both security-relevant behaviours from the old route:
          * ``validate_upload_file`` runs BEFORE the R2 write (size + type
            contract) so a rejected file never leaves an orphan blob.
          * on a failed DB commit the just-written blob is best-effort deleted
            (orphan cleanup), the transaction rolled back, and the error
            re-raised — the old blob is left untouched.

        Raises ``ValueError`` when the upload is missing (routers → 404) and
        ``IngestionValidationError`` for a too-long name / bad type / oversize
        file (routers → 400). Returns the refreshed ``Upload``."""
        upload = self._get_org_upload(upload_id)

        new_name = _sanitize_kb_file_name(file_name or upload.file_name)
        # Backend enforcement of the name + size + type contract (single source
        # of truth in UploadService) — runs BEFORE the R2 write so a rejected
        # file never creates a blob. Replace writes ``Upload.file_name``
        # (``String(512)``), so it passes the wider name-length limit.
        self.validate_upload_file(
            file_name=new_name, size_bytes=size_bytes, max_name_length=512
        )
        resolved_type = content_type or "application/octet-stream"

        logger.info(
            "[upload] replace requested upload={} org={} old_name={} new_name={} new_size={}",
            upload.id, self.org_id, upload.file_name, new_name, size_bytes,
        )

        r2 = self._r2 or R2StorageService()
        new_object_key = build_r2_object_key(
            org_id=self.org_id,
            kind=KB_DOCUMENT,
            subpath=f"{uuid4()}/{new_name}",
        )
        try:
            r2.upload_fileobj(fileobj, new_object_key, content_type=resolved_type)
        except Exception:
            logger.exception(
                "[upload] R2 replace upload failed upload={} key={}",
                upload.id, new_object_key,
            )
            raise

        old_path = upload.file_path

        upload.file_path = new_object_key
        upload.file_name = new_name
        upload.file_type = resolved_type
        upload.size_bytes = size_bytes
        # Both editions intentionally re-run the pipeline on replace: the new
        # blob must be re-embedded, so flip back to "processing" and let the
        # caller re-queue rather than marking "ready" (stale embeddings).
        upload.status = "processing"
        try:
            self.db.commit()
            self.db.refresh(upload)
        except Exception:
            # DB write failed AFTER the new blob was uploaded — roll back and
            # delete the just-written blob so we don't leak an orphan object
            # (mirrors create_upload_from_file's create-path cleanup). The old
            # blob is untouched, so the row still points at valid storage.
            logger.exception(
                "[upload] DB commit failed on replace upload={}; cleaning up new R2 blob {}",
                upload.id, new_object_key,
            )
            self.db.rollback()
            try:
                r2.delete_file(new_object_key)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Best-effort R2 cleanup of orphaned replace blob {} failed: {}",
                    new_object_key, exc,
                )
            raise

        # Best-effort delete of the old R2 blob.
        if old_path and old_path != new_object_key:
            try:
                r2.delete_file(old_path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Best-effort delete of old R2 blob {} failed: {}", old_path, exc)

        return upload

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
