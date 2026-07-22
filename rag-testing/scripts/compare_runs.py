"""Compare two eval runs and flag regressions.

Given two `run-*.json` files (or a --doc slug that auto-picks the latest two),
prints a diff:
  * per-question verdict transitions (PASS → FAIL, etc.)
  * retrieval_hit flips
  * score deltas (correctness / groundedness / relevance)
  * summary-level deltas (pass_rate, hit_rate)

Exit code: 0 if no regressions, 1 if any regression detected.

Usage:
    python rag-testing/scripts/compare_runs.py --doc <slug>
    python rag-testing/scripts/compare_runs.py --baseline <path> --candidate <path>
    python rag-testing/scripts/compare_runs.py --doc <slug> --score-drop 0.15
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import doc_dir

_VERDICT_RANK = {"FAIL": 0, "PARTIAL": 1, "PASS": 2}


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def _latest_two(doc_slug: str) -> tuple[Path, Path]:
    results_dir = doc_dir(doc_slug) / "results"
    if not results_dir.exists():
        raise FileNotFoundError(f"{results_dir} does not exist")
    runs = sorted(results_dir.glob("run-*.json"))
    if len(runs) < 2:
        raise RuntimeError(
            f"Need at least 2 run files under {results_dir}; found {len(runs)}."
        )
    return runs[-2], runs[-1]


def _index_by_id(rows: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in rows}


def _delta_str(new: float, old: float) -> str:
    d = new - old
    return f"{d:+.2f}"


def _compare(baseline: dict, candidate: dict, *, score_drop: float) -> int:
    """Return number of regressions detected."""
    b_rows = _index_by_id(baseline.get("results", []))
    c_rows = _index_by_id(candidate.get("results", []))

    baseline_ts = baseline.get("run_at", "?")
    candidate_ts = candidate.get("run_at", "?")
    print(f"[compare] baseline  {baseline_ts}")
    print(f"[compare] candidate {candidate_ts}")

    bs, cs = baseline.get("summary", {}), candidate.get("summary", {})
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

    regressions = 0
    all_ids = sorted(set(b_rows) | set(c_rows))
    if not all_ids:
        print("[compare] no rows in either run.")
        return 0

    print("\n[per-question deltas]")
    header = f"  {'id':6s} {'base':10s} {'cand':10s} {'hit(b→c)':10s}  Δcorr  Δgnd  Δrel  note"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for qid in all_ids:
        b = b_rows.get(qid)
        c = c_rows.get(qid)
        if b is None:
            print(f"  {qid:6s} {'—':10s} {c['judge']['verdict']:10s}  (new question)")
            continue
        if c is None:
            regressions += 1
            print(f"  {qid:6s} {b['judge']['verdict']:10s} {'—':10s}  (missing in candidate) ← regression")
            continue

        b_v = b["judge"]["verdict"]
        c_v = c["judge"]["verdict"]
        b_hit = b.get("retrieval_hit", False)
        c_hit = c.get("retrieval_hit", False)
        d_corr = c["judge"]["correctness"] - b["judge"]["correctness"]
        d_gnd = c["judge"]["groundedness"] - b["judge"]["groundedness"]
        d_rel = c["judge"]["relevance"] - b["judge"]["relevance"]

        note = ""
        is_regression = False
        if _VERDICT_RANK[c_v] < _VERDICT_RANK[b_v]:
            note = f"verdict regression {b_v}→{c_v}"
            is_regression = True
        elif b_hit and not c_hit:
            note = "retrieval_hit dropped"
            is_regression = True
        elif d_corr <= -score_drop:
            note = f"correctness drop {d_corr:+.2f}"
            is_regression = True
        elif d_gnd <= -score_drop:
            note = f"groundedness drop {d_gnd:+.2f}"
            is_regression = True

        if is_regression:
            regressions += 1

        marker = "!" if is_regression else " "
        print(
            f" {marker}{qid:6s} {b_v:10s} {c_v:10s} "
            f"{('Y' if b_hit else 'N')}→{('Y' if c_hit else 'N'):<7s} "
            f"{_delta_str(c['judge']['correctness'], b['judge']['correctness'])} "
            f"{_delta_str(c['judge']['groundedness'], b['judge']['groundedness'])} "
            f"{_delta_str(c['judge']['relevance'], b['judge']['relevance'])}  "
            f"{note}"
        )

    print(f"\n[compare] {regressions} regression(s)")
    return regressions


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff two RAG eval runs and flag regressions.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc", help="Slug — auto-pick the latest two run files")
    g.add_argument("--baseline", help="Path to the baseline run-*.json")
    ap.add_argument("--candidate", help="Path to the candidate run-*.json (paired with --baseline)")
    ap.add_argument(
        "--score-drop",
        type=float,
        default=0.15,
        help="Absolute drop in a judge metric that counts as a regression",
    )
    args = ap.parse_args()

    if args.doc:
        baseline_path, candidate_path = _latest_two(args.doc)
    else:
        if not args.candidate:
            print("--baseline requires --candidate", file=sys.stderr)
            return 2
        baseline_path = Path(args.baseline)
        candidate_path = Path(args.candidate)

    baseline = _load(baseline_path)
    candidate = _load(candidate_path)
    regressions = _compare(baseline, candidate, score_drop=args.score_drop)
    return 0 if regressions == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
