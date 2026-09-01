"""Shared knowledge-base route implementation.

Both the Core (``core/api/v1/knowledge_base.py``) and Enterprise
(``ee/api/v1/knowledge_base.py``) editions expose an identical knowledge-base
API. The only differences are the auth dependency and how the organization id
is derived from the resolved claims. Rather than duplicate every handler, the
full router is built here and parameterized with those two concerns, so there
is a single source of truth for the route logic.
"""

from typing import Any, Callable, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.api.v1.faceted_schemas import FacetsRequest
from core.database.session import get_db
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.evals.eval_service import EvalRunSummary, EvalService
from core.services.evals.errors import EvalGenerationError, EvalNotFoundError
from core.services.ingestion_errors import (
    AgentHasNoPublishedConfigError,
    AgentKnowledgeBaseNotFoundError,
    IngestionConfigInactiveError,
    IngestionConfigNotFoundError,
    IngestionRunKbMismatchError,
    IngestionRunNotFoundError,
    IngestionRunNotReadyError,
    IngestionValidationError,
    UnknownRagComponentError,
    is_unique_violation,
)
from core.services.ingestion_queue import (
    enqueue_eval_for_ingestion_run,
    enqueue_reprocess,
    enqueue_upload,
)
from core.services.ingestion_run_service import IngestionRunService
from core.services.rag.component_registry import ensure_rag_component
from core.services.rag.embedder_factory import EMBEDDERS
from core.services.rag.factory import VECTOR_STORES
from core.services.rag.parser_factory import PARSERS
from core.services.rag.tokeniser_factory import TOKENISERS
from core.services.r2_storage_service import (
    R2StorageService,
    signed_url_or_none,
)
from core.services.upload_service import UploadService
from core.utils.faceted_query import build_facets, distinct_values
from core.utils.list_params import resolve_sort
from shared.config import settings


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


class EvalSummaryByIngestionRequest(BaseModel):
    """Body for ``POST /{upload_id}/eval-summary/by-ingestion`` — batch lookup
    used by the runs table to paint the per-row "Evals" chip without an N+1.
    """

    ingestion_run_ids: List[UUID] = Field(default_factory=list)


class ManualQuestionIn(BaseModel):
    """One user-authored Q&A pair. ``expected_source_snippet`` and
    ``category`` are optional; ``external_id`` is optional (auto-minted
    when absent)."""

    question: str = Field(..., min_length=1, max_length=4000)
    expected_answer: str = Field(..., min_length=1, max_length=8000)
    expected_source_snippet: Optional[str] = Field(default=None, max_length=8000)
    category: Optional[str] = Field(default=None, max_length=64)
    external_id: Optional[str] = Field(default=None, max_length=64)


class AddManualQuestionsRequest(BaseModel):
    """Body for ``POST /{upload_id}/evals/manual`` — appends questions to the
    upload's eval set without wiping existing rows."""

    questions: List[ManualQuestionIn] = Field(..., min_length=1, max_length=200)


class UpdateQuestionRequest(BaseModel):
    """Body for ``PUT /{upload_id}/evals/questions/{question_id}``. All fields
    optional so callers can PATCH-style update; explicit ``null`` on the
    optional fields clears them."""

    question: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    expected_answer: Optional[str] = Field(default=None, min_length=1, max_length=8000)
    expected_source_snippet: Optional[str] = Field(default=None, max_length=8000)
    category: Optional[str] = Field(default=None, max_length=64)


class TriggerEvalRunRequest(BaseModel):
    """Body for ``POST /{upload_id}/evals/run`` — the ``ingestion_run_id`` is
    optional; when omitted the active ingestion run for the upload is used.

    Per-run overrides (``top_k`` / ``answer_model`` / ``judge_model``) are
    intentionally NOT exposed here yet — the shared Procrastinate task does
    not accept them, and quietly ignoring caller-supplied values would break
    the API contract. Add them here + wire them through the task if a real
    need arises."""

    ingestion_run_id: Optional[UUID] = None

# Knowledge-base documents are ``Upload`` rows scoped to the kb_document purpose.
KB_FACET_FIELDS = ["status"]


# ── Typed-error → HTTP mapping ─────────────────────────────────────────────
# The ingestion services raise typed exceptions from
# ``core.services.ingestion_errors`` (transport-agnostic per backend
# standards). Every KB endpoint that can hit those errors funnels them
# through this helper so 400/404 statuses stay consistent across handlers.

_INGESTION_ERROR_HTTP_MAP: tuple[tuple[type, int], ...] = (
    (IngestionRunNotFoundError, status.HTTP_404_NOT_FOUND),
    (IngestionConfigNotFoundError, status.HTTP_404_NOT_FOUND),
    (AgentHasNoPublishedConfigError, status.HTTP_404_NOT_FOUND),
    (AgentKnowledgeBaseNotFoundError, status.HTTP_404_NOT_FOUND),
    (IngestionRunNotReadyError, status.HTTP_400_BAD_REQUEST),
    (IngestionRunKbMismatchError, status.HTTP_400_BAD_REQUEST),
    (IngestionConfigInactiveError, status.HTTP_400_BAD_REQUEST),
    (UnknownRagComponentError, status.HTTP_400_BAD_REQUEST),
    (IngestionValidationError, status.HTTP_400_BAD_REQUEST),
)


def _http_status_for_ingestion_error(exc: Exception) -> Optional[int]:
    """Return the mapped HTTP status for a typed ingestion error, or None
    if the exception is not something this router owns (let it propagate)."""
    for exc_type, code in _INGESTION_ERROR_HTTP_MAP:
        if isinstance(exc, exc_type):
            return code
    return None


def _raise_http_for_ingestion_error(exc: Exception) -> None:
    """Convert a typed ingestion error into an HTTPException. No-op when the
    exception isn't a mapped type — callers should let it propagate."""
    code = _http_status_for_ingestion_error(exc)
    if code is not None:
        raise HTTPException(status_code=code, detail=str(exc)) from exc


def _upload_to_payload(upload: Upload, r2: R2StorageService | None = None) -> dict:
    payload = upload.to_dict()
    payload["url"] = signed_url_or_none(upload.file_path, r2)
    return payload


def _eval_run_summary_to_dict(s: EvalRunSummary) -> dict:
    """Transport-layer serializer for ``EvalRunSummary`` (a dataclass, so it
    has no ``to_dict``). Kept here rather than on the service so the service
    stays HTTP-agnostic."""
    return {
        "run_id": str(s.run_id),
        "upload_id": str(s.upload_id),
        "ingestion_run_id": str(s.ingestion_run_id) if s.ingestion_run_id else None,
        "run_number": s.run_number,
        "triggered_by": s.triggered_by,
        "top_k": s.top_k,
        "answer_model": s.answer_model,
        "judge_model": s.judge_model,
        "status": s.status,
        "error": s.error,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "summary": s.summary or {},
    }


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
    ingestion_config_id: UUID | None = None,
) -> tuple[IngestionPipelineRun, int]:
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
        status_filter = body.get("status")
        sort_by, sort_order = resolve_sort(body, "updated_at")

        # ``agent_id`` (first-attached, historic single-value field) is kept in
        # the response for backwards compatibility with any FE code that still
        # reads it. ``agent_ids`` is the full list — new consumers prefer it.
        agent_id = body.get("agent_id")
        agent_uuid: UUID | None = None
        if agent_id:
            try:
                agent_uuid = UUID(str(agent_id))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id"
                )

        items, total, agents_by_upload = UploadService(db, org_id=org_id).list_kb_documents(
            search=search,
            agent_id=agent_uuid,
            status_filter=status_filter,
            filters=body.get("filters"),
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        r2 = R2StorageService()

        def _payload_with_agent(upload: Upload) -> dict:
            payload = _upload_to_payload(upload, r2)
            agents = agents_by_upload.get(upload.id, [])
            payload["agent_id"] = agents[0] if agents else None
            payload["agent_ids"] = agents
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
        ingestion_config_id: str | None = Form(None),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Upload a knowledge-base document.

        ``agent_id`` is optional: when omitted (e.g. uploading from the agent
        create form before the agent has been saved), the upload row is created
        standalone and the caller is expected to attach it on agent save via
        ``upload_ids`` on the create_agent payload.

        ``ingestion_config_id`` is optional: when provided, the first ingestion
        run snapshots that saved ``IngestionConfig`` instead of using the
        env defaults. Same semantics as ``POST /runs`` — see ``resolve_run_config``.
        """
        org_id = resolve_org_id(claims)
        agent_uuid: UUID | None = None
        agent_config = None
        ingestion_config_uuid: UUID | None = None
        if ingestion_config_id:
            try:
                ingestion_config_uuid = UUID(ingestion_config_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid ingestion_config_id",
                )
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

        # Fast-path duplicate-name check: KnowledgeBase enforces
        # UniqueConstraint(organization_id, name) — without this pre-check the
        # collision becomes an opaque IntegrityError → HTTP 500 with no user
        # message. Surface a friendly 409 here BEFORE R2 write so no orphan
        # blob is created for the doomed insert. The IntegrityError catch
        # below still covers the (rare) race where two concurrent uploads
        # land the same name between this check and the service commit.
        duplicate_name = (
            db.query(KnowledgeBase.id)
            .filter(
                KnowledgeBase.organization_id == org_id,
                KnowledgeBase.name == file_name,
            )
            .first()
        )
        if duplicate_name is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A document named '{file_name}' already exists. "
                    "Rename the file or delete the existing document."
                ),
            )

        logger.info(
            "[upload] received upload org={} user={} agent={} file_name={} content_type={} size={}",
            org_id, user_id, agent_uuid, file_name, content_type, size_bytes,
        )

        try:
            upload, _kb, _run = await UploadService(
                db, user_id=user_id, org_id=org_id
            ).create_upload_from_file(
                fileobj=file.file,
                file_name=file_name,
                content_type=content_type,
                size_bytes=size_bytes,
                agent_id=agent_uuid,
                agent_config_id=agent_config.id if agent_config is not None else None,
                ingestion_config_id=ingestion_config_uuid,
            )
        except IntegrityError as exc:
            # Race safety net: another concurrent upload committed the same
            # name after our pre-check. The service has already rolled back
            # and cleaned up the R2 blob (upload_service.py). Only translate
            # the unique_violation — re-raise other integrity errors so we
            # don't silently mask an unrelated schema issue.
            if is_unique_violation(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"A document named '{file_name}' already exists. "
                        "Rename the file or delete the existing document."
                    ),
                ) from exc
            raise
        except (
            IngestionConfigNotFoundError,
            IngestionConfigInactiveError,
            UnknownRagComponentError,
            IngestionValidationError,
        ) as exc:
            # Bad ingestion_config_id (missing / inactive / references a
            # slug that's since been removed). UploadService has already
            # rolled back the DB write and cleaned the R2 blob.
            _raise_http_for_ingestion_error(exc)

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

        try:
            upload = UploadService(db, org_id=org_id).rename_upload(uid, new_name)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
            ) from exc
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

        # Resolve first so the 404 for a missing upload takes precedence over
        # the empty-file 400 (preserving the original error ordering) and so the
        # requested-name fallback can reference the current file name.
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

        # Requested name (form value wins, else the uploaded filename); the
        # service falls back to the upload's current name when both are empty.
        requested_name = (file_name or "").strip() or file.filename
        content_type = file.content_type or "application/octet-stream"

        # The service validates (size + type contract), uploads to R2, updates
        # the row, and cleans up an orphan blob on a failed commit. It raises
        # IngestionValidationError (→ 400) for a too-long name / bad type /
        # oversize file, and ValueError (→ 404) for a missing upload.
        try:
            upload = UploadService(db, org_id=org_id).replace_upload_file(
                upload_id=uid,
                fileobj=file.file,
                file_name=requested_name,
                content_type=content_type,
                size_bytes=size_bytes,
            )
        except IngestionValidationError as exc:
            _raise_http_for_ingestion_error(exc)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
            ) from exc

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

        logger.info(
            "[ingestion] reprocess requested upload={} org={} user={} prev_status={}",
            upload.id, org_id, claims.user_id, upload.status,
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

        try:
            UploadService(db, org_id=org_id).delete_upload(uid)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
            ) from exc

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
            lambda: UploadService.kb_base_query(db, org_id),
            UploadService.kb_column_map(),
            KB_FACET_FIELDS,
            filters,
        )

    @router.get("/filter-values")
    def get_document_filter_values(
        column_name: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        org_id = resolve_org_id(claims)
        column_map = UploadService.kb_column_map()
        allowed = {k: column_map[k] for k in ("status", "file_name")}
        return distinct_values(UploadService.kb_base_query(db, org_id), allowed, column_name)

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
        runs = IngestionRunService.list_runs(db, upload.id, org_id=org_id)
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

        Body may contain either:

        - ``ingestion_config_id`` (UUID) — snapshot every recipe field from a
          saved ``IngestionConfig``. When present, individual field overrides
          in the body are ignored (a saved config is a fixed recipe).

        or any subset of the individual fields:
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

        raw_body = body or {}

        # Parse the optional ingestion_config_id up front (backend enforces
        # even if the frontend omits validation).
        ingestion_config_id: UUID | None = None
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
            try:
                for kind in (
                    "parser", "tokeniser", "embedding_provider", "vector_store",
                ):
                    if kind in run_config:
                        ensure_rag_component(kind, run_config[kind])
            except UnknownRagComponentError as exc:
                _raise_http_for_ingestion_error(exc)
        else:
            # Discard any per-field entries silently when a config was chosen
            # so the response reflects what was actually applied.
            run_config = {}

        kb = _kb_for_upload(db, org_id, upload.id)
        try:
            run, job_id = await _start_ingestion_run(
                db,
                upload=upload,
                kb=kb,
                org_id=org_id,
                request_config=run_config or None,
                delete_existing=False,
                ingestion_config_id=ingestion_config_id,
            )
        except (
            IngestionConfigNotFoundError,
            IngestionConfigInactiveError,
            UnknownRagComponentError,
            IngestionValidationError,
        ) as exc:
            _raise_http_for_ingestion_error(exc)
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
        activated = IngestionRunService.activate_run(db, run.id, org_id=org_id)
        return activated.to_dict()

    @router.get("/{upload_id}/runs/{run_id}/chunks")
    def list_pipeline_run_chunks(
        upload_id: str,
        run_id: str,
        page_no: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=200),
        search: Optional[str] = Query(default=None),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Paginated list of chunks produced by a single ingestion run —
        powers the chunks drawer on the KB → Ingestion runs tab."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        try:
            rid = UUID(run_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid run_id"
            )
        try:
            rows, total = IngestionRunService.list_chunks_paginated(
                db,
                org_id=org_id,
                upload_id=upload.id,
                run_id=rid,
                search=search,
                page_no=page_no,
                page_size=page_size,
            )
        except IngestionRunNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found for this upload",
            )
        return {
            "data": [
                {
                    "id": str(c.id),
                    "chunk_index": c.chunk_index,
                    "chunk_text": c.chunk_text,
                    "chunk_metadata": c.chunk_metadata,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in rows
            ],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    @router.post("/{upload_id}/eval-summary/by-ingestion")
    def eval_summary_by_ingestion(
        upload_id: str,
        body: EvalSummaryByIngestionRequest = Body(default_factory=EvalSummaryByIngestionRequest),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Batch lookup: for each ingestion run id in the body, return the
        latest eval-batch summary. Powers the "Evals" chip in the runs table
        (one call for every visible page — no N+1). Missing keys → no eval
        was run for that ingestion run."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        by_ingestion = EvalService().latest_summaries_by_ingestion(
            db,
            org_id=org_id,
            upload_id=upload.id,
            ingestion_run_ids=body.ingestion_run_ids,
        )
        return {
            "items": {k: _eval_run_summary_to_dict(v) for k, v in by_ingestion.items()},
        }

    @router.get("/{upload_id}/runs/{ingestion_run_id}/eval-runs")
    def list_eval_runs_for_ingestion(
        upload_id: str,
        ingestion_run_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Every eval batch that scored one ingestion run, newest first — the
        drawer's run-picker reads from this."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        try:
            iid = UUID(ingestion_run_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ingestion_run_id"
            )
        summaries = EvalService().list_runs_for_ingestion(
            db,
            org_id=org_id,
            upload_id=upload.id,
            ingestion_run_id=iid,
        )
        return {"items": [_eval_run_summary_to_dict(s) for s in summaries]}

    @router.get("/{upload_id}/eval-runs/{run_id}")
    def get_eval_run_detail(
        upload_id: str,
        run_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Return summary + every scored question for one eval batch — the
        drawer body. Org-scoped in the service so a caller from another tenant
        gets 404 even with a valid ``run_id``."""
        org_id = resolve_org_id(claims)
        # Validate the upload exists in the caller's org — separate from the
        # eval batch's own org scoping so a wrong upload_id never falls through
        # to a valid batch.
        _resolve_upload(db, org_id, upload_id)
        try:
            rid = UUID(run_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid run_id"
            )
        detail = EvalService().get_run_detail(db, org_id=org_id, run_id=rid)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found"
            )
        return {
            "summary": _eval_run_summary_to_dict(detail["summary"]),
            "questions": detail["questions"],
        }

    # ── Manual eval question authoring ─────────────────────────────────
    # Users author their own Q&A pairs (typed in the UI) in addition to the
    # LLM-generated set. All four routes below are org-scoped and delegate to
    # ``EvalService``; scoring itself stays on the existing ``run_eval``
    # pipeline (retrieval + answer LLM + judge LLM), so manual questions flow
    # through the same drawer/summary UI as generated / benchmark-imported
    # ones — the ``generated_by_model`` field distinguishes them.

    def _eval_question_to_payload(row) -> dict:
        return {
            "id": str(row.id),
            "upload_id": str(row.upload_id),
            "knowledge_base_id": str(row.knowledge_base_id),
            "external_id": row.external_id,
            "question_ord": row.question_ord,
            "question": row.question,
            "expected_answer": row.expected_answer,
            "expected_source_snippet": row.expected_source_snippet,
            "category": row.category,
            "generated_by_model": row.generated_by_model,
            "generation_prompt_hash": row.generation_prompt_hash,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _eval_set_summary_to_dict(s) -> dict:
        return {
            "upload_id": str(s.upload_id),
            "organization_id": str(s.organization_id),
            "knowledge_base_id": str(s.knowledge_base_id) if s.knowledge_base_id else None,
            "question_count": s.question_count,
            "generated_by_model": s.generated_by_model,
            "generation_prompt_hash": s.generation_prompt_hash,
        }

    @router.get("/{upload_id}/evals/questions")
    def list_eval_questions(
        upload_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Return every eval question for one upload (ordered by
        ``question_ord``). Powers the manual-authoring modal so the user can
        see, edit, and delete existing questions alongside adding new ones."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        rows = EvalService().list_questions(db, upload_id=upload.id, org_id=org_id)
        return {"items": [_eval_question_to_payload(r) for r in rows]}

    @router.post(
        "/{upload_id}/evals/manual",
        status_code=status.HTTP_201_CREATED,
    )
    def add_manual_eval_questions(
        upload_id: str,
        body: AddManualQuestionsRequest = Body(...),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Append user-authored Q&A pairs to the upload's eval set. Never
        replaces existing rows — that's ``generate_eval`` / ``import_eval``.
        All validation (non-empty fields, external_id collisions, KB exists)
        lives in the service so CLI / worker callers get the same guarantees."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        payload = [q.model_dump(exclude_none=True) for q in body.questions]
        try:
            summary = EvalService().add_questions_manual(
                db,
                upload_id=upload.id,
                org_id=org_id,
                questions=payload,
            )
        except EvalNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except EvalGenerationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        return _eval_set_summary_to_dict(summary)

    @router.post(
        "/{upload_id}/evals/upload-csv",
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_eval_questions_csv(
        upload_id: str,
        file: UploadFile = File(...),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Append eval questions parsed from an uploaded CSV. Same semantics as
        ``POST /evals/manual`` — never wipes existing rows and stamps
        ``generated_by_model='manual'``. Row validation (non-empty fields,
        external_id collisions, KB exists) is enforced by the service so this
        route stays a thin adapter."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)
        try:
            raw = await file.read()
        finally:
            await file.close()
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
        try:
            summary = EvalService().add_questions_from_csv(
                db,
                upload_id=upload.id,
                org_id=org_id,
                csv_bytes=raw,
            )
        except EvalNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except EvalGenerationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        return _eval_set_summary_to_dict(summary)

    @router.put("/{upload_id}/evals/questions/{question_id}")
    def update_eval_question(
        upload_id: str,
        question_id: str,
        body: UpdateQuestionRequest = Body(...),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Patch one question row. Org-scoped so cross-tenant reads return
        404. ``upload_id`` is validated to belong to the caller's org (its
        presence in the URL isn't security by itself — the service also
        checks the row's ``organization_id``)."""
        org_id = resolve_org_id(claims)
        _resolve_upload(db, org_id, upload_id)
        try:
            qid = UUID(question_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid question_id",
            )
        patch = body.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        try:
            row = EvalService().update_question(
                db, question_id=qid, org_id=org_id, patch=patch,
            )
        except EvalNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except EvalGenerationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        return _eval_question_to_payload(row)

    @router.delete(
        "/{upload_id}/evals/questions/{question_id}",
        status_code=status.HTTP_200_OK,
    )
    def delete_eval_question(
        upload_id: str,
        question_id: str,
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Delete one question row. Cascades to its ``eval_results`` rows
        via the FK. Historic ``eval_results`` for OTHER questions in the same
        run are untouched — deletion is per-question, not per-batch."""
        org_id = resolve_org_id(claims)
        _resolve_upload(db, org_id, upload_id)
        try:
            qid = UUID(question_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid question_id",
            )
        try:
            EvalService().delete_question(db, question_id=qid, org_id=org_id)
        except EvalNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        return {"ok": True}

    @router.post(
        "/{upload_id}/evals/run",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def trigger_manual_eval_run(
        upload_id: str,
        body: TriggerEvalRunRequest = Body(default_factory=TriggerEvalRunRequest),
        claims=Depends(auth_dependency),
        db: Session = Depends(get_db),
    ):
        """Enqueue an eval run against the upload's questions.

        The actual scoring (retrieve → answer LLM → judge LLM) runs on the
        Procrastinate ``eval`` queue exactly like the auto-run after
        ingestion — this endpoint just defers the job so the HTTP request
        returns immediately instead of blocking for the 5-10 minutes an eval
        can take. Idempotency is intentionally NOT enforced: each click
        creates a fresh ``eval_results`` batch with a new ``run_id``, which
        is what the user asked for when they hit "Run".

        When ``ingestion_run_id`` is omitted, the currently-active ingestion
        run for the upload is used. Rejects with 400 when no run exists
        (upload never ingested) or when no active run is available (all runs
        failed / pending)."""
        org_id = resolve_org_id(claims)
        upload = _resolve_upload(db, org_id, upload_id)

        summary = EvalService().get_eval_by_upload(
            db, upload_id=upload.id, org_id=org_id
        )
        if summary is None or summary.question_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No eval questions exist for this upload — add or generate questions first.",
            )

        if body.ingestion_run_id is not None:
            run = (
                db.query(IngestionPipelineRun)
                .filter(
                    IngestionPipelineRun.id == body.ingestion_run_id,
                    IngestionPipelineRun.upload_id == upload.id,
                    IngestionPipelineRun.organization_id == org_id,
                )
                .first()
            )
            if run is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ingestion run not found for this upload",
                )
        else:
            run = (
                db.query(IngestionPipelineRun)
                .filter(
                    IngestionPipelineRun.upload_id == upload.id,
                    IngestionPipelineRun.organization_id == org_id,
                    IngestionPipelineRun.is_active.is_(True),
                )
                .first()
            )
            if run is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active ingestion run for this upload — ingest the document first.",
                )
        if run.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot run eval against a run with status={run.status!r}; only 'ready' is allowed",
            )

        try:
            job_id = await enqueue_eval_for_ingestion_run(run.id, triggered_by="manual")
        except Exception as exc:
            # Full traceback is captured by logger.exception; the frontend
            # gets a generic message — never leak the raw exception str
            # (per backend coding standards §"Never expose raw exceptions").
            logger.exception(
                "[eval] manual run enqueue failed upload={} run={}",
                upload.id, run.id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue eval run. Please try again later.",
            ) from exc

        logger.info(
            "[eval] manual run enqueued upload={} ingestion_run={} job_id={} user={}",
            upload.id, run.id, job_id, claims.user_id,
        )
        return {
            "upload_id": str(upload.id),
            "ingestion_run_id": str(run.id),
            "job_id": job_id,
            "status": "queued",
        }

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
        try:
            akb = IngestionRunService.set_agent_kb_active_run(
                db,
                org_id=org_id,
                agent_id=aid,
                knowledge_base_id=kid,
                run_id=body.active_ingestion_pipeline_run_id,
            )
        except (
            AgentHasNoPublishedConfigError,
            AgentKnowledgeBaseNotFoundError,
            IngestionRunNotFoundError,
            IngestionRunKbMismatchError,
            IngestionRunNotReadyError,
        ) as exc:
            _raise_http_for_ingestion_error(exc)
        return akb.to_dict()

    return router
