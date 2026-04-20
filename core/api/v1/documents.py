from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from core.database.session import get_db
from core.services.document_service import DocumentService
from core.middleware.auth import require_org_member, JWTClaims
from shared.config import settings

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
}


@router.get("/get_documents", response_model=List[Dict[str, Any]])
def get_documents(
    agent_id: int = None,
    name: Optional[str] = Query(None, description="Filter by agent name and/or file name (partial match, case-insensitive)"),
    sort: Optional[str] = Query("-created_at", description="Sort field. Prefix with - for desc. Allowed: created_at, updated_at, file_name, status"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return all documents, optionally filtered and sorted."""
    # Parse sort param: -field = desc, field = asc
    if sort.startswith("-"):
        sort_by = sort[1:]
        sort_order = "desc"
    else:
        sort_by = sort
        sort_order = "asc"

    if sort_by not in {"created_at", "updated_at", "file_name", "status"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field: {sort_by}. Allowed: created_at, updated_at, file_name, status",
        )

    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return DocumentService(db, org_id=org_id).get_documents_by_agent(
        agent_id=agent_id,
        name=name,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/upload_document", status_code=status.HTTP_201_CREATED)
def upload_document(
    agent_id: int = Form(...),
    files: List[UploadFile] = File(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Upload one or more document files (PDF, DOCX, TXT, CSV), store in R2, create Upload + Document records."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    svc = DocumentService(db, org_id=org_id)
    results = []

    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type} for file '{file.filename}'. Allowed: PDF, DOCX, TXT, CSV",
            )

        file_bytes = file.file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{file.filename}' is empty",
            )

        doc = svc.upload_and_create_document(
            agent_id=agent_id,
            file_bytes=file_bytes,
            file_name=file.filename,
            content_type=file.content_type,
        )
        results.append(svc._document_response(doc))

    return results


@router.delete("/delete_document", status_code=status.HTTP_200_OK)
def delete_document(
    document_ids: List[int] = Query(..., description="One or more document IDs to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Delete one or more documents, their chunks, and the files from R2."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    svc = DocumentService(db, org_id=org_id)
    for document_id in document_ids:
        svc.delete_document(document_id)
    return {"message": f"{len(document_ids)} document(s) deleted successfully"}

