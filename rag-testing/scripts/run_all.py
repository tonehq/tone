"""One-command RAG evaluation pipeline.

For every active KnowledgeBase in the DB, this script:

  1. Registers it in `rag-testing/documents/<slug>/` (writes metadata.json)
  2. Downloads its source file from R2 (unless already present)
  3. Validates ingestion (chunks + embeddings + dim + non-zero) — skips this doc if invalid
  4. Generates the LLM Q&A dataset (`questions.json`)
  5. Runs the eval (retrieval + grounded answer + LLM judge) and writes a
     timestamped result file under `documents/<slug>/results/`

Idempotency: a doc is considered "fully processed" when its folder has both
`questions.json` AND at least one `results/run-*.json`. Those are skipped
entirely unless `--rerun` is passed.

Usage:
    python rag-testing/scripts/run_all.py                     # process every new KB, run eval
    python rag-testing/scripts/run_all.py --kb-id <uuid>      # limit to a single KB (knowledge_bases.id)
    python rag-testing/scripts/run_all.py --upload-id <uuid>  # limit to a single upload (uploads.id)
    python rag-testing/scripts/run_all.py --doc <slug>        # limit to one doc by folder slug
    python rag-testing/scripts/run_all.py --no-download       # skip R2 download (expect source already placed)
    python rag-testing/scripts/run_all.py --skip-eval         # bootstrap + generate Q&A only, no eval
    python rag-testing/scripts/run_all.py --rerun             # force reprocess even if fully done
    python rag-testing/scripts/run_all.py --top-k 8 --answer-model gpt-4o --judge-model gpt-4o
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bootstrap_from_db import _discover, _download_source, _slugify, _write_metadata
from common import DOCS_DIR, db_session, write_questions
from generate_questions import generate as generate_questions
from run_eval import _run_one_doc
from validate_ingestion import _print_result, _validate_one


def _has_questions(folder: Path) -> bool:
    return (folder / "questions.json").exists()


def _has_results(folder: Path) -> bool:
    results = folder / "results"
    return results.exists() and any(results.glob("run-*.json"))


def _process_one(
    entry: dict,
    *,
    download_source: bool,
    overwrite_metadata: bool,
    skip_eval: bool,
    rerun: bool,
    top_k: int,
    answer_model: str,
    judge_model: str,
    gen_model: str,
    max_chars: int,
) -> str:
    """Returns a short status string for the summary table."""
    slug = _slugify(entry["kb_name"] or "kb", entry["upload_id"])
    folder = DOCS_DIR / slug

    fully_done = _has_questions(folder) and _has_results(folder)
    if fully_done and not rerun:
        print(f"\n=== {slug} — SKIP (already fully processed) ===")
        return "skipped"

    print(f"\n=== {slug} ===")
    print(f"  kb_name={entry['kb_name']!r}  upload_id={entry['upload_id']}")

    # 1. metadata + source
    _, folder, action = _write_metadata(entry, overwrite=overwrite_metadata or rerun)
    print(f"  [1/4] bootstrap: {action}")
    if download_source:
        dl = _download_source(entry, folder, overwrite=rerun)
        print(f"        R2: {dl}")
        if dl.startswith("R2 download failed") or dl == "no file_path in DB":
            return "download_failed"
    else:
        if not any(folder.glob("source.*")):
            print("  [!] no source file in folder and --no-download set — cannot generate Q&A")
            return "no_source"

    # 2. ingestion check
    with db_session() as db:
        validation = _validate_one(db, entry["upload_id"])
    print("  [2/4] ingestion validation:")
    _print_result(validation)
    if not validation.passed:
        return "ingestion_invalid"

    # 3. question generation (skip if already present unless --rerun)
    if _has_questions(folder) and not rerun:
        print("  [3/4] questions.json already present — reusing")
    else:
        try:
            payload = generate_questions(slug, model=gen_model, max_chars=max_chars)
            write_questions(slug, payload)
            print(f"  [3/4] generated {len(payload['questions'])} question(s)")
        except Exception as e:
            print(f"  [3/4] question generation FAILED: {type(e).__name__}: {e}")
            return "qgen_failed"

    # 4. run the eval
    if skip_eval:
        print("  [4/4] eval skipped (--skip-eval)")
        return "eval_skipped"
    try:
        _run_one_doc(
            doc_slug=slug,
            top_k=top_k,
            answer_model=answer_model,
            judge_model=judge_model,
        )
        return "eval_ran"
    except Exception as e:
        print(f"  [4/4] eval FAILED: {type(e).__name__}: {e}")
        return "eval_failed"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-shot: bootstrap → download → validate → generate Q&A → eval, for every KB."
    )
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--doc", help="Limit to a single doc by folder slug")
    scope.add_argument("--kb-id", help="Limit to a single KB by knowledge_bases.id (UUID)")
    scope.add_argument("--upload-id", help="Limit to a single KB by uploads.id (UUID)")
    ap.add_argument(
        "--no-download",
        action="store_true",
        help="Do not pull source files from R2; expect them already placed",
    )
    ap.add_argument(
        "--overwrite-metadata",
        action="store_true",
        help="Overwrite existing metadata.json (default: leave existing)",
    )
    ap.add_argument(
        "--skip-eval",
        action="store_true",
        help="Only bootstrap + generate Q&A; do not run the eval",
    )
    ap.add_argument(
        "--rerun",
        action="store_true",
        help="Reprocess even docs that are already fully processed",
    )
    ap.add_argument("--top-k", type=int, default=8, help="Chunks to retrieve per question")
    ap.add_argument("--answer-model", default="gpt-4o", help="Model for grounded answer generation")
    ap.add_argument("--judge-model", default="gpt-4o", help="Model for LLM-as-judge")
    ap.add_argument("--gen-model", default="gpt-4o", help="Model for question generation")
    ap.add_argument(
        "--max-chars",
        type=int,
        default=60_000,
        help="Truncate document text to this many chars before Q&A generation",
    )
    args = ap.parse_args()

    with db_session() as db:
        entries = _discover(db)

    if not entries:
        print("No active knowledge_bases with an upload_id found in the DB.", file=sys.stderr)
        return 2

    if args.doc:
        matching = [
            e
            for e in entries
            if _slugify(e["kb_name"] or "kb", e["upload_id"]) == args.doc
        ]
        filter_desc = f"slug={args.doc!r}"
    elif args.kb_id:
        matching = [e for e in entries if e["kb_id"] == args.kb_id]
        filter_desc = f"kb_id={args.kb_id!r}"
    elif args.upload_id:
        matching = [e for e in entries if e["upload_id"] == args.upload_id]
        filter_desc = f"upload_id={args.upload_id!r}"
    else:
        matching = entries
        filter_desc = None

    if filter_desc:
        if not matching:
            print(f"[run_all] no active KB in DB matches {filter_desc}", file=sys.stderr)
            return 2
        entries = matching

    print(f"[run_all] {len(entries)} KB(s) discovered in DB")

    tally: dict[str, int] = {}
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

    failure_states = {
        "download_failed",
        "no_source",
        "ingestion_invalid",
        "qgen_failed",
        "eval_failed",
    }
    had_failures = any(tally.get(s, 0) > 0 for s in failure_states)
    return 1 if had_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
