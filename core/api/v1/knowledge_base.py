from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.upload import Upload
from core.services.crud import list_records
from core.services.document_processing_service import DocumentProcessingService
from core.services.r2_storage_service import R2StorageService
from shared.config import settings

router = APIRouter()


def _resolve_org_id(claims: JWTClaims) -> UUID:
    return UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)


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


@router.post("/list")
def list_documents(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = _resolve_org_id(claims)

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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id")
        upload_ids_q = (
            db.query(AgentKnowledgeBase.upload_id)
            .filter(AgentKnowledgeBase.agent_id == agent_uuid, AgentKnowledgeBase.organization_id == org_id)
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
    return {
        "items": [_upload_to_payload(i, r2) for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent_id: str | None = Form(None),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Upload a knowledge-base document.

    ``agent_id`` is optional: when omitted (e.g. uploading from the agent
    create form before the agent has been saved), the upload row is created
    standalone and the caller is expected to attach it on agent save via
    ``upload_ids`` on the create_agent payload.
    """
    org_id = _resolve_org_id(claims)
    agent_uuid: UUID | None = None
    agent_config = None
    if agent_id:
        try:
            agent_uuid = UUID(agent_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id")

        agent = db.query(Agent).filter(Agent.id == agent_uuid, Agent.organization_id == org_id).first()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

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

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    file_name = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"
    user_id = UUID(claims.user_id) if claims.user_id else None

    object_key = f"knowledge-base/{org_id}/{uuid4()}/{file_name}"
    r2 = R2StorageService()
    r2.upload_file(file_bytes, object_key, content_type=content_type)

    try:
        upload = Upload(
            organization_id=org_id,
            container_name=settings.R2_BUCKET_NAME,
            file_path=object_key,
            file_name=file_name,
            file_type=content_type,
            size_bytes=len(file_bytes),
            purpose="kb_document",
            status="processing",
            meta_data={},
            created_by_user_id=user_id,
            is_active=True,
        )
        db.add(upload)
        db.flush()

        if agent_uuid is not None and agent_config is not None:
            db.add(
                AgentKnowledgeBase(
                    organization_id=org_id,
                    agent_id=agent_uuid,
                    upload_id=upload.id,
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

    background_tasks.add_task(
        DocumentProcessingService().process_upload, upload.id, org_id
    )

    return _upload_to_payload(upload)


@router.patch("/{upload_id}")
def rename_document(
    upload_id: str,
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = _resolve_org_id(claims)
    try:
        uid = UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

    new_name = (body.get("file_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_name is required")
    if len(new_name) > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file_name too long (max 512)"
        )

    upload = (
        db.query(Upload)
        .filter(Upload.id == uid, Upload.organization_id == org_id)
        .first()
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
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = _resolve_org_id(claims)
    try:
        uid = UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

    upload = (
        db.query(Upload)
        .filter(Upload.id == uid, Upload.organization_id == org_id)
        .first()
    )
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    new_name = (file_name or "").strip() or file.filename or upload.file_name
    if len(new_name) > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file_name too long (max 512)"
        )
    content_type = file.content_type or "application/octet-stream"

    new_object_key = f"knowledge-base/{org_id}/{uuid4()}/{new_name}"
    R2StorageService().upload_file(file_bytes, new_object_key, content_type=content_type)

    old_path = upload.file_path

    upload.file_path = new_object_key
    upload.file_name = new_name
    upload.file_type = content_type
    upload.size_bytes = len(file_bytes)
    upload.status = "processing"
    db.commit()
    db.refresh(upload)

    # Best-effort delete of the old R2 blob
    if old_path and old_path != new_object_key:
        try:
            R2StorageService().delete_file(old_path)
        except Exception:
            pass

    background_tasks.add_task(
        DocumentProcessingService().reprocess_upload, upload.id, org_id
    )

    return _upload_to_payload(upload)


@router.delete("/{upload_id}", status_code=status.HTTP_200_OK)
def delete_document(
    upload_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = _resolve_org_id(claims)
    try:
        uid = UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_id")

    upload = (
        db.query(Upload)
        .filter(Upload.id == uid, Upload.organization_id == org_id)
        .first()
    )
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    file_path = upload.file_path

    # AgentKnowledgeBase rows cascade-delete via upload FK
    db.delete(upload)
    db.commit()

    if file_path:
        try:
            R2StorageService().delete_file(file_path)
        except Exception:
            pass

    return {"ok": True}
