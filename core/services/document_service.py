from sqlalchemy.orm import Session
from typing import Optional, Union, List, Dict, Any
from uuid import UUID
import time
import uuid as uuid_lib

from fastapi import HTTPException, status
from loguru import logger

from core.services.base import BaseService
from core.models.document import Document, DocumentChunk
from core.models.upload import Upload


class DocumentService(BaseService):

    def upload_and_create_document(
        self,
        agent_id: int,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
    ) -> Document:
        """Upload file to R2, create an Upload record, then create a Document record."""
        from core.services.r2_storage_service import R2StorageService

        # Upload to R2
        r2 = R2StorageService()
        r2_object_key = f"documents/{agent_id}/{uuid_lib.uuid4()}/{file_name}"
        r2.upload_file(file_bytes, r2_object_key, content_type=content_type)
        logger.info("Document uploaded to R2: key={}", r2_object_key)

        # Create Upload record (same pattern as audio uploads in CallLogService)
        now = int(time.time())
        upload = Upload(
            r2_object_key=r2_object_key,
            agent_id=agent_id,
            organization_id=self.org_id,
            file_name=file_name,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
        )
        self.db.add(upload)
        self.db.flush()

        # Create Document record linked to the upload
        doc = Document(
            uuid=uuid_lib.uuid4(),
            upload_id=upload.id,
            agent_id=agent_id,
            status='processing',
            organization_id=self.org_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        logger.info("Document record created: id={} upload_id={}", doc.id, upload.id)
        return doc

    def get_documents_by_agent(self, agent_id: int) -> List[Dict[str, Any]]:
        """List all documents for a given agent."""
        docs = (
            self.query(Document)
            .filter(Document.agent_id == agent_id)
            .order_by(Document.created_at.desc())
            .all()
        )
        return [self._document_response(doc) for doc in docs]

    def get_document_by_id(self, document_id: int) -> Document:
        doc = self.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        return doc

    def get_document_by_uuid(self, document_uuid: UUID) -> Document:
        doc = self.query(Document).filter(Document.uuid == document_uuid).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        return doc

    def delete_document(self, document_id: int) -> Dict[str, str]:
        """Delete a document, its chunks (cascade), and the R2 file."""
        doc = self.get_document_by_id(document_id)

        # Delete the file from R2 via the linked upload
        upload = self.db.query(Upload).filter(Upload.id == doc.upload_id).first()
        if upload:
            try:
                from core.services.r2_storage_service import R2StorageService
                R2StorageService().delete_file(upload.r2_object_key)
                logger.info("Deleted document file from R2: key={}", upload.r2_object_key)
            except Exception as e:
                logger.error("Failed to delete document file from R2: {}", e)
            self.db.delete(upload)

        self.db.delete(doc)
        self.db.commit()
        return {"message": "Document deleted successfully"}

    def update_document_status(self, document_id: int, doc_status: str, content_text: str = None) -> Document:
        """Update status (and optionally full text) after processing."""
        doc = self.get_document_by_id(document_id)
        doc.status = doc_status
        if content_text is not None:
            doc.content_text = content_text
        doc.updated_at = int(time.time())
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def create_chunks(self, document_id: int, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Bulk-create chunks for a document. Each dict needs: chunk_index, chunk_text."""
        now = int(time.time())
        chunk_objects = []
        for chunk in chunks:
            obj = DocumentChunk(
                uuid=uuid_lib.uuid4(),
                document_id=document_id,
                chunk_index=chunk["chunk_index"],
                chunk_text=chunk["chunk_text"],
                organization_id=self.org_id,
                created_at=now,
                updated_at=now,
            )
            chunk_objects.append(obj)
        self.db.add_all(chunk_objects)
        self.db.commit()
        return chunk_objects

    def get_chunks_by_document(self, document_id: int) -> List[DocumentChunk]:
        return (
            self.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    def _document_response(self, doc: Document) -> Dict[str, Any]:
        upload = self.db.query(Upload).filter(Upload.id == doc.upload_id).first()
        return {
            "id": doc.id,
            "uuid": str(doc.uuid),
            "upload_id": doc.upload_id,
            "agent_id": doc.agent_id,
            "file_name": upload.file_name if upload else None,
            "content_type": upload.content_type if upload else None,
            "file_size_bytes": upload.file_size_bytes if upload else None,
            "status": doc.status,
            "meta_data": doc.meta_data,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }
