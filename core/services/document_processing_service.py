"""Background pipeline: Extract text -> Chunk -> Embed -> Store in knowledge_base_chunks."""

from uuid import UUID

from loguru import logger


class DocumentProcessingService:

    def process_upload(self, upload_id: UUID, org_id: UUID, delete_existing: bool = False):
        """Full pipeline: download file, extract text, chunk, embed, store."""
        from core.database.session import get_db_context
        from core.models.upload import Upload
        from core.models.knowledge_base_chunk import KnowledgeBaseChunk
        from core.services.r2_storage_service import R2StorageService
        from core.services.text_extraction_service import TextExtractionService
        from core.services.chunking_service import ChunkingService
        from core.services.embedding_service import EmbeddingService
        from core.services.document_tool_service import get_openai_api_key_for_agent

        with get_db_context() as db:
            try:
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if not upload:
                    logger.error("Upload {} not found, skipping processing", upload_id)
                    return

                upload.status = "processing"
                if delete_existing:
                    db.query(KnowledgeBaseChunk).filter(
                        KnowledgeBaseChunk.upload_id == upload_id
                    ).delete(synchronize_session=False)
                db.commit()

                # 1. Download file from R2
                if not upload.file_path:
                    raise ValueError("Upload has no file_path")
                file_bytes = R2StorageService().download_file(upload.file_path)

                # 2. Extract text
                text = TextExtractionService().extract(file_bytes, upload.file_type)
                if not text.strip():
                    raise ValueError("No text could be extracted from the file")

                # 3. Chunk
                chunks = ChunkingService().split(text)
                if not chunks:
                    raise ValueError("Text splitting produced no chunks")

                # 4. Get OpenAI key for embeddings
                api_key = get_openai_api_key_for_agent(org_id)
                if not api_key:
                    raise ValueError("No OpenAI API key configured for embedding")

                # 5. Embed in batches of 100
                embedder = EmbeddingService(api_key)
                chunk_texts = [c["chunk_text"] for c in chunks]
                all_embeddings = []
                for i in range(0, len(chunk_texts), 100):
                    batch = chunk_texts[i : i + 100]
                    all_embeddings.extend(embedder.embed_texts(batch))

                # 6. Bulk insert chunks
                chunk_records = []
                for chunk_data, embedding in zip(chunks, all_embeddings):
                    chunk_records.append(
                        KnowledgeBaseChunk(
                            organization_id=org_id,
                            upload_id=upload_id,
                            chunk_index=chunk_data["chunk_index"],
                            chunk_text=chunk_data["chunk_text"],
                            embedding=embedding,
                        )
                    )
                db.bulk_save_objects(chunk_records)

                # 7. Mark as ready
                upload.status = "ready"
                db.commit()
                logger.info(
                    "Upload {} processed: {} chunks stored",
                    upload_id,
                    len(chunk_records),
                )

            except Exception as e:
                db.rollback()
                logger.error("Upload {} processing failed: {}", upload_id, e)
                try:
                    upload = db.query(Upload).filter(Upload.id == upload_id).first()
                    if upload:
                        upload.status = "failed"
                        upload.meta_data = {**(upload.meta_data or {}), "error": str(e)}
                        db.commit()
                except Exception as meta_err:
                    logger.error("Failed to update error metadata: {}", meta_err)

    def reprocess_upload(self, upload_id: UUID, org_id: UUID):
        """Delete existing chunks and re-run the full pipeline."""
        self.process_upload(upload_id, org_id, delete_existing=True)
