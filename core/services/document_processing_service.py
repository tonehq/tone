from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.models.upload import Upload
from core.services.document_tool_service import get_openai_api_key_for_agent
from core.services.r2_storage_service import R2StorageService
from core.services.rag.embedders import OpenAIEmbedder
from core.services.rag.pipeline import RAGPipeline
from core.services.rag.vector_stores.pgvector_store import PgVectorStore


class DocumentProcessingService:

    def process_document(self, upload_id: UUID, org_id: UUID, file_bytes: bytes, delete_existing: bool = False):
        try:
            with get_db_context() as db:
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if not upload:
                    logger.error("Upload {} not found, skipping processing", upload_id)
                    return
                file_type = upload.file_type
                upload.status = "processing"
                if delete_existing:
                    db.query(KnowledgeBaseChunk).filter(
                        KnowledgeBaseChunk.upload_id == upload_id
                    ).delete(synchronize_session=False)
                db.commit()

            api_key = get_openai_api_key_for_agent(org_id)
            if not api_key:
                raise ValueError("No OpenAI API key configured for embedding")

            def _on_batch(batch_index: int, start_page: int, end_page: int, count: int, elapsed: float) -> None:
                logger.info(
                    "[ingestion] pages {}-{}: {} chunks stored in {:.1f}s",
                    start_page, end_page, count, elapsed,
                )

            pipeline = RAGPipeline(
                embedder=OpenAIEmbedder(api_key),
                store=PgVectorStore(),
            )
            num_chunks = pipeline.ingest_file_paged(
                file_bytes,
                file_type,
                page_batch=50,
                metadata={"organization_id": org_id, "upload_id": upload_id},
                on_batch=_on_batch,
            )
            if not num_chunks:
                raise ValueError("Text extraction produced no chunks")

            with get_db_context() as db:
                db.query(Upload).filter(Upload.id == upload_id).update({"status": "ready"})
                db.commit()
            logger.info("Upload {} processed: {} chunks stored", upload_id, num_chunks)

        except Exception as e:
            logger.error("Upload {} processing failed: {}", upload_id, e)
            try:
                with get_db_context() as db:
                    upload = db.query(Upload).filter(Upload.id == upload_id).first()
                    if upload:
                        upload.status = "failed"
                        upload.meta_data = {**(upload.meta_data or {}), "error": str(e)}
                        db.commit()
            except Exception as meta_err:
                logger.error("Failed to update error metadata: {}", meta_err)

    def process_upload(self, upload_id: UUID, org_id: UUID, delete_existing: bool = False):
        with get_db_context() as db:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if not upload or not upload.file_path:
                logger.error("Upload {} not found or has no file_path", upload_id)
                return
            file_path = upload.file_path

        file_bytes = R2StorageService().download_file(file_path)
        self.process_document(upload_id, org_id, file_bytes, delete_existing=delete_existing)

    def reprocess_upload(self, upload_id: UUID, org_id: UUID):
        self.process_upload(upload_id, org_id, delete_existing=True)
