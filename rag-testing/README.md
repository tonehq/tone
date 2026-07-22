# RAG Evaluation Suite

Reusable evaluation harness for the Tone RAG pipeline. For each knowledge-base document, this suite:

1. **Generates** a Q&A dataset with an LLM (positive, negative, ambiguous, out-of-scope, edge cases).
2. **Runs** each question through the *real* production retrieval path (`RAGPipeline.retrieve` → pgvector), asks an LLM to answer *only* from the retrieved context, and scores the answer with an LLM-as-judge.
3. **Records** timestamped per-run results so regressions across pipeline changes (embedding model, chunk size, top-K) are diff-able.

Retrieval quality **and** answer grounding are both scored — a hallucinated answer that "sounds right" fails on `groundedness`, and a good LLM answer over a bad retrieval fails on `retrieval_hit`. That split tells you *where* to look when something breaks.

Manual QA still owns upload / ingestion / chunking / embedding sanity (upload via UI, confirm `knowledge_bases.status = 'ready'` and chunks exist in `knowledge_base_chunks`). This suite kicks in *after* that.

---

## Layout

```
rag-testing/
  README.md                        ← you are here
  documents/
    <doc-slug>/
      source.pdf                   ← original file (.pdf | .md | .txt | .docx | .html)
      metadata.json                ← {upload_id, org_id, source_file, ingested_at}
      questions.json               ← LLM-generated Q&A (review + edit before committing)
      results/
        run-2026-07-22T14-05-32Z.json
  prompts/
    question_generation.md
    answer_from_context.md
    judge_correctness.md
  scripts/
    run_all.py                   ← ONE COMMAND: does everything below in order (recommended)
    common.py
    bootstrap_from_db.py         ← auto-register every KB in the DB
    validate_ingestion.py        ← programmatic ingestion check (chunks + embeddings)
    generate_questions.py        ← LLM → questions.json
    run_eval.py                  ← retrieval + answer + judge → results/
    compare_runs.py              ← diff two runs, flag regressions
    judge.py
```

## The one command

```bash
python rag-testing/scripts/run_all.py
```

For every active KB in the DB, this runs the full chain in order:

1. Register in `rag-testing/documents/<slug>/` and write `metadata.json`
2. Download the source file from R2 into `source.<ext>`
3. Validate ingestion (status, chunks, embeddings, dim, non-zero) — skips this doc if invalid
4. Generate `questions.json` with the LLM
5. Run the eval (retrieval + grounded answer + LLM judge) → `results/run-<ISO>.json`

**Idempotent** — any KB whose folder already has both `questions.json` AND at least one `results/run-*.json` is skipped entirely. Only *new* KBs get processed on subsequent runs. Add `--rerun` to force reprocessing.

Useful flags:
```bash
python rag-testing/scripts/run_all.py --kb-id <uuid>         # target one KB by knowledge_bases.id
python rag-testing/scripts/run_all.py --upload-id <uuid>     # target one KB by uploads.id
python rag-testing/scripts/run_all.py --doc <slug>           # target one KB by folder slug
python rag-testing/scripts/run_all.py --skip-eval            # bootstrap + Q&A only (skip eval)
python rag-testing/scripts/run_all.py --no-download          # don't pull from R2 (expect source already placed)
python rag-testing/scripts/run_all.py --rerun                # force reprocess a fully-processed doc
```
`--doc`, `--kb-id`, and `--upload-id` are mutually exclusive.

The step-by-step scripts below still exist for granular control (e.g., regenerating Q&A for one doc, comparing runs). Skip to them if you want to do a single stage manually.

---


---

## Workflow for a new document

### 1. Upload the doc (through the app UI or `POST /api/v1/knowledge-base`)

That's the only *fully* manual step. Everything below is scripted.

### 2. Auto-register every KB in the DB (and optionally pull the file from R2)

```bash
python rag-testing/scripts/bootstrap_from_db.py                         # dry run
python rag-testing/scripts/bootstrap_from_db.py --write                 # create metadata.json only
python rag-testing/scripts/bootstrap_from_db.py --write --download-source   # + auto-pull the file from R2
```

Scans `knowledge_bases` for every active row and creates `rag-testing/documents/<slug>/metadata.json` (slug = `<kb-name>-<upload-id[:8]>`). With `--download-source` it also uses `R2StorageService().download_file(...)` (the same call the ingestion worker uses) to write `documents/<slug>/source.<ext>` — no manual copy needed. Without the flag, the script prints which slugs still need a source file placed.

**Idempotency:** any doc that already has `questions.json` is treated as "already set up" and **skipped entirely** — its source is not re-downloaded and metadata is not touched. So you can safely rerun bootstrap after every new upload; only *new* KBs get processed. To force reprocessing an already-set-up doc, add `--rerun`.

### 3. Programmatically validate ingestion

```bash
python rag-testing/scripts/validate_ingestion.py --doc <slug>
# or across every KB in the DB:
python rag-testing/scripts/validate_ingestion.py --all
```

Asserts: `knowledge_bases.status='ready'`, `uploads.status='ready'`, chunk count > 0, no NULL embeddings, embedding dim = 1536, no zero-vector embeddings. Exits non-zero if anything fails — CI-safe.

### 4. Generate the Q&A dataset

```bash
python rag-testing/scripts/generate_questions.py --doc <doc-slug>
# options: --model gpt-4o | --max-chars 60000 | --force
```

This writes `rag-testing/documents/<doc-slug>/questions.json`. **Open it and review.** Prune weak questions, tighten expected answers, add hand-authored edge cases. Commit the reviewed file.

### 5. Run the eval

```bash
python rag-testing/scripts/run_eval.py --doc <doc-slug>

# or across every ingested doc (after a pipeline change):
python rag-testing/scripts/run_eval.py --all

# tuning:
python rag-testing/scripts/run_eval.py --doc <doc-slug> \
    --top-k 8 --answer-model gpt-4o --judge-model gpt-4o
```

The runner prints a per-question line and a summary block, then writes `documents/<doc-slug>/results/run-<timestamp>.json`.

### 6. Track regressions

Every run writes a timestamped `results/run-<ISO>.json`. Compare the latest two runs of a doc:

```bash
python rag-testing/scripts/compare_runs.py --doc <slug>

# or pin explicit files:
python rag-testing/scripts/compare_runs.py \
    --baseline rag-testing/documents/<slug>/results/run-<old>.json \
    --candidate rag-testing/documents/<slug>/results/run-<new>.json

# tighten the regression threshold:
python rag-testing/scripts/compare_runs.py --doc <slug> --score-drop 0.10
```

Exits non-zero if any regression is detected: verdict downgrade (`PASS→FAIL`), `retrieval_hit` flip Y→N, or a score drop ≥ threshold on `correctness` / `groundedness`. Wire this into a nightly job to catch drift.

---

## What each metric means

| Metric | Meaning | Failure mode it catches |
|---|---|---|
| `retrieval_hit` | Did the expected source snippet appear (fuzzy) in the retrieved chunks? | Retrieval-side: wrong chunk, wrong ranking, embedding drift |
| `judge.correctness` | Does the actual answer convey the same meaning as the expected answer? | Wrong facts, wrong direction |
| `judge.groundedness` | Is every claim in the answer supported by the retrieved chunks? | **Hallucinations** |
| `judge.relevance` | Does the answer address the question at all? | Off-topic / evasive |
| `judge.verdict` | Bucketed `PASS`/`PARTIAL`/`FAIL` from the three axes | Overall gate |

**Diagnosing a failure**: if `retrieval_hit = false`, the problem is upstream (chunker/embedder/top-K). If `retrieval_hit = true` but `groundedness` is low, the LLM is hallucinating over correctly retrieved context. If both are fine but `correctness` is low, the expected answer or the question is wrong (revisit `questions.json`).

---

## Question categories (produced by the generator)

- **factual** — direct lookup; `expected_source_snippet` is a literal substring of the doc.
- **negative** — plausible question about info NOT in the doc; expected answer is exactly `"not in the provided documents"`.
- **ambiguous** — under-specified; expected answer describes the ambiguity or lists candidates.
- **out-of-scope** — adjacent domain but not in this doc; treated like `negative`.
- **edge** — multi-hop / requires synthesis across ≥ 2 passages.

The generator is instructed to produce at least: 6 factual, 3 negative, 2 ambiguous, 2 out-of-scope, 2 edge.

---

## Reused primitives (nothing re-implemented)

| Purpose | Source |
|---|---|
| Retrieval | `RAGPipeline.retrieve()` — `core/services/rag/pipeline.py` |
| Vector search + filters | `PgVectorStore.query(filters={"upload_id": …})` — `core/services/rag/vector_stores/pgvector_store.py` |
| Embedder (matches prod) | `OpenAIEmbedder` — `core/services/rag/embedders.py` |
| Document text extraction | `CompositeReader.read_path()` — `core/services/rag/readers.py` |
| Settings & API keys | `shared.config.settings` |
| DB session | `core.database.session.SessionLocal` |

No new services, no new HTTP routes, no new models.

---

## Prereqs

- Python env with the project's `requirements.txt` installed (same env used to run the backend).
- `OPENAI_API_KEY` available via `shared.config.settings` (Infisical) or the `.env` file — same key the ingestion worker uses.
- Local DB reachable from the script (the runner opens a session via `SessionLocal`).

---

## Not in scope (yet)

- CI gating on `pass_rate` — add once a stable baseline exists per doc.
- Ingestion / chunking / embedding validation — owned by manual QA (upload docs, inspect DB + Procrastinate worker logs).
- Voice-call end-to-end (Twilio + STT + LLM + TTS) — separate suite; this one isolates retrieval + synthesis.
