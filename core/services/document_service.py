from typing import List, Dict, Any
from uuid import UUID
import time
import uuid as uuid_lib
import traceback

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import Null

from core.services.base import BaseService
from core.models.document import Document, DocumentChunk
from core.models.upload import Upload
from core.models.service_provider import ServiceProvider
from core.models.api_key import ApiKey
from core.utils.encryption import decrypt


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

        # Process the document: extract text → chunk → embed → store
        self._process_document(doc, file_bytes, content_type)

        return doc

    def _process_document(self, doc: Document, file_bytes: bytes, content_type: str):
        """Extract text, chunk it, generate embeddings, and store chunks."""
        try:
            from core.services.text_extractor import TextExtractor
            from core.services.chunking_service import ChunkingService
            from core.services.embedding_service import EmbeddingService

            # Step 1: Extract plain text from the file
            extractor = TextExtractor()
            plain_text = extractor.extract(file_bytes, content_type)
            if not plain_text.strip():
                self._update_status(doc, "failed")
                logger.warning("Document {} has no extractable text", doc.id)
                return

            # Step 2: Split text into chunks
            chunker = ChunkingService()
            chunks = chunker.split(plain_text)
            if not chunks:
                self._update_status(doc, "failed")
                logger.warning("Document {} produced no chunks", doc.id)
                return

            # Step 3: Get OpenAI API key from DB and generate embeddings
            api_key = self._get_openai_api_key()
            embedder = EmbeddingService(api_key)
            chunk_texts = [c["chunk_text"] for c in chunks]
            embeddings = embedder.embed_texts(chunk_texts)

            # Step 4: Store chunks with embeddings
            now = int(time.time())
            chunk_objects = []
            for chunk, embedding in zip(chunks, embeddings):
                obj = DocumentChunk(
                    uuid=uuid_lib.uuid4(),
                    document_id=doc.id,
                    chunk_index=chunk["chunk_index"],
                    chunk_text=chunk["chunk_text"],
                    embedding=embedding,
                    organization_id=self.org_id,
                    created_at=now,
                    updated_at=now,
                )
                chunk_objects.append(obj)
            self.db.add_all(chunk_objects)

            # Step 5: Update document status to ready
            doc.status = "ready"
            doc.content_text = plain_text
            doc.updated_at = now
            self.db.commit()
            self.db.refresh(doc)

            logger.info(
                "Document {} processed: {} chunks with embeddings",
                doc.id, len(chunk_objects),
            )

        except Exception as e:
            print(traceback.format_exc())
            logger.error("Failed to process document {}: {}", doc.id, e)
            self.db.rollback()
            # Update status to failed
            doc.status = "failed"
            doc.meta_data = {"error": str(e)}
            doc.updated_at = int(time.time())
            self.db.add(doc)
            self.db.commit()

    def _update_status(self, doc: Document, new_status: str):
        doc.status = new_status
        doc.updated_at = int(time.time())
        self.db.commit()

    def _get_openai_api_key(self) -> str:
        """Fetch the OpenAI API key from DB.

        Tries new path first (Account with model_provider_menu → ApiKey.account_id),
        then falls back to old path (ServiceProvider → ApiKey.service_provider_id).
        """
        # New path: Account linked to ModelProviderMenu
        from core.models.account import Account
        from core.models.model_provider_menu import ModelProviderMenu

        mpm = (
            self.db.query(ModelProviderMenu)
            .filter(ModelProviderMenu.name == "openai", ModelProviderMenu.provider_type == "llm")
            .first()
        )
        if mpm:
            acct = (
                self.db.query(Account)
                .filter(Account.model_provider_menu_id == mpm.id, Account.status == "active")
                .first()
            )
            if acct:
                api_key_record = (
                    self.query(ApiKey)
                    .filter(ApiKey.account_id == acct.id, ApiKey.status == "active")
                    .first()
                )
                if api_key_record and api_key_record.api_key_encrypted:
                    return decrypt(api_key_record.api_key_encrypted)

        # Old path: ServiceProvider
        provider = (
            self.db.query(ServiceProvider)
            .filter(ServiceProvider.name == "openai", ServiceProvider.provider_type == "llm")
            .first()
        )
        if provider:
            api_key_record = (
                self.query(ApiKey)
                .filter(ApiKey.service_provider_id == provider.id, ApiKey.status == "active")
                .first()
            )
            if api_key_record and api_key_record.api_key_encrypted:
                return decrypt(api_key_record.api_key_encrypted)

        raise ValueError("No active OpenAI API key found for embedding")

    def get_documents_by_agent(
        self,
        agent_id: int | None = None,
        name: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """List documents with optional filters, sorting, and pagination."""
        from core.models.agent import Agent
        from sqlalchemy import asc, desc, or_

        query = self.query(Document).filter(Document.organization_id == self.org_id)
        agent_joined = False
        upload_joined = False

        if agent_id is not None:
            query = query.filter(Document.agent_id == agent_id)

        if name is not None:
            query = query.join(Agent, Document.agent_id == Agent.id)
            agent_joined = True
            query = query.join(Upload, Document.upload_id == Upload.id)
            upload_joined = True
            query = query.filter(
                or_(
                    Agent.name.ilike(f"%{name}%"),
                    Upload.file_name.ilike(f"%{name}%"),
                )
            )

        # Get total count before pagination
        total = query.count()

        # Determine sort column
        sort_column_map = {
            "created_at": Document.created_at,
            "updated_at": Document.updated_at,
        }
        if sort_by == "name":
            if not upload_joined:
                query = query.join(Upload, Document.upload_id == Upload.id)
            sort_column = Upload.file_name
        else:
            sort_column = sort_column_map[sort_by]

        order_func = asc if sort_order == "asc" else desc
        offset = (page - 1) * page_size
        docs = query.order_by(order_func(sort_column)).offset(offset).limit(page_size).all()

        total_pages = (total + page_size - 1) // page_size

        return {
            "data": [self._document_response(doc) for doc in docs],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        }

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
        url = None
        if upload and upload.r2_object_key:
            try:
                from core.services.r2_storage_service import R2StorageService
                url = R2StorageService().generate_presigned_url(upload.r2_object_key)
            except Exception as e:
                logger.error("Failed to generate presigned URL for document {}: {}", doc.id, e)
        return {
            "id": doc.id,
            "uuid": str(doc.uuid),
            "upload_id": doc.upload_id,
            "agent_id": doc.agent_id,
            "file_name": upload.file_name if upload else None,
            "content_type": upload.content_type if upload else None,
            "file_size_bytes": upload.file_size_bytes if upload else None,
            "url": url,
            "status": doc.status,
            "meta_data": doc.meta_data,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }

    def get_all_documents(self):
        documents = self.db.query(Document).filter(Document.organization_id == self.org_id).all()
        if documents:
            return documents
        else:
            return "No documents found for this organisation"    

