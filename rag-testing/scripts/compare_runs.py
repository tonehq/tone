"""CLI wrapper — diff the latest two ``eval_results`` runs for a doc (or two
specific results by id) and flag regressions.

Exit code: 0 if no regressions, 1 otherwise.

Usage:
    python rag-testing/scripts/compare_runs.py --doc <slug>
    python rag-testing/scripts/compare_runs.py --baseline <eval_result_id> --candidate <eval_result_id>
    python rag-testing/scripts/compare_runs.py --doc <slug> --score-drop 0.10
"""
from __future__ import annotations

import argparse
import sys

from common import DocMetadata, db_session


def _print_diff(diff: dict) -> None:
    b = diff["baseline"]
    c = diff["candidate"]
    bs = b.get("summary") or {}
    cs = c.get("summary") or {}
    print(f"[compare] baseline  run_number={b['run_number']}  {b['started_at']}")
    print(f"[compare] candidate run_number={c['run_number']}  {c['started_at']}")
    print(
        f"[summary] pass_rate  base={bs.get('pass_rate', 0):.2%} → "
        f"cand={cs.get('pass_rate', 0):.2%}"
    )
    print(
        f"[summary] hit_rate   base={bs.get('retrieval_hit_rate', 0):.2%} → "
        f"cand={cs.get('retrieval_hit_rate', 0):.2%}"
    )
    print(
        f"[summary] avg_gnd    base={bs.get('avg_groundedness', 0):.2f} → "
        f"cand={cs.get('avg_groundedness', 0):.2f}"
    )

    print("\n[per-question]")
    for row in diff["per_question"]:
        if row.get("kind") == "new":
            print(f"  {row['id']:6s} (new — candidate {row['candidate']})")
            continue
        if row.get("kind") == "missing":
            print(f"! {row['id']:6s} {row['baseline']:10s} → (missing in candidate)")
            continue
        marker = "!" if row["regression"] else " "
        print(
            f" {marker}{row['id']:6s} {row['baseline_verdict']:10s} {row['candidate_verdict']:10s} "
            f"hit={('Y' if row['baseline_hit'] else 'N')}→{('Y' if row['candidate_hit'] else 'N')} "
            f"Δcorr={row['delta_correctness']:+.2f} "
            f"Δgnd={row['delta_groundedness']:+.2f} "
            f"Δrel={row['delta_relevance']:+.2f}  "
            f"{row['note'] or ''}"
        )
    print(f"\n[compare] {diff['regression_count']} regression(s)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff two RAG eval runs and flag regressions.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc", help="Slug — auto-pick the latest two eval_results for this doc")
    g.add_argument("--baseline", help="Baseline eval_results.id (paired with --candidate)")
    ap.add_argument("--candidate", help="Candidate eval_results.id (paired with --baseline)")
    ap.add_argument(
        "--score-drop", type=float, default=0.15,
        help="Absolute drop in a judge metric that counts as a regression",
    )
    args = ap.parse_args()

    from core.services.evals.eval_service import EvalService

    svc = EvalService()
    with db_session() as db:
        if args.doc:
            meta = DocMetadata.load(args.doc)
            if not meta.org_id:
                print(f"[compare] {args.doc} missing org_id in metadata.json", file=sys.stderr)
                return 2
            eval_row = svc.get_eval_by_upload(
                db, upload_id=meta.upload_id, org_id=meta.org_id
            )
            if eval_row is None:
                print(f"[compare] {args.doc} has no eval row", file=sys.stderr)
                return 2
            diff = svc.compare_latest_two(db, eval_row.id, score_drop=args.score_drop)
        else:
            if not args.candidate:
                print("--baseline requires --candidate", file=sys.stderr)
                return 2
            diff = svc.compare_results(
                db, args.baseline, args.candidate, score_drop=args.score_drop
            )

    _print_diff(diff)
    return 0 if diff["regression_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
