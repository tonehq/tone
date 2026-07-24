from __future__ import annotations

import threading
from uuid import UUID

from loguru import logger
from procrastinate import App, PsycopgConnector

from shared.config import settings


def _conninfo() -> str:
    url = settings.DATABASE_URL
    return url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")


app = App(connector=PsycopgConnector(conninfo=_conninfo(), min_size=1, max_size=6))

# The module-level ``app`` is a shared singleton. Opening it (``app.open()`` /
# ``app.open_async()``) opens AND closes the connector, so two threads doing it concurrently can
# close it mid-defer in the other ("App was not open"). This surfaces on the post-call path when
# several WebSocket-bridge calls (each a daemon thread) complete at once — each fires both the
# sync post-call defers AND, via the completion refill, ``enqueue_outbound_calls_batch``.
# EVERY threaded open→defer→close of the shared app is serialized through this one lock (the sync
# ``with app.open()`` helpers below, and the ``asyncio.run`` entry points that open_async off a
# worker thread) so at most one open/close cycle touches the connector at a time. Defers are
# quick, so the added contention is negligible. Async-context callers (the ``async def`` enqueue
# variants that await on the single main event loop) don't take this lock — a threading.Lock in
# async code would block the loop, and same-loop opens don't race across threads.
_APP_OPEN_LOCK = threading.Lock()


def _defer_sync(task, **kwargs) -> int:
    """Thread-safe ``with app.open(): task.defer(**kwargs)`` (see ``_APP_OPEN_LOCK``)."""
    with _APP_OPEN_LOCK:
        with app.open():
            return task.defer(**kwargs)


@app.task(name="ingest_upload", queue="ingestion")
def ingest_upload(
    upload_id: str,
    org_id: str,
    delete_existing: bool = False,
    run_config: dict | None = None,
) -> None:
    """Run one ingestion pipeline for an uploaded document.

    ``run_config`` is an optional dict of pipeline overrides (parser / tokeniser /
    embedding_provider / embedding_model / embedding_dimensions / vector_store /
    vector_store_ref, plus any per-component *_config sub-dict). Anything left
    unset falls back to the org / system defaults resolved by
    ``IngestionRunService.resolve_run_config``. Must be JSON-serialisable —
    Procrastinate stores task kwargs as JSON.
    """
    from core.services.document_processing_service import DocumentProcessingService

    logger.info(
        "[ingestion] processing upload {} (reprocess={}, custom_config={})",
        upload_id, delete_existing, bool(run_config),
    )
    DocumentProcessingService().process_upload(
        UUID(upload_id), UUID(org_id),
        delete_existing=delete_existing, run_config=run_config,
    )


@app.task(name="run_contact_sync", queue="contact_import")
def run_contact_sync(sync_id: str, org_id: str) -> None:
    """Execute one directory sync run: source → map → validate → upsert → auto-assign.

    Idempotent: ``ContactSyncService.run_contact_sync`` upserts by
    ``(directory_id, external_id)``, so a re-delivered job re-parses the same file to the
    same result rather than duplicating contacts.
    """
    from uuid import UUID as _UUID

    from core.database.session import get_db_context
    from core.services.contacts.contact_sync_service import ContactSyncService

    logger.info("[contact-sync] worker running sync sync_id={} org={}", sync_id, org_id)
    with get_db_context() as db:
        service = ContactSyncService(db, org_id=_UUID(org_id))
        sync = service.get_contact_sync(_UUID(sync_id))
        service.run_contact_sync(sync)


async def enqueue_contact_sync(sync_id, org_id) -> int:
    async with app.open_async():
        return await run_contact_sync.defer_async(sync_id=str(sync_id), org_id=str(org_id))


def enqueue_contact_sync_sync(sync_id, org_id) -> int:
    """Sync counterpart for callers inside a sync route handler (the contact-syncs router
    runs in the threadpool)."""
    with app.open():
        return run_contact_sync.defer(sync_id=str(sync_id), org_id=str(org_id))


@app.periodic(cron="* * * * *")
@app.task(name="sync_pods_and_nodes", queue="pod_sync")
def sync_pods_and_nodes_task(timestamp: int) -> None:
    from core.jobs.pod_sync import sync_pods_and_nodes

    sync_pods_and_nodes()


@app.task(name="detect_call_overlaps", queue="call_overlaps")
def detect_call_overlaps_task(call_id: str) -> None:
    from core.jobs.call_overlap import detect_call_overlaps

    detect_call_overlaps(call_id=call_id)


@app.task(name="consolidate_call_transcript", queue="call_transcripts")
def consolidate_call_transcript_task(call_id: str) -> None:
    from core.jobs.consolidated_transcript import consolidate_call_transcript

    consolidate_call_transcript(call_id=call_id)


@app.task(name="compute_call_metrics_aggregates", queue="call_metrics")
def compute_call_metrics_aggregates_task(call_id: str) -> None:
    from core.jobs.call_metrics_aggregates import compute_call_metrics_aggregates

    compute_call_metrics_aggregates(call_id=call_id)


@app.task(name="sync_loki_logs", queue="log_sync", retry=3)
def sync_loki_logs_task(call_id: str) -> None:
    from core.jobs.sync_loki import sync_call_logs

    sync_call_logs(call_id=call_id)


async def _defer_ingestion(
    upload_id,
    org_id,
    delete_existing: bool,
    run_config: dict | None = None,
) -> int:
    async with app.open_async():
        return await ingest_upload.defer_async(
            upload_id=str(upload_id),
            org_id=str(org_id),
            delete_existing=delete_existing,
            run_config=run_config,
        )


async def enqueue_upload(upload_id, org_id, run_config: dict | None = None) -> int:
    return await _defer_ingestion(upload_id, org_id, False, run_config=run_config)


async def enqueue_reprocess(upload_id, org_id, run_config: dict | None = None) -> int:
    return await _defer_ingestion(upload_id, org_id, True, run_config=run_config)


@app.task(name="execute_outbound_call", queue="outbound_calls")
def execute_outbound_call(scheduled_call_id: str, org_id: str) -> None:
    """Dispatch a scheduled outbound call when its ``schedule_at`` fires.

    Idempotent: ``dispatch_scheduled_call`` atomically claims ``scheduled -> processing``
    and is a no-op if the row was already canceled or dispatched, so a re-delivered job
    never double-dials.
    """
    from uuid import UUID as _UUID

    from core.database.session import get_db_context
    from core.services.outbound_call_service import OutboundCallService

    logger.info("[outbound] worker dispatching scheduled call id={} org={}", scheduled_call_id, org_id)
    with get_db_context() as db:
        OutboundCallService(db, org_id=_UUID(org_id)).dispatch_scheduled_call(_UUID(scheduled_call_id))


@app.periodic(cron="* * * * *")
@app.task(name="reconcile_outbound_calls", queue="outbound_calls")
def reconcile_outbound_calls(timestamp: int) -> None:
    """Safety net for scheduled calls that were persisted but never enqueued (e.g. the API
    died between committing the rows and deferring their jobs). Re-enqueues them so they
    can't be stranded as 'scheduled' forever. Idempotent — see
    ``reconcile_orphaned_scheduled_calls``."""
    from core.database.session import get_db_context
    from core.services.outbound_call_service import OutboundCallService

    with get_db_context() as db:
        OutboundCallService(db).reconcile_orphaned_scheduled_calls()


@app.periodic(cron="* * * * *")
@app.task(name="drain_outbound_calls", queue="outbound_calls")
def drain_outbound_calls(timestamp: int) -> None:
    """Concurrency safety net: for batches carrying a per-batch limit, fill any free slots
    with due, waiting scheduled calls that were held back at dispatch. Instant refill happens
    on each call's completion webhook; this catches slots stranded by a missed/late terminal
    callback. No-op when there are no batch-limited waiting rows."""
    from core.database.session import get_db_context
    from core.services.outbound_call_service import OutboundCallService

    with get_db_context() as db:
        OutboundCallService(db).drain_outbound_capacity()


def enqueue_outbound_calls_batch(items):
    """Defer one or many scheduled outbound calls over a single Procrastinate connection.

    ``items`` is a sequence of ``(scheduled_call_id, org_id, schedule_at)`` tuples. Opens
    the app once and defers every job inside it, instead of a connect/defer/close cycle
    per row — so a bulk batch doesn't churn connections. Sync-friendly (runs its own loop)
    so the API route (a sync ``def`` in the threadpool) can call it.

    Returns a list of ``(job_id, error)`` tuples aligned to ``items``: ``job_id`` is the
    Procrastinate job id on success (store it to allow cancellation), or ``None`` with a
    string ``error`` when that row failed to enqueue. Failures are isolated per row so one
    bad defer doesn't drop the rest of the batch.
    """
    import asyncio

    items = list(items)

    async def _defer_all():
        results = []
        async with app.open_async():
            for scheduled_call_id, org_id, schedule_at in items:
                try:
                    job_id = await execute_outbound_call.configure(schedule_at=schedule_at).defer_async(
                        scheduled_call_id=str(scheduled_call_id), org_id=str(org_id)
                    )
                    results.append((job_id, None))
                except Exception as exc:  # noqa: BLE001
                    # Per-item: one bad defer must not drop the rest of the batch.
                    # Capture the error for the caller and log the traceback.
                    logger.exception("[outbound] defer failed for scheduled_call_id={}", scheduled_call_id)
                    results.append((None, str(exc)))
        return results

    # Serialize with every other threaded open/close of the shared app (see _APP_OPEN_LOCK).
    # Held across the whole batch's open_async→defer→close; callers are all sync (request
    # threadpool / completion-refill worker thread), never the async event loop.
    with _APP_OPEN_LOCK:
        return asyncio.run(_defer_all())


def cancel_outbound_job(job_id: int) -> bool:
    """Best-effort cancel of a deferred outbound-dial job. The ``dial`` claim guard is
    the real safety net, so a failure here is logged and swallowed."""
    import asyncio

    async def _cancel() -> bool:
        async with app.open_async():
            return await app.job_manager.cancel_job_by_id_async(job_id)

    try:
        # Serialize with every other threaded open/close of the shared app (see _APP_OPEN_LOCK);
        # sync callers only (scheduled-call cancel / directory delete).
        with _APP_OPEN_LOCK:
            return asyncio.run(_cancel())
    except Exception:  # noqa: BLE001
        logger.exception("[outbound] cancel_outbound_job failed job_id={}", job_id)
        return False


async def enqueue_call_overlap_detection(call_id) -> int:
    async with app.open_async():
        return await detect_call_overlaps_task.defer_async(call_id=str(call_id))


def enqueue_call_overlap_detection_sync(call_id) -> int:
    """Sync counterpart for callers inside a sync service method
    (e.g. ``CallLogService.complete_call``)."""
    return _defer_sync(detect_call_overlaps_task, call_id=str(call_id))


async def enqueue_consolidate_call_transcript(call_id) -> int:
    async with app.open_async():
        return await consolidate_call_transcript_task.defer_async(call_id=str(call_id))


def enqueue_consolidate_call_transcript_sync(call_id) -> int:
    """Sync counterpart for post-call actions running inside
    ``CallLogService.complete_call`` (a sync service method)."""
    return _defer_sync(consolidate_call_transcript_task, call_id=str(call_id))


async def enqueue_compute_call_metrics_aggregates(call_id) -> int:
    async with app.open_async():
        return await compute_call_metrics_aggregates_task.defer_async(call_id=str(call_id))


def enqueue_compute_call_metrics_aggregates_sync(call_id) -> int:
    """Sync counterpart mirroring ``enqueue_consolidate_call_transcript_sync`` —
    called from ``PostCallHandler`` which runs inside the sync completion
    path."""
    return _defer_sync(compute_call_metrics_aggregates_task, call_id=str(call_id))


async def enqueue_loki_log_sync(call_id, *, delay_seconds: int = 0) -> int:
    async with app.open_async():
        return await sync_loki_logs_task.configure(
            schedule_in={"seconds": delay_seconds}
        ).defer_async(call_id=str(call_id))


def enqueue_loki_log_sync_sync(call_id, *, delay_seconds: int = 0) -> int:
    """Sync counterpart for the ``sync_loki_logs`` post-call action (runs inside
    the sync completion path). ``delay_seconds`` defers the job so Loki has time
    to ingest the call's teardown lines before we read them back."""
    with _APP_OPEN_LOCK:
        with app.open():
            return sync_loki_logs_task.configure(
                schedule_in={"seconds": delay_seconds}
            ).defer(call_id=str(call_id))
