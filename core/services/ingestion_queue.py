from __future__ import annotations

import threading
from uuid import UUID

from loguru import logger
from procrastinate import App, PsycopgConnector

from core.logging import get_applied_level, setup_logging
from shared.config import settings

# The Procrastinate worker starts via ``python -m procrastinate --app=core.services.ingestion_queue.app``
# which imports this module but never runs ``main.py``, so ``setup_logging()`` never fires and the
# default loguru format is used — stripping the ``trace_id=...`` prefix from every ingestion log.
# Installing the custom sink at import time fixes worker logs without affecting other processes:
# ``setup_logging`` is skipped when the sink is already applied (API server via ``main.py``,
# call subprocess via DB-resolved level), so no other entrypoint's log configuration is overridden.
if get_applied_level() is None:
    setup_logging()


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
    ingestion_run_id: str,
    delete_existing: bool = False,
) -> None:
    """Run one ingestion pipeline for an uploaded document. The router creates
    the pending ``ingestion_pipeline_runs`` row before defer and passes its id
    here; the worker flips it to ``running`` and reads every pipeline param
    (parser / tokeniser / embedder / store) off that row."""
    # Very first line — proves the worker picked the job even if the DB call
    # below (or any subsequent step) fails. Emitted BEFORE the trace_id is
    # stamped, so this single line is the only one in this task that lacks the
    # trace context — everything after ``ensure_trace_id`` is filterable by it.
    logger.info(
        "[ingestion] worker picked job upload={} run={} reprocess={}",
        upload_id, ingestion_run_id, delete_existing,
    )

    from core.database.session import get_db_context
    from core.services.document_processing_service import DocumentProcessingService
    from core.services.ingestion_run_service import IngestionRunService

    run_uuid = UUID(ingestion_run_id)
    try:
        # Stamp the trace_id BEFORE the first downstream log so every log
        # emitted from here on — including the pre-``mark_running`` steps
        # (upload load, R2 download) and the failure path — carries the same
        # filterable value. Idempotent on retries.
        with get_db_context() as db:
            IngestionRunService.ensure_trace_id(db, run_uuid)

        logger.info(
            "[ingestion] processing upload {} (run={}, reprocess={})",
            upload_id, ingestion_run_id, delete_existing,
        )
        DocumentProcessingService().process_upload(
            UUID(upload_id), UUID(org_id),
            ingestion_run_id=run_uuid,
            delete_existing=delete_existing,
        )
        logger.info(
            "[ingestion] worker task done upload={} run={}",
            upload_id, ingestion_run_id,
        )
    except Exception:
        # ``process_document`` already logs + persists its own failure, but any
        # exception escaping this task would otherwise land only in
        # Procrastinate's generic failure log — this line guarantees the app
        # log carries a traceback correlated by upload+run for tailing.
        logger.exception(
            "[ingestion] worker task crashed upload={} run={}",
            upload_id, ingestion_run_id,
        )
        raise


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
    ingestion_run_id,
) -> int:
    logger.info(
        "[ingestion] deferring job upload={} run={} reprocess={}",
        upload_id, ingestion_run_id, delete_existing,
    )
    try:
        async with app.open_async():
            job_id = await ingest_upload.defer_async(
                upload_id=str(upload_id),
                org_id=str(org_id),
                ingestion_run_id=str(ingestion_run_id),
                delete_existing=delete_existing,
            )
    except Exception:
        logger.exception(
            "[ingestion] defer_async failed upload={} run={} reprocess={}",
            upload_id, ingestion_run_id, delete_existing,
        )
        raise
    logger.info(
        "[ingestion] deferred job_id={} upload={} run={}",
        job_id, upload_id, ingestion_run_id,
    )
    return job_id


async def enqueue_upload(upload_id, org_id, ingestion_run_id) -> int:
    return await _defer_ingestion(upload_id, org_id, False, ingestion_run_id)


async def enqueue_reprocess(upload_id, org_id, ingestion_run_id) -> int:
    return await _defer_ingestion(upload_id, org_id, True, ingestion_run_id)


_EVAL_TRIGGERS = {"auto", "manual", "cli"}


@app.task(name="eval_ingestion_run", queue="eval")
def eval_ingestion_run(ingestion_run_id: str, triggered_by: str = "auto") -> None:
    """Run the RAG eval for a completed ingestion pipeline run.

    ``triggered_by`` is stamped on every ``eval_results`` row this task
    produces so the audit trail distinguishes the auto-run that fires after
    ingestion (``'auto'`` — the default, matches historic behavior) from a
    user-initiated batch (``'manual'``) or a CLI run (``'cli'``). Kept as a
    task argument (not derived from an env / setting) so multiple enqueue
    sites can produce runs with different attribution against the SAME
    Procrastinate task — no forked worker code needed.

    Runs on the dedicated ``eval`` queue (not ``ingestion``) so:
    (1) an older worker deployment that doesn't yet know this task can't grab
    the job and fail it as ``TaskNotFound`` before an updated worker sees it,
    and (2) slow LLM-heavy eval work (5-10 min per doc) doesn't compete with
    ingestion slots. Workers must include ``eval`` in ``--queues`` to consume.

    Idempotency: ``EvalService.get_or_generate_eval`` short-circuits when
    questions already exist for the upload, so a redelivered job reuses the
    existing set instead of regenerating. ``run_eval`` always inserts a fresh
    batch of ``eval_results`` rows tagged with a new ``run_id`` — duplicate
    delivery becomes a duplicate run rather than a partial update, which is
    what we want for audit.

    Failures are logged with a full traceback but NEVER re-raised: an eval
    outage must not fail the ingestion pipeline."""
    from uuid import UUID as _UUID

    from core.database.session import get_db_context
    from core.models.ingestion_pipeline_run import IngestionPipelineRun
    from core.services.evals.eval_service import EvalService

    # Defensive: workers get their kwargs off the wire, so validate here
    # too — an older enqueue site sending a stale/misspelled value must
    # not crash halfway through the eval loop with ``run_eval``'s ValueError.
    if triggered_by not in _EVAL_TRIGGERS:
        logger.warning(
            "[eval] unknown triggered_by={!r} on ingestion_run={}; defaulting to 'auto'",
            triggered_by, ingestion_run_id,
        )
        triggered_by = "auto"

    logger.info(
        "[eval] worker picked job ingestion_run={} triggered_by={}",
        ingestion_run_id, triggered_by,
    )
    try:
        with get_db_context() as db:
            run = (
                db.query(IngestionPipelineRun)
                .filter(IngestionPipelineRun.id == _UUID(ingestion_run_id))
                .first()
            )
            if run is None:
                logger.warning(
                    "[eval] run skipped: ingestion_run {} not found",
                    ingestion_run_id,
                )
                return
            svc = EvalService()
            logger.info(
                "[eval] resolving question set ingestion_run={} upload={} org={}",
                ingestion_run_id, run.upload_id, run.organization_id,
            )
            eval_set = svc.get_or_generate_eval(
                db, upload_id=run.upload_id, org_id=run.organization_id
            )
            logger.info(
                "[eval] running eval ingestion_run={} upload={} questions={} triggered_by={}",
                ingestion_run_id, run.upload_id, eval_set.question_count, triggered_by,
            )
            svc.run_eval(
                db,
                upload_id=run.upload_id,
                ingestion_run_id=run.id,
                triggered_by=triggered_by,
            )
        logger.info(
            "[eval] worker task done ingestion_run={}", ingestion_run_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "[eval] run failed for ingestion_run={} triggered_by={} (swallowed — ingestion is unaffected)",
            ingestion_run_id, triggered_by,
        )


async def enqueue_eval_for_ingestion_run(
    ingestion_run_id, triggered_by: str = "auto",
) -> int:
    async with app.open_async():
        return await eval_ingestion_run.defer_async(
            ingestion_run_id=str(ingestion_run_id),
            triggered_by=triggered_by,
        )


def enqueue_eval_for_ingestion_run_sync(
    ingestion_run_id, triggered_by: str = "auto",
) -> int:
    """Sync counterpart for callers inside a sync service method
    (``IngestionRunService.complete_run`` runs inside the ingestion worker,
    which is a sync ``def`` task executed in the worker's threadpool thread).

    Why an ephemeral app: the module-level ``app`` uses an async
    ``PsycopgConnector`` whose psycopg pool is bound to the worker's main
    event loop. Opening the SAME connector from a fresh ``asyncio.run`` loop
    inside a threadpool thread creates cross-loop futures — closing the pool
    on our loop raises ``ValueError: future belongs to a different loop`` and
    leaves the worker's pool in a closed state (the whole worker then errors
    on ``pool 'pool-1' is already closed``). Instead, spin up a one-shot
    ``SyncPsycopgConnector``-backed app just for the defer, then close it.
    Fully isolated — cannot touch the shared async pool."""
    from procrastinate import App as _App
    from procrastinate import SyncPsycopgConnector

    # ``kwargs`` on ``SyncPsycopgConnector`` are forwarded to psycopg's sync
    # ``ConnectionPool``. Cap it small — this pool exists only long enough to
    # defer one job, so we don't want to hold more than a single connection.
    ephemeral = _App(
        connector=SyncPsycopgConnector(
            conninfo=_conninfo(), min_size=1, max_size=1
        )
    )
    with ephemeral.open():
        # Defer by task name — the task doesn't need to be registered on this
        # ephemeral app; the worker (running with the shared ``app``) resolves
        # the name against its own registry when it picks the job up.
        return ephemeral.configure_task(
            name="eval_ingestion_run",
            queue="eval",
        ).defer(ingestion_run_id=str(ingestion_run_id), triggered_by=triggered_by)


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


@app.periodic(cron="*/5 * * * *")
@app.task(name="reap_orphaned_calls", queue="pod_sync")
def reap_orphaned_calls_task(timestamp: int) -> None:
    """Close calls left with ended_at NULL because their pod was SIGKILLed mid-call
    (spot reclaim, OOM, node loss, or a deploy that outran the drain). Without this they
    show 'in process' forever. Idempotent; only touches rows older than the max call length."""
    from core.database.session import get_db_context
    from core.services.call_log_service import CallLogService

    with get_db_context() as db:
        CallLogService(db).reap_orphaned_calls()


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
