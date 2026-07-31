"""Shared knowledge-base route implementation.

Both the Core (``core/api/v1/knowledge_base.py``) and Enterprise
(``ee/api/v1/knowledge_base.py``) editions expose an identical knowledge-base
API. The only differences are the auth dependency and how the organization id
is derived from the resolved claims. Rather than duplicate every handler, the
full router is built here and parameterized with those two concerns, so there
is a single source of truth for the route logic.
"""

from typing import Any, Callable, List, Optional
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class ListPipelineRunsRequest(BaseModel):
    """Pagination + search + filter body for ``POST /{upload_id}/runs/list``."""

    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    status_filter: Optional[List[str]] = None
    is_active_only: bool = False


class SetAgentKbActiveRunRequest(BaseModel):
    """Body for ``PUT /agents/{agent_id}/knowledge-bases/{kb_id}/active-run``.

    ``active_ingestion_pipeline_run_id = None`` clears the per-agent pin so the
    agent falls back to the KB default.
    """

    active_ingestion_pipeline_run_id: Optional[UUID] = None

from core.api.v1.faceted_schemas import FacetsRequest
from core.database.session import get_db
from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.services.document_processing_service import DocumentProcessingService
from core.services.ingestion_queue import enqueue_reprocess, enqueue_upload
from core.services.ingestion_run_service import IngestionRunService
from core.services.rag.embedder_factory import EMBEDDERS
from core.services.rag.factory import VECTOR_STORES
from core.services.rag.parser_factory import PARSERS
from core.services.rag.tokeniser_factory import TOKENISERS
from core.services.r2_storage_service import R2StorageService
from core.services.upload_service import UploadService
from core.utils.faceted_query import apply_filters, apply_sort, build_facets, distinct_values
from core.utils.list_params import resolve_sort
from shared.config import settings

# Knowledge-base documents are ``Upload`` rows scoped to the kb_document purpose.
KB_FACET_FIELDS = ["status"]


def _kb_column_map() -> dict:
    """Scalar columns exposed for filtering / sorting / faceting on documents."""
    return {
        "file_name": Upload.file_name,
        "status": Upload.status,
        "size_bytes": Upload.size_bytes,
        "created_at": Upload.created_at,
        "updated_at": Upload.updated_at,
    }


def _kb_base_query(db: Session, org_id: UUID):
    """Org-scoped base query for kb documents (excludes soft-deleted rows)."""
    return db.query(Upload).filter(
        Upload.organization_id == org_id,
        Upload.purpose == "kb_document",
        Upload.deleted_at.is_(None),
    )


def _signed_url(file_path: str | None, r2: R2StorageService | None = None) -> str | None:
    if not file_path:
        return None
    try:
        return (r2 or R2StorageService()).generate_presigned_url(file_path)
    except Exception as exc:
        logger.debug("Failed to generate presigned URL for {}: {}", file_path, exc)
        return None


def _upload_to_payload(upload: Upload, r2: R2StorageService | None = None) -> dict:
    payload = upload.to_dict()
    payload["url"] = _signed_url(upload.file_path, r2)
    return payload


def _kb_for_upload(db: Session, org_id: UUID, upload_id: UUID) -> KnowledgeBase:
    """Resolve the KnowledgeBase row backing an upload for enqueue flows. There
    is exactly one per upload — a missing KB means the earlier create failed
    and reprocess/replace is invalid, so surface a 500 rather than silently
    dropping the enqueue."""
    kb = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.upload_id == upload_id,
            KnowledgeBase.organization_id == org_id,
        )
        .first()
    )
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge base row missing for upload",
        )
    return kb


async def _start_ingestion_run(
    db: Session,
    *,
    upload: Upload,
    kb: KnowledgeBase,
    org_id: UUID,
    request_config: dict | None,
    delete_existing: bool,
) -> tuple[IngestionPipelineRun, int]:
    """Create a pending IngestionPipelineRun, defer the Procrastinate job, and
    stamp the returned job id on the run. Shared by every KB write path
    (upload / replace / reprocess / custom /runs) so the "create-run → enqueue
    → stamp" trio lives in exactly one place.

    On defer failure the pending run is marked ``failed`` (not orphaned) and
    the exception is re-raised for the caller to translate to an HTTP error.
    """
    cfg = IngestionRunService.resolve_run_config(
        db, org_id, kb.id, request_config
    )
    run = IngestionRunService.begin_pending_run(
        db,
        upload_id=upload.id,
        knowledge_base_id=kb.id,
        org_id=org_id,
        config=cfg,
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
    return run, job_id


def build_knowledge_base_router(
    auth_dependency: Callable[..., Any],
    resolve_org_id: Callable[[Any], UUID],
) -> APIRouter:
    """Build the knowledge-base router.

    :param auth_dependency: FastAPI dependency that authenticates the request
        and returns the edition's claims object.
    :param resolve_org_id: Extracts the organization UUID from those claims.
    """
    router = APIRouter()

    @router.post("/list")
    def list_documents(
        body: dict = Body(default={}),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)

        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 20), 1), 100)
        search = body.get("search")
        agent_id = body.get("agent_id")
        status_filter = body.get("status")

        column_map = _kb_column_map()
        query = _kb_base_query(db, org_id)

        # Named params (back-compat): free-text search, owning-agent and status.
        if search:
            query = query.filter(Upload.file_name.ilike(f"%{search}%"))
        if agent_id:
            try:
                agent_uuid = UUID(str(agent_id))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id"
                )
            upload_ids_q = (
                db.query(KnowledgeBase.upload_id)
                .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
                .filter(
                    AgentKnowledgeBase.agent_id == agent_uuid,
                    AgentKnowledgeBase.organization_id == org_id,
                )
            )
            query = query.filter(Upload.id.in_(upload_ids_q))
        if status_filter:
            query = query.filter(Upload.status == status_filter)

        # Generic faceted filters + sort.
        query = apply_filters(query, body.get("filters"), column_map)
        total = query.count()
        sort_by, sort_order = resolve_sort(body, "updated_at")
        query = apply_sort(query, column_map, sort_by, sort_order, Upload.updated_at)

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        r2 = R2StorageService()

        # Map each upload to its linked agent (if any) so the UI can show the
        # owning agent. Uploads created from the agent form before save are
        # standalone and have no link yet.
        upload_ids = [i.id for i in items]
        agent_by_upload: dict[UUID, str] = {}
        if upload_ids:
            links = (
                db.query(KnowledgeBase.upload_id, AgentKnowledgeBase.agent_id)
                .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
                .filter(
                    KnowledgeBase.upload_id.in_(upload_ids),
                    AgentKnowledgeBase.organization_id == org_id,
                )
                .all()
            )
            for link_upload_id, link_agent_id in links:
                agent_by_upload.setdefault(link_upload_id, str(link_agent_id))

        def _payload_with_agent(upload: Upload) -> dict:
            payload = _upload_to_payload(upload, r2)
            payload["agent_id"] = agent_by_upload.get(upload.id)
            return payload

        return {
            "items": [_payload_with_agent(i) for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def upload_document(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        agent_id: str | None = Form(None),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Upload a knowledge-base document.

        ``agent_id`` is optional: when omitted (e.g. uploading from the agent
        create form before the agent has been saved), the upload row is created
        standalone and the caller is expected to attach it on agent save via
        ``upload_ids`` on the create_agent payload.
        """
        org_id = resolve_org_id(claims)
        agent_uuid: UUID | None = None
        agent_config = None
        if agent_id:
            try:
                agent_uuid = UUID(agent_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id"
                )

            agent = (
                db.query(Agent)
                .filter(Agent.id == agent_uuid, Agent.organization_id == org_id)
                .first()
            )
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
                )

            # Uploads from this admin route attach directly to the agent's
            # PUBLISHED config — i.e. the document goes live for the call
            # pipeline as soon as the upload finishes ingesting. That is the
            # established behaviour for this endpoint; per-version isolation
            # only applies to the editor flow, where saves clone the chosen
            # source version. Resolving up-front here (before touching R2)
            # also means a missing-publication 409 doesn't orphan the blob.
            from core.models.agent_config import AgentConfig

            agent_config = None
            if agent.published_config_id:
                agent_config = (
                    db.query(AgentConfig)
                    .filter(
                        AgentConfig.id == agent.published_config_id,
                        AgentConfig.deleted_at.is_(None),
                    )
                    .first()
                )
            if not agent_config:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Agent has no published configuration yet. Save and publish the agent before uploading knowledge base documents.",
                )

        file_name = file.filename or "upload.bin"
        content_type = file.content_type or "application/octet-stream"
        user_id = UUID(claims.user_id) if claims.user_id else None

        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
        if not size_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

        upload, _kb, _run = await UploadService(
            db, user_id=user_id, org_id=org_id
        ).create_upload_from_file(
            fileobj=file.file,
            file_name=file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            agent_id=agent_uuid,
            agent_config_id=agent_config.id if agent_config is not None else None,
        )

        return _upload_to_payload(upload)

    @router.patch("/{upload_id}")
    def rename_document(
        upload_id: str,
        body: dict = Body(...),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        try:
            uid = UUID(upload_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

        new_name = (body.get("file_name") or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="file_name is required"
            )
        if len(new_name) > 512:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="file_name too long (max 512)"
            )

        upload = (
            db.query(Upload).filter(Upload.id == uid, Upload.organization_id == org_id).first()
        )
        if not upload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

        upload.file_name = new_name
        db.commit()
        db.refresh(upload)
        return _upload_to_payload(upload)

    @router.patch("/{upload_id}/file")
    async def replace_document_file(
        upload_id: str,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        file_name: str | None = Form(None),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        try:
            uid = UUID(upload_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

        upload = (
            db.query(Upload).filter(Upload.id == uid, Upload.organization_id == org_id).first()
        )
        if not upload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
        if not size_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

        new_name = (file_name or "").strip() or file.filename or upload.file_name
        if len(new_name) > 512:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="file_name too long (max 512)"
            )
        content_type = file.content_type or "application/octet-stream"

        new_object_key = f"knowledge-base/{org_id}/{uuid4()}/{new_name}"
        R2StorageService().upload_fileobj(file.file, new_object_key, content_type=content_type)

        old_path = upload.file_path

        upload.file_path = new_object_key
        upload.file_name = new_name
        upload.file_type = content_type
        upload.size_bytes = size_bytes
        # Both editions intentionally re-run the pipeline on replace: the new
        # blob must be re-embedded, so flip back to "processing" and re-queue
        # rather than marking "ready" (which would leave stale embeddings).
        upload.status = "processing"
        db.commit()
        db.refresh(upload)

        # Best-effort delete of the old R2 blob
        if old_path and old_path != new_object_key:
            try:
                R2StorageService().delete_file(old_path)
            except Exception as exc:
                logger.debug("Best-effort delete of old R2 blob {} failed: {}", old_path, exc)

        kb = _kb_for_upload(db, org_id, upload.id)
        await _start_ingestion_run(
            db,
            upload=upload,
            kb=kb,
            org_id=org_id,
            request_config=None,
            delete_existing=True,
        )

        return _upload_to_payload(upload)

    @router.post("/{upload_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
    async def reprocess_document(
        upload_id: str,
        background_tasks: BackgroundTasks,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Re-run the processing pipeline for an existing upload.

        Used to retry a ``failed`` document (e.g. after configuring the OpenAI
        key for embeddings) without forcing the user to upload the file again.
        The original blob already lives in R2, so we just reset the status,
        clear the previous error, and re-queue the pipeline.
        """
        org_id = resolve_org_id(claims)
        try:
            uid = UUID(upload_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

        upload = (
            db.query(Upload).filter(Upload.id == uid, Upload.organization_id == org_id).first()
        )
        if not upload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

        if not upload.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload has no stored file to reprocess",
            )

        # Flip to processing and drop the stale error so the UI reflects the
        # retry immediately, before the background task runs.
        upload.status = "processing"
        meta = dict(upload.meta_data or {})
        meta.pop("error", None)
        upload.meta_data = meta
        db.commit()
        db.refresh(upload)

        kb = _kb_for_upload(db, org_id, upload.id)
        await _start_ingestion_run(
            db,
            upload=upload,
            kb=kb,
            org_id=org_id,
            request_config=None,
            delete_existing=True,
        )

        return _upload_to_payload(upload)

    @router.delete("/{upload_id}", status_code=status.HTTP_200_OK)
    def delete_document(
        upload_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        try:
            uid = UUID(upload_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

        upload = (
            db.query(Upload).filter(Upload.id == uid, Upload.organization_id == org_id).first()
        )
        if not upload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

        file_path = upload.file_path

        db.query(KnowledgeBase).filter(
            KnowledgeBase.upload_id == uid, KnowledgeBase.organization_id == org_id
        ).delete(synchronize_session=False)
        db.delete(upload)
        db.commit()

        if file_path:
            try:
                R2StorageService().delete_file(file_path)
            except Exception as exc:
                logger.debug("Best-effort R2 delete of {} failed: {}", file_path, exc)

        return {"ok": True}

    @router.post("/facets")
    def get_document_facets(
        body: FacetsRequest,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        filters = [f.model_dump() for f in body.filters] if body.filters else None
        return build_facets(
            lambda: _kb_base_query(db, org_id), _kb_column_map(), KB_FACET_FIELDS, filters
        )

    @router.get("/filter-values")
    def get_document_filter_values(
        column_name: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        column_map = _kb_column_map()
        allowed = {k: column_map[k] for k in ("status", "file_name")}
        return distinct_values(_kb_base_query(db, org_id), allowed, column_name)

    # ── RAG pipeline runs (parser / tokeniser / embedder / vector store) ────
    # Endpoints for A/B-ing the ingestion pipeline: one upload can carry many
    # ``ingestion_pipeline_runs`` (different model, tokeniser, store); at most
    # one is active per upload and drives live retrieval. Everything else
    # stays queryable via the RAG store's ``ingestion_run_id`` filter so
    # evals compare runs side-by-side without swapping the live pipeline.

    @router.get("/pipeline-options")
    def get_pipeline_options(claims=Depends(auth_dependency)):
        """Advertise every registered parser / tokeniser / embedder / vector store
        so callers know what values are legal in a ``run_config`` body."""
        _ = claims  # authn only; no per-org filtering — registries are global.
        defaults = {
            "parser": settings.DEFAULT_PARSER,
            "tokeniser": settings.DEFAULT_TOKENISER,
            "embedding_provider": settings.DEFAULT_EMBEDDING_PROVIDER,
            "embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
            "embedding_dimensions": settings.DEFAULT_EMBEDDING_DIMENSIONS,
            "vector_store": settings.DEFAULT_VECTOR_STORE,
        }
        return {
            "parsers": sorted(PARSERS.keys()),
            "tokenisers": sorted(TOKENISERS.keys()),
            "embedders": sorted(EMBEDDERS.keys()),
            "vector_stores": sorted(VECTOR_STORES.keys()),
            "defaults": defaults,
        }

    def _resolve_upload(db: Session, org_id: UUID, upload_id: str) -> Upload:
        try:
            uid = UUID(upload_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")
        upload = (
            db.query(Upload).filter(Upload.id == uid, Upload.organization_id == org_id).first()
        )
        if not upload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
        return upload

    @router.get("/{upload_id}/runs")
    def list_pipeline_runs(
        upload_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        runs = IngestionRunService.list_runs(db, upload.id)
        return {"items": [r.to_dict() for r in runs]}

    @router.post("/{upload_id}/runs/list")
    def list_pipeline_runs_paginated(
        upload_id: str,
        body: ListPipelineRunsRequest = Body(default_factory=ListPipelineRunsRequest),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Paginated + searchable list of pipeline runs for one upload —
        canonical ``POST /list`` shape (search, sort_by, sort_order,
        page_no, page_size, status_filter, is_active_only)."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        rows, total = IngestionRunService.list_runs_paginated(
            db,
            org_id=org_id,
            upload_id=upload.id,
            search=body.search,
            sort_by=body.sort_by,
            sort_order=body.sort_order,
            page_no=body.page_no,
            page_size=body.page_size,
            status_filter=body.status_filter,
            is_active_only=body.is_active_only,
        )
        return {
            "data": [r.to_dict() for r in rows],
            "total": total,
            "page_no": body.page_no,
            "page_size": body.page_size,
        }

    @router.post("/{upload_id}/runs", status_code=status.HTTP_202_ACCEPTED)
    async def create_pipeline_run(
        upload_id: str,
        body: dict = Body(default={}),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Kick off a NEW ingestion run for an existing upload with a custom
        pipeline configuration (parser / tokeniser / embedder / vector store).
        Previous runs are preserved so evals can compare them.

        Body may contain any subset of:
        ``parser`` (str), ``parser_config`` (dict),
        ``tokeniser`` (str), ``tokeniser_config`` (dict),
        ``embedding_provider`` (str), ``embedding_model`` (str),
        ``embedding_dimensions`` (int), ``embedding_version`` (str),
        ``vector_store`` (str), ``vector_store_ref`` (dict).
        Anything omitted falls back to system defaults resolved by
        ``IngestionRunService.resolve_run_config``.
        """
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        if not upload.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload has no stored file to reprocess",
            )

        allowed = {
            "parser", "parser_config",
            "tokeniser", "tokeniser_config",
            "embedding_provider", "embedding_model",
            "embedding_dimensions", "embedding_version",
            "vector_store", "vector_store_ref",
        }
        run_config = {k: v for k, v in (body or {}).items() if k in allowed}

        # Fail fast on obvious mis-typed slugs (unknown parser / tokeniser / provider / store)
        # so the queued job doesn't error mid-ingest.
        if "parser" in run_config and run_config["parser"] not in PARSERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown parser {run_config['parser']!r}. Available: {sorted(PARSERS)}",
            )
        if "tokeniser" in run_config and run_config["tokeniser"] not in TOKENISERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown tokeniser {run_config['tokeniser']!r}. Available: {sorted(TOKENISERS)}",
            )
        if "embedding_provider" in run_config and run_config["embedding_provider"] not in EMBEDDERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown embedding provider {run_config['embedding_provider']!r}. "
                f"Available: {sorted(EMBEDDERS)}",
            )
        if "vector_store" in run_config and run_config["vector_store"] not in VECTOR_STORES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown vector store {run_config['vector_store']!r}. "
                f"Available: {sorted(VECTOR_STORES)}",
            )

        kb = _kb_for_upload(db, org_id, upload.id)
        run, job_id = await _start_ingestion_run(
            db,
            upload=upload,
            kb=kb,
            org_id=org_id,
            request_config=run_config or None,
            delete_existing=False,
        )
        logger.info(
            "[ingestion] enqueued custom run for upload {} (run={}, job={}, overrides={})",
            upload.id, run.id, job_id, sorted(run_config.keys()),
        )
        return {
            "upload_id": str(upload.id),
            "ingestion_run_id": str(run.id),
            "job_id": job_id,
            "run_config": run_config,
            "status": "queued",
        }

    @router.post("/{upload_id}/runs/{run_id}/activate", status_code=status.HTTP_200_OK)
    def activate_pipeline_run(
        upload_id: str,
        run_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Flip ``is_active`` to this run so live retrieval (the ``read_document``
        tool) switches to its embedder + store. The previously-active run stays
        in the DB and remains queryable for evals via its ``ingestion_run_id``."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        try:
            rid = UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid run_id")
        run = (
            db.query(IngestionPipelineRun)
            .filter(
                IngestionPipelineRun.id == rid,
                IngestionPipelineRun.upload_id == upload.id,
                IngestionPipelineRun.organization_id == org_id,
            )
            .first()
        )
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found for this upload",
            )
        if run.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot activate a run with status={run.status!r}; only 'ready' is allowed",
            )
        activated = IngestionRunService.activate_run(db, run.id)
        return activated.to_dict()

    @router.put(
        "/agents/{agent_id}/knowledge-bases/{kb_id}/active-run",
        status_code=status.HTTP_200_OK,
    )
    def set_agent_kb_active_run(
        agent_id: str,
        kb_id: str,
        body: SetAgentKbActiveRunRequest = Body(...),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Set (or clear when the body's run id is null) the per-agent pin for
        one AgentKnowledgeBase row. Falls back to the KB-level default when
        cleared. Validation (row exists, run in same KB, run is ready) lives
        in ``IngestionRunService.set_agent_kb_active_run`` — the router is a
        pure transport."""
        org_id = resolve_org_id(claims)
        try:
            aid = UUID(agent_id)
            kid = UUID(kb_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agent_id or kb_id",
            )
        akb = IngestionRunService.set_agent_kb_active_run(
            db,
            org_id=org_id,
            agent_id=aid,
            knowledge_base_id=kid,
            run_id=body.active_ingestion_pipeline_run_id,
        )
        return akb.to_dict()

    return router
