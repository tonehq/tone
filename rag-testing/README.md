# RAG Evaluation Suite

Reusable evaluation harness for the Tone RAG pipeline. For each knowledge-base document, this suite:

1. **Generates** a Q&A dataset with an LLM (positive, negative, ambiguous, out-of-scope, edge cases).
2. **Runs** each question through the *real* production retrieval path (rebuilds the embedder + vector store from the ingestion pipeline run under test), asks an LLM to answer *only* from the retrieved context, and scores the answer with an LLM-as-judge.
3. **Records** every run in Postgres (`evals` + `eval_results` tables) so regressions across pipeline changes (parser, tokeniser, embedder, top-K) are diff-able and org-scoped.

Both retrieval quality **and** answer grounding are scored — a hallucinated answer that "sounds right" fails on `groundedness`, a good LLM answer over a bad retrieval fails on `retrieval_hit`. That split tells you *where* to look when something breaks.

## Auto-run (the default path)

Every successful ingestion enqueues a Procrastinate `eval_ingestion_run` task at the end of `IngestionRunService.complete_run`. The worker:

1. `EvalService.get_or_generate_eval(upload_id, org_id)` — upserts the `evals` row (unique per upload; regeneration replaces in-place).
2. `EvalService.run_eval(eval_id, ingestion_run_id, triggered_by="auto")` — retrieval uses the same embedder + vector store that the ingestion run used, so query and stored vectors are guaranteed compatible.

Failures are logged with a full traceback and swallowed — a broken eval must never fail the ingestion. Disable via `EVAL_AUTO_RUN_ENABLED=false`.

## Storage

- **`evals`** — one row per upload (`UNIQUE(upload_id)`). Holds the Q&A set (`questions` JSONB), the generator model, and a prompt hash for audit.
- **`eval_results`** — one row per run of an eval. Includes `summary` + `per_question` JSONB, `run_number` auto-incremented per eval, and `ingestion_run_id` FK'd to the specific pipeline recipe under test. Query by `ingestion_run_id` to answer "did this recipe regress vs. the previous one?".

The CLI wrappers all persist through `EvalService`; there are no filesystem `questions.json` / `run-*.json` files anymore. Old files under `documents/<slug>/` can be deleted.

---

## Layout

```
rag-testing/
  README.md                       ← you are here
  documents/
    <doc-slug>/
      source.pdf                  ← original file (pulled from R2 by bootstrap_from_db.py)
      metadata.json               ← {upload_id, org_id, source_file, ingested_at}
  prompts/
    question_generation.md
    answer_from_context.md
    judge_correctness.md
  scripts/
    run_all.py                    ← ONE COMMAND: does everything below (recommended)
    common.py
    bootstrap_from_db.py          ← auto-register every KB in the DB, pull source from R2
    validate_ingestion.py         ← programmatic ingestion check (chunks + embeddings)
    generate_questions.py         ← EvalService.generate_eval wrapper
    run_eval.py                   ← EvalService.run_eval wrapper
    compare_runs.py               ← EvalService.compare_* wrapper
```

## The one command

```bash
python rag-testing/scripts/run_all.py
```

For every active KB in the DB, this runs the full chain in order:

1. Register in `rag-testing/documents/<slug>/` and write `metadata.json`
2. Download the source file from R2 into `source.<ext>`
3. Validate ingestion (status, chunks, embeddings, dim, non-zero) — skips this doc if invalid
4. Generate the eval (persists `evals` row in Postgres)
5. Run the eval against the active ingestion run (persists `eval_results` row)

**Idempotent** — any KB that already has a ready `evals` row AND an `eval_results` row for its active ingestion run is skipped. Add `--rerun` to force reprocessing.

Useful flags:
```bash
python rag-testing/scripts/run_all.py --kb-id <uuid>         # target one KB by knowledge_bases.id
python rag-testing/scripts/run_all.py --upload-id <uuid>     # target one KB by uploads.id
python rag-testing/scripts/run_all.py --doc <slug>           # target one KB by folder slug
python rag-testing/scripts/run_all.py --skip-eval            # bootstrap + Q&A only (skip eval)
python rag-testing/scripts/run_all.py --no-download          # don't pull from R2 (expect source already placed)
python rag-testing/scripts/run_all.py --rerun                # force reprocess a fully-processed doc
```

---

## Step-by-step workflow

### 1. Upload the doc (through the app UI or `POST /api/v1/knowledge-base`)

That's the only *fully* manual step. Everything below is scripted.

### 2. Bootstrap folders + download source files from R2

```bash
python rag-testing/scripts/bootstrap_from_db.py --write --download-source
```

Creates `rag-testing/documents/<slug>/metadata.json` (slug = `<kb-name>-<upload-id[:8]>`) and pulls the file via `R2StorageService`. Idempotent — folders that already have `questions.json`-era artefacts are left alone; use `--rerun` to force.

### 3. Programmatically validate ingestion

```bash
python rag-testing/scripts/validate_ingestion.py --doc <slug>
# or across every KB:
python rag-testing/scripts/validate_ingestion.py --all
```

Asserts: `knowledge_bases.status='ready'`, `uploads.status='ready'`, chunk count > 0, no NULL embeddings, embedding dim = 1536, no zero-vector embeddings. Exit code non-zero if any check fails.

### 4. Generate the Q&A dataset

```bash
python rag-testing/scripts/generate_questions.py --doc <slug>
python rag-testing/scripts/generate_questions.py --doc <slug> --model gpt-4o --max-chars 60000 --force
```

Persists to the `evals` table via `EvalService.generate_eval`. `--force` regenerates in-place.

### 5. Run the eval

```bash
python rag-testing/scripts/run_eval.py --doc <slug>
python rag-testing/scripts/run_eval.py --all
python rag-testing/scripts/run_eval.py --doc <slug> --top-k 8 --answer-model gpt-4o --judge-model gpt-4o
```

Persists to `eval_results`. `triggered_by="cli"` distinguishes CLI runs from `auto` (worker) and `manual` (future UI-triggered) runs.

### 6. Track regressions

```bash
python rag-testing/scripts/compare_runs.py --doc <slug>
# or pin specific eval_results.id values:
python rag-testing/scripts/compare_runs.py --baseline <id> --candidate <id>
# tighten the regression threshold:
python rag-testing/scripts/compare_runs.py --doc <slug> --score-drop 0.10
```

Exit code non-zero if any regression is detected: verdict downgrade (`PASS→FAIL`), `retrieval_hit` flip Y→N, or a score drop ≥ threshold on `correctness` / `groundedness`.

---

## What each metric means

| Metric | Meaning | Failure mode it catches |
|---|---|---|
| `retrieval_hit` | Did the expected source snippet appear (fuzzy) in the retrieved chunks? | Retrieval-side: wrong chunk, wrong ranking, embedding drift |
| `judge.correctness` | Does the actual answer convey the same meaning as the expected answer? | Wrong facts, wrong direction |
| `judge.groundedness` | Is every claim in the answer supported by the retrieved chunks? | **Hallucinations** |
| `judge.relevance` | Does the answer address the question at all? | Off-topic / evasive |
| `judge.verdict` | Bucketed `PASS`/`PARTIAL`/`FAIL` from the three axes | Overall gate |

**Diagnosing a failure**: if `retrieval_hit = false`, the problem is upstream (chunker/embedder/top-K). If `retrieval_hit = true` but `groundedness` is low, the LLM is hallucinating over correctly retrieved context. If both are fine but `correctness` is low, the expected answer or the question is wrong.

---

## Configuration

All eval knobs live in `shared/config.py` (loaded from env / Infisical):

| Setting | Default | Purpose |
|---|---|---|
| `EVAL_AUTO_RUN_ENABLED` | `true` | Kill switch for the post-ingestion Procrastinate task |
| `EVAL_GENERATION_MODEL` | `gpt-4o` | Question-generation LLM |
| `EVAL_ANSWER_MODEL` | `gpt-4o` | Grounded-answer LLM |
| `EVAL_JUDGE_MODEL` | `gpt-4o` | LLM-as-judge |
| `EVAL_TOP_K` | `8` | Chunks to retrieve per question |
| `EVAL_MAX_CONTEXT_CHARS` | `60000` | Doc truncation before question generation |

---

## Reused primitives (nothing re-implemented)

| Purpose | Source |
|---|---|
| Persistence | `EvalService` — `core/services/evals/eval_service.py` |
| Embedder pinned to the run under test | `build_embedder_from_run` — `core/services/rag/embedder_factory.py` |
| Vector store lookup | `get_vector_store` — `core/services/rag/factory.py` |
| Vector search + filters | `PgVectorStore.query(filters={"ingestion_run_id": …})` — `core/services/rag/vector_stores/pgvector_store.py` |
| Provider key (LLM + embedder) | `ProviderKeyService.require_key` — `core/services/rag/provider_keys.py` |
| Document text extraction | `CompositeReader.read()` — `core/services/rag/readers.py` |
| Source file bytes | `R2StorageService().download_file()` — `core/services/r2_storage_service.py` |
| Active ingestion run lookup | `IngestionRunService.get_active_run` — `core/services/ingestion_run_service.py` |
| Async job queue | `enqueue_eval_for_ingestion_run` — `core/services/ingestion_queue.py` |

No new HTTP routes; API endpoints on top of `EvalService` are a follow-up when a UI needs them.

---

## Prereqs

- Python env with the project's `requirements.txt` installed.
- OpenAI API key stored in the DB via `api_keys` for the target org (`ProviderKeyService.get_key(org_id, "openai")`), NOT `.env`.
- Local DB reachable and Alembic migrated (`alembic upgrade head`).
- Procrastinate worker consuming BOTH the `ingestion` and `eval` queues for auto-run to fire end-to-end:
  ```
  python -m procrastinate --app=core.services.ingestion_queue.app worker \
      --queues=ingestion,eval,pod_sync,outbound_calls
  ```
  Eval work runs on its own `eval` queue (isolated from ingestion so a slow LLM run can't starve ingest slots, and an older worker deployment that doesn't yet know the eval task can't grab and fail the job). You can also run a separate worker deployment with `--queues=eval` if you want to scale eval capacity independently.

---

## Not in scope (yet)

- HTTP endpoints for eval CRUD (`POST /evals/generate`, `GET /evals/{id}/results`, …). Callers use the service directly.
- UI dashboard for eval results.
- Backfill of pre-existing filesystem `questions.json` / `run-*.json` files into DB — leave the old files or delete them.
- CI gating on `pass_rate` — the data is now in Postgres, wiring a CI check on top is a follow-up.
- Per-question `eval_question_results` child table — `per_question` JSONB is enough today; normalise if per-question analytics become the primary query pattern.
