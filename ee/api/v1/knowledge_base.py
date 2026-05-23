from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from core.database.session import get_db
from core.models.agent import Agent
from core.models.document import Document
from core.models.upload import Upload
from core.services.crud import list_records
from core.services.r2_storage_service import R2StorageService
from ee.middleware.auth import EEJWTClaims, require_ee_org_member
from shared.config import settings

router = APIRouter()


def _signed_url(file_path: str | None, r2: R2StorageService | None = None) -> str | None:
    if not file_path:
        return None
    try:
        return (r2 or R2StorageService()).generate_presigned_url(file_path)
    except Exception:
        return None


def _doc_to_payload(doc: Document, r2: R2StorageService | None = None) -> dict:
    payload = doc.to_dict()
    payload["url"] = _signed_url(doc.upload.file_path if doc.upload else None, r2)
    return payload


@router.post("/list")
def list_documents(
    body: dict = Body(default={}),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)

    page = max(int(body.get("page") or 1), 1)
    page_size = min(max(int(body.get("page_size") or 20), 1), 100)
    search = body.get("search")
    sort_by = body.get("sort_by")
    agent_id = body.get("agent_id")
    status_filter = body.get("status")

    filters = []
    if search:
        filters.append(Document.file_name.ilike(f"%{search}%"))
    if agent_id:
        try:
            filters.append(Document.agent_id == UUID(str(agent_id)))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id")
    if status_filter:
        filters.append(Document.status == status_filter)

    allowed_sort_fields = {"file_name", "file_size_bytes", "created_at", "updated_at", "status"}
    order_by = Document.updated_at.desc()
    if sort_by:
        desc = sort_by.startswith("-")
        field_name = sort_by.lstrip("-")
        if field_name in allowed_sort_fields:
            col = getattr(Document, field_name)
            order_by = col.desc() if desc else col.asc()

    items, total = list_records(
        db,
        Document,
        org_id,
        page,
        page_size,
        filters,
        order_by,
        options=[joinedload(Document.upload)],
    )
    r2 = R2StorageService()
    return {
        "items": [_doc_to_payload(i, r2) for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    agent_id: str = Form(...),
    file: UploadFile = File(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent_id")

    agent = db.query(Agent).filter(Agent.id == agent_uuid, Agent.organization_id == org_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    file_name = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"
    user_id = UUID(claims.user_id) if claims.user_id else None

    object_key = f"knowledge-base/{org_id}/{uuid4()}/{file_name}"
    R2StorageService().upload_file(file_bytes, object_key, content_type=content_type)

    upload = Upload(
        organization_id=org_id,
        container_name=settings.R2_BUCKET_NAME,
        file_path=object_key,
        file_type=content_type,
        size_bytes=len(file_bytes),
        purpose="kb_document",
        created_by_user_id=user_id,
        is_active=True,
    )
    db.add(upload)
    db.flush()

    doc = Document(
        organization_id=org_id,
        upload_id=upload.id,
        agent_id=agent_uuid,
        file_name=file_name,
        content_type=content_type,
        file_size_bytes=len(file_bytes),
        status="ready",
        meta_data={},
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_to_payload(doc)


@router.patch("/{document_id}")
def rename_document(
    document_id: str,
    body: dict = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document_id")

    new_name = (body.get("file_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_name is required")
    if len(new_name) > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file_name too long (max 512)"
        )

    doc = (
        db.query(Document)
        .filter(Document.id == doc_uuid, Document.organization_id == org_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.file_name = new_name
    db.commit()
    db.refresh(doc)
    return _doc_to_payload(doc)


@router.patch("/{document_id}/file")
async def replace_document_file(
    document_id: str,
    file: UploadFile = File(...),
    file_name: str | None = Form(None),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document_id")

    doc = (
        db.query(Document)
        .filter(Document.id == doc_uuid, Document.organization_id == org_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    new_name = (file_name or "").strip() or file.filename or doc.file_name
    if len(new_name) > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="file_name too long (max 512)"
        )
    content_type = file.content_type or "application/octet-stream"

    new_object_key = f"knowledge-base/{org_id}/{uuid4()}/{new_name}"
    R2StorageService().upload_file(file_bytes, new_object_key, content_type=content_type)

    upload = doc.upload
    old_path = upload.file_path if upload else None

    if upload is None:
        upload = Upload(
            organization_id=org_id,
            container_name=settings.R2_BUCKET_NAME,
            file_path=new_object_key,
            file_type=content_type,
            size_bytes=len(file_bytes),
            purpose="kb_document",
            created_by_user_id=UUID(claims.user_id) if claims.user_id else None,
            is_active=True,
        )
        db.add(upload)
        db.flush()
        doc.upload_id = upload.id
    else:
        upload.file_path = new_object_key
        upload.file_type = content_type
        upload.size_bytes = len(file_bytes)

    doc.file_name = new_name
    doc.content_type = content_type
    doc.file_size_bytes = len(file_bytes)
    doc.status = "ready"
    db.commit()
    db.refresh(doc)

    if old_path and old_path != new_object_key:
        try:
            R2StorageService().delete_file(old_path)
        except Exception:
            pass

    return _doc_to_payload(doc)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(claims.org_id)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document_id")

    doc = (
        db.query(Document)
        .filter(Document.id == doc_uuid, Document.organization_id == org_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    upload = doc.upload
    file_path = upload.file_path if upload else None

    db.delete(doc)
    if upload:
        db.delete(upload)
    db.commit()

    if file_path:
        try:
            R2StorageService().delete_file(file_path)
        except Exception:
            pass

    return {"ok": True}
