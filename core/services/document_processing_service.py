import os
import tempfile
import time
from typing import Optional
from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.ingestion_run_service import IngestionRunService
from core.services.r2_storage_service import R2StorageService
from core.services.rag.builders import build_pipeline_from_run
from core.services.rag.errors import EmbeddingProviderUnavailableError, humanize_ingestion_error
from core.services.rag.pdf_router import HTML_CONTENT_TYPE, PDF_CONTENT_TYPE, PdfRoutingService
from core.services.rag.provider_keys import ProviderKeyService


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
        ingestion_run_id: UUID,
        delete_existing: bool = False,
    ):
        run: Optional[IngestionPipelineRun] = None
        t_start = time.monotonic()
        try:
            logger.info(
                "[ingestion] process_document start upload={} run={} bytes={} reprocess={}",
                upload_id, ingestion_run_id, len(file_bytes), delete_existing,
            )
            with get_db_context() as db:
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if not upload:
                    logger.warning(
                        "[ingestion] upload {} not found, skipping processing (run={})",
                        upload_id, ingestion_run_id,
                    )
                    return
                file_type = upload.file_type
                upload.status = "processing"
                db.commit()

                # The pending run row was created by the router before the
                # Procrastinate defer — just flip it to running here. Pipeline
                # params (parser/tokeniser/embedder/store) live on that row, so
                # no resolve_run_config is needed on the worker side.
                run = IngestionRunService.mark_running(db, ingestion_run_id)

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
                    if prior:
                        logger.info(
                            "[ingestion] reprocess wiping {} prior active run(s) upload={} new_run={}",
                            len(prior), upload_id, run.id,
                        )
                    for old in prior:
                        db.delete(old)
                    db.commit()

                api_key = ProviderKeyService.get_key(db, org_id, run.embedding_provider)
                if not api_key:
                    logger.warning(
                        "[ingestion] provider key missing org={} provider={} run={}",
                        org_id, run.embedding_provider, run.id,
                    )
                    raise EmbeddingProviderUnavailableError(
                        f"No {run.embedding_provider!r} API key configured for embedding"
                    )
                logger.debug(
                    "[ingestion] provider key resolved org={} provider={} run={}",
                    org_id, run.embedding_provider, run.id,
                )

                # One shared builder assembles parser → chunker → embedder →
                # store from the run row (see core/services/rag/builders.py) so
                # ingestion, eval, and retrieval don't each re-wire the factories.
                pipeline = build_pipeline_from_run(run, api_key=api_key)
                logger.info(
                    "[ingestion] pipeline built run={} parser={} tokeniser={} "
                    "embedder={}({}d) store={} file_type={}",
                    run.id, run.parser, run.tokeniser,
                    run.embedding_model, run.embedding_dimensions,
                    run.vector_store, file_type,
                )

            def _on_batch(batch_index: int, start_page: int, end_page: int, count: int, elapsed: float) -> None:
                logger.info(
                    "[ingestion] pages {}-{}: {} chunks stored in {:.1f}s",
                    start_page, end_page, count, elapsed,
                )

            pdf_path = None
            html_path = None
            build = None
            # PdfRoutingService converts PDF → HTML so docling can pick up tables /
            # images via its HTML pipeline. Only the docling parser benefits from
            # this — every other parser (pypdf, docx, text, composite) expects the
            # ORIGINAL PDF bytes, so we skip the route for them and stream the raw
            # PDF straight through ``ingest_file_paged``.
            uses_pdf_html_route = (
                file_type == PDF_CONTENT_TYPE and run.parser == "docling"
            )
            if uses_pdf_html_route:
                logger.info(
                    "[ingestion] pdf→html routing start run={} bytes={}",
                    run.id, len(file_bytes),
                )
                t_route = time.monotonic()
                pdf_fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
                with os.fdopen(pdf_fd, "wb") as f:
                    f.write(file_bytes)
                html_fd, html_path = tempfile.mkstemp(suffix=".html")
                os.close(html_fd)
                try:
                    build = PdfRoutingService().build(pdf_path, html_path)
                except Exception:
                    logger.exception(
                        "[ingestion] pdf→html routing failed run={} pdf={} html={}",
                        run.id, pdf_path, html_path,
                    )
                    raise
                _remove_files(pdf_path)
                pdf_path = None
                logger.info(
                    "[ingestion] pdf→html routing done run={} elapsed_s={:.1f}",
                    run.id, time.monotonic() - t_route,
                )

            try:
                t_ingest = time.monotonic()
                if build is not None:
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
                logger.info(
                    "[ingestion] pipeline ingest done run={} chunks={} elapsed_s={:.1f}",
                    run.id, num_chunks, time.monotonic() - t_ingest,
                )
            finally:
                _remove_files(pdf_path, html_path)
            if not num_chunks:
                # #1 cause of silent failures — surface all inputs before raising.
                logger.warning(
                    "[ingestion] extraction produced 0 chunks run={} upload={} "
                    "file_type={} bytes={} parser={}",
                    run.id, upload_id, file_type, len(file_bytes), run.parser,
                )
                raise ValueError("Text extraction produced no chunks")

            ingestion_stats = build.metrics() if build is not None else None
            with get_db_context() as db:
                IngestionRunService.complete_run(
                    db,
                    run.id,
                    chunk_count=num_chunks,
                    ingestion_stats=ingestion_stats,
                )
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
            logger.info(
                "[ingestion] upload {} processed: {} chunks stored (run={}, elapsed_s={:.1f})",
                upload_id, num_chunks, run.id, time.monotonic() - t_start,
            )

        except Exception as e:
            logger.exception(
                "[ingestion] upload {} failed (run={}, elapsed_s={:.1f})",
                upload_id, ingestion_run_id, time.monotonic() - t_start,
            )
            # Sanitize before persisting — the raw provider exception (e.g.
            # OpenAI ``NotFoundError`` for a bad model name) stringifies to
            # a noisy `Error code: 404 - {'error': {...}}` dump that the UI
            # would otherwise show verbatim. ``humanize_ingestion_error``
            # returns a short, user-friendly one-liner; the full traceback
            # is already captured above by ``logger.exception``.
            user_error = humanize_ingestion_error(e)
            try:
                with get_db_context() as db:
                    # Use the router-created pending run id as the fallback in
                    # case mark_running itself raised — the row still exists
                    # and needs to be flipped to failed.
                    fail_id = run.id if run is not None else ingestion_run_id
                    try:
                        IngestionRunService.fail_run(db, fail_id, error=user_error)
                    except ValueError:
                        logger.warning(
                            "[ingestion] pending run {} missing during failure handling",
                            fail_id,
                        )
                    upload = db.query(Upload).filter(Upload.id == upload_id).first()
                    if upload:
                        upload.status = "failed"
                        upload.meta_data = {**(upload.meta_data or {}), "error": user_error}
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
        ingestion_run_id: UUID,
        delete_existing: bool = False,
    ):
        with get_db_context() as db:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if not upload or not upload.file_path:
                logger.warning(
                    "[ingestion] upload {} not found or has no file_path (run={})",
                    upload_id, ingestion_run_id,
                )
                return
            file_path = upload.file_path

        logger.info(
            "[r2] downloading upload={} run={} path={}",
            upload_id, ingestion_run_id, file_path,
        )
        t_dl = time.monotonic()
        try:
            file_bytes = R2StorageService().download_file(file_path)
        except Exception:
            logger.exception(
                "[r2] download failed upload={} run={} path={}",
                upload_id, ingestion_run_id, file_path,
            )
            raise
        logger.info(
            "[r2] downloaded upload={} run={} bytes={} elapsed_s={:.1f}",
            upload_id, ingestion_run_id, len(file_bytes),
            time.monotonic() - t_dl,
        )
        self.process_document(
            upload_id, org_id, file_bytes,
            ingestion_run_id=ingestion_run_id,
            delete_existing=delete_existing,
        )
