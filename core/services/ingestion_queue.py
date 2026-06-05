from __future__ import annotations

from uuid import UUID

from loguru import logger
from procrastinate import App, PsycopgConnector

from shared.config import settings


def _conninfo() -> str:
    url = settings.DATABASE_URL
    return url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")


app = App(connector=PsycopgConnector(conninfo=_conninfo(), min_size=1, max_size=6))


@app.task(name="ingest_upload", queue="ingestion")
def ingest_upload(upload_id: str, org_id: str, delete_existing: bool = False) -> None:
    from core.services.document_processing_service import DocumentProcessingService

    logger.info("[ingestion] processing upload {} (reprocess={})", upload_id, delete_existing)
    DocumentProcessingService().process_upload(UUID(upload_id), UUID(org_id), delete_existing=delete_existing)


async def _defer_ingestion(upload_id, org_id, delete_existing: bool) -> int:
    async with app.open_async():
        return await ingest_upload.defer_async(
            upload_id=str(upload_id), org_id=str(org_id), delete_existing=delete_existing
        )


async def enqueue_upload(upload_id, org_id) -> int:
    return await _defer_ingestion(upload_id, org_id, False)


async def enqueue_reprocess(upload_id, org_id) -> int:
    return await _defer_ingestion(upload_id, org_id, True)
