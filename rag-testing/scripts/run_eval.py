"""CLI wrapper — run an eval for one KB upload (or every doc with metadata).

Persists into ``eval_results`` via ``EvalService.run_eval``. Retrieval is
pinned to the upload's currently-active ``ingestion_pipeline_run`` — the same
recipe that ingested the doc — so the query embedder matches the stored
vectors' embedder without additional configuration.

Usage:
    python rag-testing/scripts/run_eval.py --doc <slug>
    python rag-testing/scripts/run_eval.py --all
    python rag-testing/scripts/run_eval.py --doc <slug> --top-k 8 --answer-model gpt-4o --judge-model gpt-4o
"""
from __future__ import annotations

import argparse
import sys

from common import DocMetadata, db_session, list_all_docs


def _run_one(doc_slug: str, args) -> int:
    from core.services.evals.eval_service import EvalService
    from core.services.evals.errors import EvalNotFoundError
    from core.services.ingestion_run_service import IngestionRunService

    meta = DocMetadata.load(doc_slug)
    upload_id, org_id = meta.upload_id, meta.org_id
    if not org_id:
        print(f"[eval] {doc_slug} missing org_id in metadata.json", file=sys.stderr)
        return 1

    svc = EvalService()
    with db_session() as db:
        run = IngestionRunService.get_active_run(db, upload_id)
        if run is None:
            print(f"[eval] {doc_slug} has no active ingestion run", file=sys.stderr)
            return 1

        eval_set = svc.get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
        if eval_set is None:
            print(
                f"[eval] {doc_slug} has no eval. Run generate_questions.py first.",
                file=sys.stderr,
            )
            return 1

        try:
            result = svc.run_eval(
                db,
                upload_id=upload_id,
                ingestion_run_id=run.id,
                triggered_by="cli",
                top_k=args.top_k,
                answer_model=args.answer_model,
                judge_model=args.judge_model,
            )
        except EvalNotFoundError as e:
            print(f"[eval] {doc_slug} ERROR: {e}", file=sys.stderr)
            return 1

    if result.status != "completed":
        print(f"[eval] {doc_slug} run_number={result.run_number} FAILED: {result.error}", file=sys.stderr)
        return 1

    s = result.summary or {}
    print(
        f"[eval] {doc_slug} run_number={result.run_number} "
        f"total={s.get('total', 0)}  PASS={s.get('pass', 0)}  "
        f"PARTIAL={s.get('partial', 0)}  FAIL={s.get('fail', 0)}"
    )
    print(
        f"       pass_rate={s.get('pass_rate', 0):.2%}  "
        f"hit_rate={s.get('retrieval_hit_rate', 0):.2%}  "
        f"avg_corr={s.get('avg_correctness', 0):.2f}  "
        f"avg_gnd={s.get('avg_groundedness', 0):.2f}"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run RAG evaluation for one or all indexed docs.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc", help="Slug of a single doc under rag-testing/documents/")
    g.add_argument("--all", action="store_true", help="Run every doc with metadata.json")
    ap.add_argument("--top-k", type=int, default=None, help="Override EVAL_TOP_K")
    ap.add_argument("--answer-model", default=None, help="Override EVAL_ANSWER_MODEL")
    ap.add_argument("--judge-model", default=None, help="Override EVAL_JUDGE_MODEL")
    args = ap.parse_args()

    slugs = list_all_docs() if args.all else [args.doc]
    if not slugs:
        print("No docs with metadata.json found under rag-testing/documents/", file=sys.stderr)
        return 2

    exit_code = 0
    for slug in slugs:
        try:
            rc = _run_one(slug, args)
        except Exception as e:  # noqa: BLE001
            print(f"[eval] {slug} ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            rc = 1
        if rc != 0:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
