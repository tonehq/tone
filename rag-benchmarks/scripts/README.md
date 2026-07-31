# RAG benchmark dataset population

Two CLIs live here:

| Script | Purpose |
|---|---|
| `download_datasets.py` | Populate `rag-benchmarks/<key>/{docs/,qa.jsonl}` from upstream (Plan 2). |
| `import_dataset.py` | Push a populated dataset through the KB pipeline + auto-eval (Plan 1). |

## First run

```bash
cd rag-benchmarks/scripts
pip install -r requirements.txt
python download_datasets.py                 # all 4 datasets, ~35 MB total
python download_datasets.py --dataset tatqa-mini    # just one
python download_datasets.py --force         # re-download / overwrite
```

Datasets populated:

| Key | Questions | Docs | Category | Source |
|---|---|---|---|---|
| `hotpotqa-mini` | 100 | ~100 `.txt` | `multi-hop` | HF `hotpot_qa` (distractor / validation) |
| `ragbench-emanual` | 100 | 1 synthesized `.txt` | `manual` | HF `rungalileo/ragbench` subset `emanual` |
| `tatqa-mini` | 100 | ≤100 `.txt` (contexts) | `finance-table` | Raw GitHub JSON (TAT-QA dev) |
| `openragbench-arxiv-mini` | 50 | ≤~15 `.pdf` (or `.txt` fallback) | `scientific-pdf` | HF `vectara/open_ragbench` (arXiv slice) |

## Determinism

- Every fetcher takes the FIRST N rows in dataset-native order — no shuffling.
- IDs are index-derived (e.g. `hpq-042`, `tat-0007`), so re-runs write byte-identical `qa.jsonl`.
- Doc filenames are slugified deterministically (`slugify` is lowercase / ASCII / `_`).

If you need to change output, edit the fetcher — do NOT hand-edit `qa.jsonl`; the next `--force` run will clobber your edits.

## qa.jsonl schema (must match Plan 1 plumbing)

```json
{ "id": "hpq-000",
  "doc_filename": "return_of_the_king.txt",
  "category": "multi-hop",
  "question": "…",
  "expected_answer": "…",
  "expected_source_snippet": "…" }
```

`expected_source_snippet` may be an empty string but is never omitted (the eval scorer reads it unconditionally). `doc_filename` MUST match a file in `docs/`.

## After populating: run the benchmark

```bash
# From repo root, with the API's Procrastinate worker running:
python rag-benchmarks/scripts/import_dataset.py hotpotqa-mini
python rag-benchmarks/scripts/import_dataset.py ragbench-emanual
python rag-benchmarks/scripts/import_dataset.py tatqa-mini
python rag-benchmarks/scripts/import_dataset.py openragbench-arxiv-mini
```

For each doc: `Upload` + `KnowledgeBase` are created, a gold `evals` row is pre-seeded (`status="ready"`), and ingestion is enqueued. The existing `eval_ingestion_run` auto-task short-circuits on `ready` — no LLM question generation — and scores against the gold Q&A into `eval_results`.

## Matrix runs (comparing models)

After the initial import, kick a second ingestion with different embedder/parser/LLM:

```
POST /api/v1/knowledge-base/{upload_id}/runs
{ "embedding_provider": "voyage", "embedding_model": "voyage-3", "vector_store": "pgvector" }
```

Auto-eval reuses the SAME gold Q&A → a fresh `eval_results` row lands under the new `ingestion_pipeline_run`.

## Troubleshooting

- **`load_dataset(...)` 404 or config error**: HF configs / splits do drift. Each fetcher isolates its lookup logic (`_load_ragbench_split`, `_load_openragbench_arxiv`) and tries a small candidate list before giving up. Edit that list, don't paper over it at the call site.
- **HotpotQA is slow to load**: HF caches to `~/.cache/huggingface`. Subsequent runs read from cache.
- **`vectara/open_ragbench` PDF download fails**: the fetcher falls back to writing the passage text as `.txt` so the eval still runs, just with lossier documents. `du -sh rag-benchmarks/openragbench-arxiv-mini/docs` will tell you which case you hit.
- **Total footprint > 35 MB**: check whether `openragbench-arxiv-mini` actually fetched PDFs (they can be 1-3 MB each) vs. text fallbacks.
