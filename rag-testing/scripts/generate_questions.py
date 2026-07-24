"""CLI wrapper — generate (or regenerate) a Q&A dataset for one KB upload.

Persists into the ``evals`` Postgres table via ``EvalService.generate_eval``.
Resolves the upload from either ``--doc <slug>`` (reads local metadata.json,
produced by bootstrap_from_db.py) or ``--upload-id <uuid>`` directly.

Usage:
    python rag-testing/scripts/generate_questions.py --doc <slug>
    python rag-testing/scripts/generate_questions.py --upload-id <uuid> --org-id <uuid>
    python rag-testing/scripts/generate_questions.py --doc <slug> --model gpt-4o --max-chars 60000 --force
"""
from __future__ import annotations

import argparse
import sys

from common import DocMetadata, db_session


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a RAG eval Q&A set for one upload.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc", help="Slug matching rag-testing/documents/<slug>/")
    g.add_argument("--upload-id", help="Upload UUID (bypasses metadata.json)")
    ap.add_argument("--org-id", help="Organization UUID (required with --upload-id)")
    ap.add_argument("--model", default=None, help="Override EVAL_GENERATION_MODEL")
    ap.add_argument("--max-chars", type=int, default=None, help="Override EVAL_MAX_CONTEXT_CHARS")
    ap.add_argument("--force", action="store_true", help="Regenerate even if an eval already exists")
    args = ap.parse_args()

    if args.doc:
        meta = DocMetadata.load(args.doc)
        upload_id, org_id = meta.upload_id, meta.org_id
        if not org_id:
            print(
                f"[generate] metadata.json for {args.doc} has no org_id; "
                "rerun `bootstrap_from_db.py --write` to refresh.",
                file=sys.stderr,
            )
            return 2
    else:
        if not args.org_id:
            print("--upload-id requires --org-id", file=sys.stderr)
            return 2
        upload_id, org_id = args.upload_id, args.org_id

    from core.services.evals.eval_service import EvalService

    svc = EvalService()
    with db_session() as db:
        existing = svc.get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
        if existing is not None and existing.status == "ready" and not args.force:
            print(
                f"[generate] eval {existing.id} already exists for upload {upload_id} "
                f"({existing.question_count} questions). Use --force to regenerate.",
                file=sys.stderr,
            )
            return 2
        eval_row = svc.generate_eval(
            db,
            upload_id=upload_id,
            org_id=org_id,
            model=args.model,
            max_chars=args.max_chars,
        )

    print(
        f"[generate] eval={eval_row.id} upload={upload_id} "
        f"questions={eval_row.question_count} model={eval_row.generated_by_model}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
