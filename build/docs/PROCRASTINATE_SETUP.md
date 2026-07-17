# Procrastinate Background Jobs — Setup Guide

How Tone runs background jobs with [Procrastinate](https://procrastinate.readthedocs.io)
(a Postgres-backed job queue — no Redis, no RabbitMQ), and how to recreate the same
setup in another project or another queue inside this one.

Everything below is derived from the working implementation:

| Piece | File |
|---|---|
| App + task definitions | `core/services/ingestion_queue.py` |
| Read-only ORM models for job status | `core/models/procrastinate.py` |
| Queue schema migration | `alembic/versions/b2e9f47a1c30_procrastinate_schema.py` |
| Autogenerate exclusion | `alembic/env.py` (`include_object`) |
| Producer (enqueue from API) | `core/api/v1/knowledge_base_routes.py` |
| Worker process | `build/kubernetes/staging-aws/worker/deployment.yaml` |
| Local schema bootstrap | `db-bootstrap.sh` |

---

## How it fits together

```
FastAPI request ──► enqueue_upload()  ──► INSERT into procrastinate_jobs  (same Postgres)
                       (defer_async)                    │
                                                        ▼
                                      worker process ── polls / LISTEN-NOTIFY
                                                        │
                                                        ▼
                                             ingest_upload() runs the real work
```

Jobs live in the **application database**. The API only inserts a row and returns; a
separate long-running worker process picks it up. Two independent queues run today:
`ingestion` (document processing, on demand) and `pod_sync` (periodic, every minute).

---

## Step 1 — Dependencies

```
procrastinate==3.8.1
psycopg[binary]==3.3.4
psycopg-pool==3.3.1
```

Procrastinate 3.x uses psycopg 3. Pin the version — the queue schema is tied to it,
and a major upgrade means a schema migration.

---

## Step 2 — Define the app and its tasks

One module owns the `App`. Everything else imports from it. Tone's is
`core/services/ingestion_queue.py`:

```python
from procrastinate import App, PsycopgConnector
from shared.config import settings


def _conninfo() -> str:
    url = settings.DATABASE_URL
    return url.replace("postgresql+psycopg2://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


app = App(connector=PsycopgConnector(conninfo=_conninfo(), min_size=1, max_size=6))


@app.task(name="ingest_upload", queue="ingestion")
def ingest_upload(upload_id: str, org_id: str, delete_existing: bool = False) -> None:
    from core.services.document_processing_service import DocumentProcessingService

    DocumentProcessingService().process_upload(
        UUID(upload_id), UUID(org_id), delete_existing=delete_existing
    )
```

Four rules this encodes, each of which matters:

**Strip the SQLAlchemy dialect from the URL.** Procrastinate takes a raw libpq
conninfo string, not a SQLAlchemy URL. `postgresql+psycopg2://…` will not connect.
`_conninfo()` exists solely to reuse one `DATABASE_URL` for both.

**Name every task explicitly.** `name="ingest_upload"` is what gets written to
`procrastinate_jobs.task_name`. Without it the name is derived from the module path,
so moving the file orphans every job already queued.

**Give each task its own queue.** Queues are the unit of worker assignment — a worker
subscribes to a queue list. Sharing one queue between a fast periodic job and a slow
CPU-bound one means the slow one starves the fast one.

**Import heavy dependencies inside the task body.** The producer (the API pod) imports
this module to enqueue, so anything at module top level gets imported into the API too.
`DocumentProcessingService` pulls in Docling and torch — deferring the import keeps it
out of the API's memory.

**Task arguments must be JSON-serializable.** They land in a JSONB column. Pass
`str(uuid)`, not `UUID`; re-parse inside the task.

---

## Step 3 — Create the queue schema

Procrastinate needs its own tables (`procrastinate_jobs`, `procrastinate_workers`,
`procrastinate_events`, `procrastinate_periodic_defers`) plus functions and triggers.
There are two ways to install them, and **this repo does both** — pick one when
starting fresh.

### Option A — the CLI (what the docs and bootstrap scripts use)

```bash
PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply
```

One-time per environment/database. `--app` is `<module path>.<app variable>`.
`db-bootstrap.sh` guards it so re-runs are safe:

```bash
if PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app healthchecks &>/dev/null; then
    echo "    Schema already applied — skipping."
else
    PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply
fi
```

### Option B — an Alembic migration

`alembic/versions/b2e9f47a1c30_procrastinate_schema.py` embeds the same DDL as a raw
SQL string and executes it in `upgrade()`. Generate it by dumping the schema instead
of applying it:

```bash
PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply --dry-run
```

Option B is the better default for a new project: one `alembic upgrade head` sets up
everything, no separate step to forget on a new environment. Option A is what the
runbooks here reference, so both are kept in sync.

### Required either way — exclude the tables from autogenerate

Procrastinate owns these tables; Alembic must not manage them, or the next
`--autogenerate` emits DROP statements for the whole queue. In `alembic/env.py`:

```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name and name.startswith("procrastinate_"):
        return False
    table = getattr(object, "table", None)
    if table is not None and getattr(table, "name", "").startswith("procrastinate_"):
        return False
    return True
```

Pass it into both `context.configure(...)` calls (online and offline).

---

## Step 4 — Enqueue from the API

```python
async def _defer_ingestion(upload_id, org_id, delete_existing: bool) -> int:
    async with app.open_async():
        return await ingest_upload.defer_async(
            upload_id=str(upload_id), org_id=str(org_id), delete_existing=delete_existing
        )


async def enqueue_upload(upload_id, org_id) -> int:
    return await _defer_ingestion(upload_id, org_id, False)
```

`defer_async` returns the job id. Store it on your domain row so the UI can poll status
later — `knowledge_bases.procrastinate_job_id`, added in migration `6bd88c8ee3dc`:

```python
op.add_column('knowledge_bases', sa.Column('procrastinate_job_id', sa.BigInteger(), nullable=True))
op.create_index(op.f('ix_knowledge_bases_procrastinate_job_id'), 'knowledge_bases', ['procrastinate_job_id'])
op.create_foreign_key(
    'fk_knowledge_bases_procrastinate_job_id', 'knowledge_bases', 'procrastinate_jobs',
    ['procrastinate_job_id'], ['id'], ondelete='SET NULL',
)
```

`ondelete="SET NULL"` matters: Procrastinate prunes old jobs, and a `RESTRICT`/default
FK would either block pruning or cascade a delete into your domain table.

**Commit the domain row before deferring.** In `knowledge_base_routes.py:303` the
upload row is committed, *then* the job is deferred, then the job id is written back.
Defer first and the worker can start — and fail on a missing row — before your
transaction commits.

---

## Step 5 — Run the worker

Local:

```bash
PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app worker
```

Production, from `build/kubernetes/staging-aws/worker/deployment.yaml` — same image as
the API, different command:

```yaml
command:
  - python
  - "-m"
  - procrastinate
  - "--app=core.services.ingestion_queue.app"
  - worker
  - "--name=$(POD_NAME)"
  - "--queues=ingestion,pod_sync"
  - "--concurrency=1"
  - "--no-listen-notify"
  - "--fetch-job-polling-interval=5"
```

Why each flag:

- `--name=$(POD_NAME)` — from the downward API. Shows up in `procrastinate_workers` and
  in logs, so you can tell which pod holds a stuck job.
- `--queues=…` — subscribe explicitly. Omitting it consumes every queue, including ones
  added later by someone else.
- `--concurrency=1` — ingestion is CPU-bound (Docling); parallel jobs in one pod just
  thrash. Scale with replicas, not concurrency, for CPU-bound work. Raise it for
  IO-bound tasks.
- `--no-listen-notify` + `--fetch-job-polling-interval=5` — poll every 5s instead of
  holding a `LISTEN` connection. Required with connection poolers (PgBouncer in
  transaction mode, Neon's pooled endpoint) where LISTEN/NOTIFY silently never fires.
  On a direct Postgres connection, drop both and get instant pickup.

Deployment shape:

- `strategy: Recreate` and `terminationGracePeriodSeconds: 120` — let an in-flight job
  finish before the pod dies rather than running two workers mid-rollout.
- Thread caps (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `DOCLING_NUM_THREADS = 2`) —
  BLAS defaults to one thread per core and will blow the CPU limit.
- `serviceAccountName: tone-worker` + `rbac.yaml` — only because `pod_sync` calls the
  Kubernetes API. A pure ingestion worker needs no ServiceAccount.
- `replicas: 0` is the committed default here; scale up per environment.

---

## Step 6 — Periodic jobs

Stack `@app.periodic` above `@app.task`:

```python
@app.periodic(cron="* * * * *")
@app.task(name="sync_pods_and_nodes", queue="pod_sync")
def sync_pods_and_nodes_task(timestamp: int) -> None:
    from core.jobs.pod_sync import sync_pods_and_nodes

    sync_pods_and_nodes()
```

Decorator order is fixed — `@app.periodic` must be outermost. The function **must**
accept a `timestamp: int` argument; Procrastinate passes the schedule tick and errors
without it. Deferral is deduplicated through `procrastinate_periodic_defers`, so running
N worker replicas still produces one job per tick — no leader election needed.

A periodic task only fires while a worker subscribed to its queue is running. With
`replicas: 0`, nothing schedules — ticks are skipped, not backfilled.

---

## Step 7 — Expose job status (optional)

Procrastinate has no ORM models of its own. `core/models/procrastinate.py` declares
read-only SQLAlchemy models over its tables so the API can join job status into
responses:

```python
ProcrastinateBase = declarative_base()


class ProcrastinateJob(ProcrastinateBase):
    __tablename__ = "procrastinate_jobs"

    id = Column(BigInteger, primary_key=True)
    queue_name = Column(String(128), nullable=False)
    task_name = Column(String(128), nullable=False)
    status = Column(String, nullable=False, default="todo")
    attempts = Column(Integer, nullable=False, default=0)
    ...

    @property
    def is_finished(self) -> bool:
        return self.status in ("succeeded", "failed", "cancelled", "aborted")
```

Note the **separate declarative base**. These models mirror tables Procrastinate owns;
putting them on the app's main `Base` would put them back in Alembic's autogenerate
target and undo the `include_object` guard. Read through them — never write.

Job statuses: `todo` → `doing` → `succeeded` | `failed` | `cancelled` | `aborted`.

---

## Recreating this in a new project — checklist

1. Add `procrastinate`, `psycopg[binary]`, `psycopg-pool` and pin them.
2. Create one module holding `app = App(connector=PsycopgConnector(conninfo=...))`;
   strip the SQLAlchemy dialect prefix from the URL.
3. Define tasks with an explicit `name=` and a dedicated `queue=`; import heavy deps
   inside the function body.
4. Install the schema — Alembic migration (preferred) or `schema --apply`.
5. Add the `include_object` guard to `alembic/env.py` **before** the next autogenerate.
6. Enqueue with `await task.defer_async(...)` inside `async with app.open_async()`;
   store the returned job id with an `ondelete="SET NULL"` FK.
7. Run a worker process with explicit `--queues` and a `--name`; add
   `--no-listen-notify --fetch-job-polling-interval=5` if the DB sits behind a pooler.
8. Add `@app.periodic(cron=...)` tasks with a `timestamp: int` parameter if needed.
9. Optionally declare read-only ORM models on their own `declarative_base()`.

---

## Gotchas

| Symptom | Cause |
|---|---|
| Worker error-loops on a missing table | Schema step never ran on this DB. Apply it per environment. |
| Next autogenerated migration drops the queue | `include_object` guard missing from `alembic/env.py`. |
| Connector refuses the URL | `DATABASE_URL` still carries `+psycopg2` / `+psycopg`. |
| Jobs queue but never start | No worker subscribed to that queue — check `--queues` and `replicas`. |
| Jobs picked up minutes late | LISTEN/NOTIFY swallowed by a pooler; use polling. |
| Periodic task never fires | Missing `timestamp: int` param, wrong decorator order, or no worker on that queue. |
| Worker OOMs or exceeds CPU limit | BLAS thread defaults; cap `OMP_NUM_THREADS` and friends. |
| Job runs before its data exists | Deferred inside the transaction that creates the row — commit first. |
