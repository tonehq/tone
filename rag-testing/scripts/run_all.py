"""One-command RAG evaluation orchestrator.

For every active KnowledgeBase in the DB:
  1. Register in `rag-testing/documents/<slug>/` (writes metadata.json)
  2. Download the source file from R2
  3. Validate ingestion (chunks + embeddings + dim + non-zero)
  4. Generate the Q&A dataset (persists into `evals`)
  5. Run the eval (persists into `eval_results`)

Idempotency (DB-backed): a doc is "fully processed" when it has a ready
``evals`` row AND at least one ``eval_results`` row for its active ingestion
run. Fully-processed docs are skipped unless ``--rerun`` is passed.

Usage:
    python rag-testing/scripts/run_all.py
    python rag-testing/scripts/run_all.py --doc <slug>
    python rag-testing/scripts/run_all.py --kb-id <uuid>
    python rag-testing/scripts/run_all.py --upload-id <uuid>
    python rag-testing/scripts/run_all.py --skip-eval        # bootstrap + Q&A only
    python rag-testing/scripts/run_all.py --rerun            # force reprocess
    python rag-testing/scripts/run_all.py --top-k 8 --answer-model gpt-4o --judge-model gpt-4o
"""
from __future__ import annotations

import argparse
import sys

from bootstrap_from_db import _discover, _download_source, _slugify, _write_metadata
from common import DOCS_DIR, db_session
from validate_ingestion import _print_result, _validate_one


def _has_ready_eval(db, upload_id, org_id) -> bool:
    from core.services.evals.eval_service import EvalService

    eval_row = EvalService().get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
    return eval_row is not None and eval_row.status == "ready"


def _has_results_for_active_run(db, upload_id) -> bool:
    from core.services.evals.eval_service import EvalService
    from core.services.ingestion_run_service import IngestionRunService

    run = IngestionRunService.get_active_run(db, upload_id)
    if run is None:
        return False
    return EvalService().latest_result_for_ingestion_run(db, run.id) is not None


def _process_one(
    entry: dict,
    *,
    download_source: bool,
    overwrite_metadata: bool,
    skip_eval: bool,
    rerun: bool,
    top_k,
    answer_model,
    judge_model,
    gen_model,
    max_chars,
) -> str:
    from core.services.evals.eval_service import EvalService
    from core.services.ingestion_run_service import IngestionRunService

    slug = _slugify(entry["kb_name"] or "kb", entry["upload_id"])
    folder = DOCS_DIR / slug
    upload_id, org_id = entry["upload_id"], entry["org_id"]

    if not rerun:
        with db_session() as db:
            done = _has_ready_eval(db, upload_id, org_id) and _has_results_for_active_run(db, upload_id)
        if done:
            print(f"\n=== {slug} — SKIP (already fully processed) ===")
            return "skipped"

    print(f"\n=== {slug} ===")
    print(f"  kb_name={entry['kb_name']!r}  upload_id={upload_id}")

    _, folder, action = _write_metadata(entry, overwrite=overwrite_metadata or rerun)
    print(f"  [1/4] bootstrap: {action}")
    if download_source:
        dl = _download_source(entry, folder, overwrite=rerun)
        print(f"        R2: {dl}")
        if dl.startswith("R2 download failed") or dl == "no file_path in DB":
            return "download_failed"
    elif not any(folder.glob("source.*")):
        print("  [!] no source file in folder and --no-download set — cannot generate Q&A")
        return "no_source"

    with db_session() as db:
        validation = _validate_one(db, upload_id)
    print("  [2/4] ingestion validation:")
    _print_result(validation)
    if not validation.passed:
        return "ingestion_invalid"

    svc = EvalService()
    try:
        with db_session() as db:
            existing = svc.get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
            if existing is not None and existing.status == "ready" and not rerun:
                print(f"  [3/4] eval {existing.id} already present ({existing.question_count} questions)")
                eval_row = existing
            else:
                eval_row = svc.generate_eval(
                    db, upload_id=upload_id, org_id=org_id,
                    model=gen_model, max_chars=max_chars,
                )
                print(f"  [3/4] generated {eval_row.question_count} question(s)")
    except Exception as e:  # noqa: BLE001
        print(f"  [3/4] question generation FAILED: {type(e).__name__}: {e}")
        return "qgen_failed"

    if skip_eval:
        print("  [4/4] eval skipped (--skip-eval)")
        return "eval_skipped"

    try:
        with db_session() as db:
            run = IngestionRunService.get_active_run(db, upload_id)
            if run is None:
                print("  [4/4] eval SKIPPED — no active ingestion run")
                return "eval_failed"
            result = svc.run_eval(
                db, eval_id=eval_row.id, ingestion_run_id=run.id,
                triggered_by="cli",
                top_k=top_k, answer_model=answer_model, judge_model=judge_model,
            )
    except Exception as e:  # noqa: BLE001
        print(f"  [4/4] eval FAILED: {type(e).__name__}: {e}")
        return "eval_failed"

    if result.status != "completed":
        print(f"  [4/4] eval FAILED: {result.error}")
        return "eval_failed"

    s = result.summary or {}
    print(
        f"  [4/4] eval ran run_number={result.run_number} "
        f"pass_rate={s.get('pass_rate', 0):.2%} hit_rate={s.get('retrieval_hit_rate', 0):.2%}"
    )
    return "eval_ran"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-shot: bootstrap → download → validate → generate Q&A → eval, for every KB."
    )
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--doc", help="Limit to a single doc by folder slug")
    scope.add_argument("--kb-id", help="Limit to a single KB by knowledge_bases.id (UUID)")
    scope.add_argument("--upload-id", help="Limit to a single KB by uploads.id (UUID)")
    ap.add_argument("--no-download", action="store_true", help="Do not pull source files from R2")
    ap.add_argument("--overwrite-metadata", action="store_true", help="Overwrite existing metadata.json")
    ap.add_argument("--skip-eval", action="store_true", help="Only bootstrap + generate Q&A; do not run the eval")
    ap.add_argument("--rerun", action="store_true", help="Reprocess even docs that are already fully processed")
    ap.add_argument("--top-k", type=int, default=None, help="Override EVAL_TOP_K")
    ap.add_argument("--answer-model", default=None, help="Override EVAL_ANSWER_MODEL")
    ap.add_argument("--judge-model", default=None, help="Override EVAL_JUDGE_MODEL")
    ap.add_argument("--gen-model", default=None, help="Override EVAL_GENERATION_MODEL")
    ap.add_argument("--max-chars", type=int, default=None, help="Override EVAL_MAX_CONTEXT_CHARS")
    args = ap.parse_args()

    with db_session() as db:
        entries = _discover(db)

    if not entries:
        print("No active knowledge_bases with an upload_id found in the DB.", file=sys.stderr)
        return 2

    if args.doc:
        matching = [e for e in entries if _slugify(e["kb_name"] or "kb", e["upload_id"]) == args.doc]
        filter_desc = f"slug={args.doc!r}"
    elif args.kb_id:
        matching = [e for e in entries if e["kb_id"] == args.kb_id]
        filter_desc = f"kb_id={args.kb_id!r}"
    elif args.upload_id:
        matching = [e for e in entries if e["upload_id"] == args.upload_id]
        filter_desc = f"upload_id={args.upload_id!r}"
    else:
        matching, filter_desc = entries, None

    if filter_desc:
        if not matching:
            print(f"[run_all] no active KB in DB matches {filter_desc}", file=sys.stderr)
            return 2
        entries = matching

    print(f"[run_all] {len(entries)} KB(s) discovered in DB")

    tally: dict = {}
    for entry in entries:
        status = _process_one(
            entry,
            download_source=not args.no_download,
            overwrite_metadata=args.overwrite_metadata,
            skip_eval=args.skip_eval,
            rerun=args.rerun,
            top_k=args.top_k,
            answer_model=args.answer_model,
            judge_model=args.judge_model,
            gen_model=args.gen_model,
            max_chars=args.max_chars,
        )
        tally[status] = tally.get(status, 0) + 1

    print("\n=== run_all summary ===")
    for status, n in sorted(tally.items()):
        print(f"  {status:20s} {n}")

    failure_states = {"download_failed", "no_source", "ingestion_invalid", "qgen_failed", "eval_failed"}
    return 1 if any(tally.get(s, 0) > 0 for s in failure_states) else 0


if __name__ == "__main__":
    raise SystemExit(main())
