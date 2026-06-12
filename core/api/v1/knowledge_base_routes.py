"""Shared knowledge-base route implementation.

Both the Core (``core/api/v1/knowledge_base.py``) and Enterprise
(``ee/api/v1/knowledge_base.py``) editions expose an identical knowledge-base
API. The only differences are the auth dependency and how the organization id
is derived from the resolved claims. Rather than duplicate every handler, the
full router is built here and parameterized with those two concerns, so there
is a single source of truth for the route logic.
"""

from typing import Any, Callable
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
from sqlalchemy.orm import Session

from core.api.v1.faceted_schemas import FacetsRequest
from core.database.session import get_db
from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.document_processing_service import DocumentProcessingService
from core.services.ingestion_queue import enqueue_reprocess, enqueue_upload
from core.services.r2_storage_service import R2StorageService
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
    except Exception:
        return None


def _upload_to_payload(upload: Upload, r2: R2StorageService | None = None) -> dict:
    payload = upload.to_dict()
    payload["url"] = _signed_url(upload.file_path, r2)
    return payload


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

            # Resolve the agent's PUBLISHED config up-front so we fail fast
            # (before touching R2) when the agent has no live version yet —
            # otherwise raising 409 after the blob is written would orphan
            # the R2 object. The upload attaches to the published version so
            # it's immediately available to the live agent; draft versions
            # get their own copy via cloning on the next save.
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

        object_key = f"knowledge-base/{org_id}/{uuid4()}/{file_name}"
        r2 = R2StorageService()
        r2.upload_fileobj(file.file, object_key, content_type=content_type)

        try:
            upload = Upload(
                organization_id=org_id,
                container_name=settings.R2_BUCKET_NAME,
                file_path=object_key,
                file_name=file_name,
                file_type=content_type,
                size_bytes=size_bytes,
                purpose="kb_document",
                status="processing",
                meta_data={},
                created_by_user_id=user_id,
                is_active=True,
            )
            db.add(upload)
            db.flush()

            knowledge_base = KnowledgeBase(
                organization_id=org_id,
                name=file_name,
                status="processing",
                upload_id=upload.id,
                meta_data={},
            )
            db.add(knowledge_base)
            db.flush()

            if agent_uuid is not None and agent_config is not None:
                db.add(
                    AgentKnowledgeBase(
                        organization_id=org_id,
                        agent_id=agent_uuid,
                        knowledge_base_id=knowledge_base.id,
                        agent_config_id=agent_config.id,
                    )
                )

            db.commit()
            db.refresh(upload)
        except Exception:
            # DB write failed after the blob landed in R2 — clean up so we don't
            # leak orphan objects. R2 delete is best-effort.
            db.rollback()
            try:
                r2.delete_file(object_key)
            except Exception:
                pass
            raise

        job_id = await enqueue_upload(upload.id, org_id)
        knowledge_base.procrastinate_job_id = job_id
        db.commit()

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
            except Exception:
                pass

        job_id = await enqueue_reprocess(upload.id, org_id)
        db.query(KnowledgeBase).filter(
            KnowledgeBase.upload_id == upload.id, KnowledgeBase.organization_id == org_id
        ).update({KnowledgeBase.procrastinate_job_id: job_id}, synchronize_session=False)
        db.commit()

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

        job_id = await enqueue_reprocess(upload.id, org_id)
        db.query(KnowledgeBase).filter(
            KnowledgeBase.upload_id == upload.id, KnowledgeBase.organization_id == org_id
        ).update({KnowledgeBase.procrastinate_job_id: job_id}, synchronize_session=False)
        db.commit()

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
            except Exception:
                pass

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

    return router
