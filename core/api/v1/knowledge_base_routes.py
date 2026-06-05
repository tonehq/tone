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

from core.database.session import get_db
from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.crud import list_records
from core.services.document_processing_service import DocumentProcessingService
from core.services.ingestion_queue import enqueue_reprocess, enqueue_upload
from core.services.r2_storage_service import R2StorageService
from shared.config import settings


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
        sort_by = body.get("sort_by")
        agent_id = body.get("agent_id")
        status_filter = body.get("status")

        filters = [Upload.purpose == "kb_document"]
        if search:
            filters.append(Upload.file_name.ilike(f"%{search}%"))
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
            filters.append(Upload.id.in_(upload_ids_q))
        if status_filter:
            filters.append(Upload.status == status_filter)

        allowed_sort_fields = {"file_name", "size_bytes", "created_at", "updated_at", "status"}
        order_by = Upload.updated_at.desc()
        if sort_by:
            desc = sort_by.startswith("-")
            field_name = sort_by.lstrip("-")
            if field_name in allowed_sort_fields:
                col = getattr(Upload, field_name)
                order_by = col.desc() if desc else col.asc()

        items, total = list_records(db, Upload, org_id, page, page_size, filters, order_by)
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

            # Resolve the latest agent_config up-front so we fail fast (before
            # touching R2) when the agent has no config yet — otherwise raising
            # 409 after the blob is written would orphan the R2 object.
            from core.models.agent_config import AgentConfig

            agent_config = (
                db.query(AgentConfig)
                .filter(AgentConfig.agent_id == agent_uuid, AgentConfig.deleted_at.is_(None))
                .order_by(AgentConfig.version.desc())
                .first()
            )
            if not agent_config:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Agent has no configuration yet. Save the agent before uploading knowledge base documents.",
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

        await enqueue_upload(upload.id, org_id)

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

        await enqueue_reprocess(upload.id, org_id)

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

        await enqueue_reprocess(upload.id, org_id)

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

    return router
