import os
import tempfile
from typing import Optional
from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.ingestion_run_service import IngestionRunService
from core.services.r2_storage_service import R2StorageService
from core.services.rag.embedder_factory import build_embedder_from_run
from core.services.rag.errors import EmbeddingProviderUnavailableError
from core.services.rag.factory import get_vector_store
from core.services.rag.parser_factory import get_parser
from core.services.rag.pdf_router import HTML_CONTENT_TYPE, PDF_CONTENT_TYPE, PdfRoutingService
from core.services.rag.pipeline import RAGPipeline
from core.services.rag.provider_keys import ProviderKeyService
from core.services.rag.tokeniser_factory import get_tokeniser

DIRECT_PDF_DOCLING = False
DIRECT_PDF_OCR = False
DIRECT_PDF_MAX_PAGES = 0


_CONTENT_TYPE_DOC_TYPE = {
    "application/pdf": "pdf",
    "text/html": "html",
    "text/plain": "txt",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


def _derive_doc_type(file_name: str | None, file_type: str | None) -> str | None:
    if file_name and "." in file_name:
        return file_name.rsplit(".", 1)[-1].lower() or None
    if file_type:
        return _CONTENT_TYPE_DOC_TYPE.get(file_type.split(";")[0].strip().lower())
    return None


def _remove_files(*paths: str) -> None:
    for path in paths:
        if not path:
            continue
        try:
            os.remove(path)
        except OSError:
            pass


class DocumentProcessingService:

    def process_document(
        self,
        upload_id: UUID,
        org_id: UUID,
        file_bytes: bytes,
        delete_existing: bool = False,
        run_config: Optional[dict] = None,
    ):
        run: Optional[IngestionPipelineRun] = None
        try:
            with get_db_context() as db:
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if not upload:
                    logger.error("Upload {} not found, skipping processing", upload_id)
                    return
                file_type = upload.file_type
                upload.status = "processing"
                kb = (
                    db.query(KnowledgeBase)
                    .filter(KnowledgeBase.upload_id == upload_id)
                    .first()
                )
                if kb is None:
                    logger.error(
                        "No KnowledgeBase found for upload {}, cannot open ingestion run",
                        upload_id,
                    )
                    return
                kb_id = kb.id
                db.commit()

                cfg = IngestionRunService.resolve_run_config(
                    db, org_id, kb_id, run_config
                )
                run = IngestionRunService.begin_run(
                    db,
                    upload_id=upload_id,
                    knowledge_base_id=kb_id,
                    org_id=org_id,
                    config=cfg,
                )

                if delete_existing:
                    # Wipe the previous ready run's data so re-ingest starts clean.
                    prior = (
                        db.query(IngestionPipelineRun)
                        .filter(
                            IngestionPipelineRun.upload_id == upload_id,
                            IngestionPipelineRun.id != run.id,
                            IngestionPipelineRun.is_active.is_(True),
                        )
                        .all()
                    )
                    for old in prior:
                        db.delete(old)
                    db.commit()

                api_key = ProviderKeyService.get_key(db, org_id, run.embedding_provider)
                if not api_key:
                    raise EmbeddingProviderUnavailableError(
                        f"No {run.embedding_provider!r} API key configured for embedding"
                    )

                parser_cfg = dict(run.parser_config or {})
                if run.parser == "docling" and DIRECT_PDF_DOCLING and file_type == PDF_CONTENT_TYPE:
                    # Local dev toggle: run docling directly on the PDF (with OCR) instead of
                    # routing through PdfRoutingService. Kept behind flags at module top.
                    page_range = (1, DIRECT_PDF_MAX_PAGES) if DIRECT_PDF_MAX_PAGES else None
                    parser_cfg.setdefault("ocr", DIRECT_PDF_OCR)
                    parser_cfg.setdefault("tables", DIRECT_PDF_OCR)
                    if page_range:
                        parser_cfg.setdefault("page_range", page_range)

                parser = get_parser(run.parser, config=parser_cfg)
                chunker = get_tokeniser(run.tokeniser, config=run.tokeniser_config)
                embedder = build_embedder_from_run(run, api_key=api_key)
                store = get_vector_store(run.vector_store, **(run.vector_store_ref or {}))
                pipeline = RAGPipeline(
                    run=run,
                    parser=parser,
                    chunker=chunker,
                    embedder=embedder,
                    store=store,
                )

            def _on_batch(batch_index: int, start_page: int, end_page: int, count: int, elapsed: float) -> None:
                logger.info(
                    "[ingestion] pages {}-{}: {} chunks stored in {:.1f}s",
                    start_page, end_page, count, elapsed,
                )

            pdf_path = None
            html_path = None
            build = None
            direct = file_type == PDF_CONTENT_TYPE and DIRECT_PDF_DOCLING
            # PdfRoutingService converts PDF → HTML so docling can pick up tables /
            # images via its HTML pipeline. Only the docling parser benefits from
            # this — every other parser (pypdf, docx, text, composite) expects the
            # ORIGINAL PDF bytes, so we skip the route for them and stream the raw
            # PDF straight through ``ingest_file_paged``.
            uses_pdf_html_route = (
                file_type == PDF_CONTENT_TYPE and not direct and run.parser == "docling"
            )
            if uses_pdf_html_route:
                pdf_fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
                with os.fdopen(pdf_fd, "wb") as f:
                    f.write(file_bytes)
                html_fd, html_path = tempfile.mkstemp(suffix=".html")
                os.close(html_fd)
                build = PdfRoutingService().build(pdf_path, html_path)
                _remove_files(pdf_path)
                pdf_path = None

            try:
                if direct:
                    logger.info(
                        "[direct-pdf] docling parsing PDF directly (ocr={}, tables={}, max_pages={})",
                        DIRECT_PDF_OCR, DIRECT_PDF_OCR, DIRECT_PDF_MAX_PAGES,
                    )
                    num_chunks = pipeline.ingest_file_streaming(
                        file_bytes, file_type
                    )
                elif build is not None:
                    num_chunks = pipeline.ingest_path(
                        build.html_path, HTML_CONTENT_TYPE
                    )
                else:
                    num_chunks = pipeline.ingest_file_paged(
                        file_bytes,
                        file_type,
                        page_batch=50,
                        on_batch=_on_batch,
                    )
            finally:
                _remove_files(pdf_path, html_path)
            if not num_chunks:
                raise ValueError("Text extraction produced no chunks")

            ingestion_stats = build.metrics() if build is not None else None
            with get_db_context() as db:
                IngestionRunService.complete_run(db, run.id, chunk_count=num_chunks)
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if upload:
                    upload.status = "ready"
                    if ingestion_stats is not None:
                        upload.meta_data = {**(upload.meta_data or {}), "routing": ingestion_stats}
                doc_type = _derive_doc_type(
                    upload.file_name if upload else None, file_type
                )
                db.query(KnowledgeBase).filter(
                    KnowledgeBase.upload_id == upload_id
                ).update(
                    {
                        KnowledgeBase.status: "ready",
                        KnowledgeBase.doc_type: doc_type,
                        KnowledgeBase.ingestion_stats: ingestion_stats,
                    },
                    synchronize_session=False,
                )
                db.commit()
            logger.info("Upload {} processed: {} chunks stored (run={})", upload_id, num_chunks, run.id)

        except Exception as e:
            logger.exception("[ingestion] upload {} failed", upload_id)
            try:
                with get_db_context() as db:
                    if run is not None:
                        IngestionRunService.fail_run(db, run.id, error=str(e))
                    upload = db.query(Upload).filter(Upload.id == upload_id).first()
                    if upload:
                        upload.status = "failed"
                        upload.meta_data = {**(upload.meta_data or {}), "error": str(e)}
                    db.query(KnowledgeBase).filter(
                        KnowledgeBase.upload_id == upload_id
                    ).update(
                        {KnowledgeBase.status: "failed"},
                        synchronize_session=False,
                    )
                    db.commit()
            except Exception:
                logger.exception("[ingestion] failed to update error metadata for upload {}", upload_id)

    def process_upload(
        self,
        upload_id: UUID,
        org_id: UUID,
        delete_existing: bool = False,
        run_config: Optional[dict] = None,
    ):
        with get_db_context() as db:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if not upload or not upload.file_path:
                logger.error("Upload {} not found or has no file_path", upload_id)
                return
            file_path = upload.file_path

        file_bytes = R2StorageService().download_file(file_path)
        self.process_document(
            upload_id, org_id, file_bytes,
            delete_existing=delete_existing, run_config=run_config,
        )

    def reprocess_upload(
        self, upload_id: UUID, org_id: UUID, run_config: Optional[dict] = None,
    ):
        self.process_upload(upload_id, org_id, delete_existing=True, run_config=run_config)
