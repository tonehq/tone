from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database.session import get_db
from core.services.document_service import DocumentService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


class GetDocumentsRequest(BaseModel):
    agent_id: Optional[int] = None
    name: Optional[str] = Field(None, description="Filter by agent name and/or file name (partial match, case-insensitive)")
    sort: Optional[str] = Field("-created_at", description="Sort field. Prefix with - for desc. Allowed: created_at, updated_at, name")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
}


@router.post("/get_documents")
def get_documents(
    body: GetDocumentsRequest,
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Return documents with filtering, sorting, and pagination."""
    sort = body.sort or "-created_at"
    if sort.startswith("-"):
        sort_by = sort[1:]
        sort_order = "desc"
    else:
        sort_by = sort
        sort_order = "asc"

    if sort_by not in {"created_at", "updated_at", "name"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field: {sort_by}. Allowed: created_at, updated_at, name",
        )

    return DocumentService(db, org_id=UUID(claims.org_id)).get_documents_by_agent(
        agent_id=body.agent_id,
        name=body.name,
        sort_by=sort_by,
        sort_order=sort_order,
        page=body.page,
        page_size=body.page_size,
    )


@router.post("/upload_document", status_code=status.HTTP_201_CREATED)
def upload_document(
    agent_id: int = Form(...),
    files: List[UploadFile] = File(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Upload one or more document files (PDF, DOCX, TXT, CSV), store in R2, create Upload + Document records."""
    svc = DocumentService(db, org_id=UUID(claims.org_id))
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Delete one or more documents, their chunks, and the files from R2."""
    svc = DocumentService(db, org_id=UUID(claims.org_id))
    for document_id in document_ids:
        svc.delete_document(document_id)
    return {"message": f"{len(document_ids)} document(s) deleted successfully"}
