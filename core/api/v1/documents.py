from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from core.database.session import get_db
from core.services.document_service import DocumentService
from core.middleware.auth import require_org_member, JWTClaims
from shared.config import settings

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


@router.get("/get_documents", response_model=List[Dict[str, Any]])
def get_documents(
    agent_id: int = Query(..., description="The agent ID to fetch documents for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Return all documents for a given agent."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return DocumentService(db, org_id=org_id).get_documents_by_agent(agent_id)


@router.post("/upload_document", status_code=status.HTTP_201_CREATED)
def upload_document(
    agent_id: int = Form(...),
    file: UploadFile = File(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Upload a document file (PDF, DOCX, TXT), store in R2, create Upload + Document records."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT",
        )

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    svc = DocumentService(db, org_id=org_id)
    doc = svc.upload_and_create_document(
        agent_id=agent_id,
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=file.content_type,
    )
    return svc._document_response(doc)


@router.delete("/delete_document", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int = Query(..., description="The document ID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Delete a document, its chunks, and the file from R2."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return DocumentService(db, org_id=org_id).delete_document(document_id)
