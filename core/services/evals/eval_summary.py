"""Pure roll-up / diff helpers for RAG eval runs.

Extracted verbatim from ``eval_service.py`` so the summary-aggregation and
run-comparison responsibilities live apart from the ~1200-line ``EvalService``
orchestrator (SRP). These functions are pure: scored-row ``dict``/``list`` in,
plain ``dict`` out — no DB session, no models, no ``EvalService`` state — so
they are safe to reuse from any caller and trivially unit-testable.

``EvalService`` imports ``_summarize_scored_rows`` / ``_diff_scored_rows`` (and
``_DEEPEVAL_SUMMARY_METRICS``, which its own query/summary helpers also read)
back under the same names, so no call site changed — this is a pure relocation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:  # annotation only — lazy under ``from __future__ import annotations``
    from core.services.evals.eval_service import EvalRunSummary


_VERDICT_RANK = {"FAIL": 0, "PARTIAL": 1, "PASS": 2}

# DeepEval metrics we surface in per-run summaries (SQL AVG over the JSONB
# scorecard) and in the compare view's per-question deltas. ``correctness``
# is intentionally omitted — it already flows through the mapped
# ``correctness`` column and its avg is exposed as ``avg_correctness``.
_DEEPEVAL_SUMMARY_METRICS: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "contextual_precision",
    "contextual_recall",
    "contextual_relevancy",
    "hallucination",
)

# Legacy summary keys derived from the mapped columns — the per-scorecard
# aggregation loop skips these names so it can't overwrite them with a
# semantically different value pulled from the DeepEval scorecard.
_LEGACY_AVG_KEYS: frozenset[str] = frozenset({"correctness", "groundedness", "relevance"})

# Metrics where a HIGHER score is WORSE (DeepEval's hallucination fraction).
# Regression semantics for these are inverted: a positive delta (more
# hallucination) is a regression, a negative delta (less hallucination) is
# an improvement.
_INVERTED_SUMMARY_METRICS: frozenset[str] = frozenset({"hallucination"})


def _summarize_scored_rows(rows: List[dict]) -> dict:
    """Roll up the in-memory scored-row list — used at the tail of ``run_eval``
    so the returned ``EvalRunSummary`` carries the same summary payload the
    CLI used to read off ``result.summary``.

    Averages ``avg_<metric>`` are emitted for every DeepEval metric that
    appears in at least one row's ``judge.metric_scores``; legacy
    ``avg_correctness``/``avg_groundedness``/``avg_relevance`` keep working
    off the mapped columns so pre-DeepEval consumers see no change.
    """
    total = len(rows)
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    hit_count = 0
    corr_sum = 0.0
    gnd_sum = 0.0
    rel_sum = 0.0
    latency_sum = 0
    by_category: dict = {}
    # Per-DeepEval-metric aggregates. Denominator is per-metric so a metric
    # that only appears on some rows doesn't get diluted by rows that
    # skipped it (legacy-judge rows carry no scorecard).
    metric_sums: dict[str, float] = {}
    metric_counts: dict[str, int] = {}

    for r in rows:
        judge = r.get("judge") or {}
        v = judge.get("verdict", "FAIL")
        counts[v] = counts.get(v, 0) + 1
        if r.get("retrieval_hit"):
            hit_count += 1
        corr_sum += float(judge.get("correctness", 0) or 0)
        gnd_sum += float(judge.get("groundedness", 0) or 0)
        rel_sum += float(judge.get("relevance", 0) or 0)
        latency_sum += int(r.get("latency_ms", 0) or 0)
        for name, entry in (judge.get("metric_scores") or {}).items():
            if not isinstance(entry, dict):
                continue
            # Skip names that would clobber the mapped-column averages
            # computed above — ``avg_correctness`` etc. must stay derived
            # from the same source as their ``EvalResult`` column to keep
            # trends comparable across engine flips.
            if name in _LEGACY_AVG_KEYS:
                continue
            score = entry.get("score")
            if score is None:
                continue
            metric_sums[name] = metric_sums.get(name, 0.0) + float(score)
            metric_counts[name] = metric_counts.get(name, 0) + 1
        cat = r.get("category") or "unknown"
        c = by_category.setdefault(
            cat, {"total": 0, "PASS": 0, "PARTIAL": 0, "FAIL": 0, "hits": 0}
        )
        c["total"] += 1
        c[v] = c.get(v, 0) + 1
        if r.get("retrieval_hit"):
            c["hits"] += 1

    summary = {
        "total": total,
        "pass": counts["PASS"],
        "partial": counts["PARTIAL"],
        "fail": counts["FAIL"],
        "pass_rate": (counts["PASS"] / total) if total else 0.0,
        "partial_rate": (counts["PARTIAL"] / total) if total else 0.0,
        "fail_rate": (counts["FAIL"] / total) if total else 0.0,
        "retrieval_hit_rate": (hit_count / total) if total else 0.0,
        "avg_correctness": (corr_sum / total) if total else 0.0,
        "avg_groundedness": (gnd_sum / total) if total else 0.0,
        "avg_relevance": (rel_sum / total) if total else 0.0,
        "total_questions": total,
        "duration_ms": latency_sum,
        "by_category": by_category,
    }
    for name, sum_ in metric_sums.items():
        cnt = metric_counts.get(name, 0)
        summary[f"avg_{name}"] = (sum_ / cnt) if cnt else 0.0
    return summary


def _diff_scored_rows(
    *,
    baseline_summary: "EvalRunSummary",
    candidate_summary: "EvalRunSummary",
    baseline_rows: List[dict],
    candidate_rows: List[dict],
    score_drop: float,
) -> dict:
    """Compare two runs' per-question rows. Output shape mirrors the
    pre-refactor helper so ``compare_runs.py`` needs no template changes."""
    b_rows = _index_by_id(baseline_rows)
    c_rows = _index_by_id(candidate_rows)
    all_ids = sorted(set(b_rows) | set(c_rows))

    per_question_diff: List[dict] = []
    regressions: List[dict] = []
    for qid in all_ids:
        b = b_rows.get(qid)
        c = c_rows.get(qid)
        if b is None:
            per_question_diff.append({"id": qid, "kind": "new", "candidate": c["judge"]["verdict"]})
            continue
        if c is None:
            entry = {"id": qid, "kind": "missing", "baseline": b["judge"]["verdict"]}
            per_question_diff.append(entry)
            regressions.append(entry)
            continue

        b_v = b["judge"]["verdict"]
        c_v = c["judge"]["verdict"]
        b_hit = bool(b.get("retrieval_hit"))
        c_hit = bool(c.get("retrieval_hit"))
        d_corr = c["judge"]["correctness"] - b["judge"]["correctness"]
        d_gnd = c["judge"]["groundedness"] - b["judge"]["groundedness"]
        d_rel = c["judge"]["relevance"] - b["judge"]["relevance"]

        # Per-DeepEval-metric deltas from the JSONB scorecard. Only emitted
        # when BOTH runs actually scored the metric — comparing a real
        # score to a missing/legacy row would coerce ``None → 0.0`` and
        # trigger a spurious "big drop" regression on every question.
        b_scores = (b["judge"].get("metric_scores") or {}) if isinstance(b["judge"], dict) else {}
        c_scores = (c["judge"].get("metric_scores") or {}) if isinstance(c["judge"], dict) else {}
        metric_deltas: dict[str, float] = {}
        for metric_name in _DEEPEVAL_SUMMARY_METRICS:
            b_entry = b_scores.get(metric_name)
            c_entry = c_scores.get(metric_name)
            b_raw = b_entry.get("score") if isinstance(b_entry, dict) else None
            c_raw = c_entry.get("score") if isinstance(c_entry, dict) else None
            if b_raw is None or c_raw is None:
                continue
            metric_deltas[metric_name] = _safe_score(c_raw) - _safe_score(b_raw)

        note = None
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
        else:
            # A big drop on any DeepEval metric — even one not mapped to a
            # legacy column — is still a regression the compare view should
            # surface. Hallucination is inverted (higher = worse), so a
            # positive delta above the threshold is the regression signal.
            for metric_name, delta in metric_deltas.items():
                if metric_name in _INVERTED_SUMMARY_METRICS:
                    if delta >= score_drop:
                        note = f"{metric_name} rose {delta:+.2f}"
                        is_regression = True
                        break
                elif delta <= -score_drop:
                    note = f"{metric_name} drop {delta:+.2f}"
                    is_regression = True
                    break

        entry = {
            "id": qid,
            "baseline_verdict": b_v,
            "candidate_verdict": c_v,
            "baseline_hit": b_hit,
            "candidate_hit": c_hit,
            "delta_correctness": d_corr,
            "delta_groundedness": d_gnd,
            "delta_relevance": d_rel,
            "regression": is_regression,
            "note": note,
        }
        for metric_name, delta in metric_deltas.items():
            entry[f"delta_{metric_name}"] = delta
        per_question_diff.append(entry)
        if is_regression:
            regressions.append(entry)

    return {
        "baseline": {
            "id": str(baseline_summary.run_id),
            "run_number": baseline_summary.run_number,
            "started_at": baseline_summary.started_at.isoformat() if baseline_summary.started_at else None,
            "summary": baseline_summary.summary or {},
        },
        "candidate": {
            "id": str(candidate_summary.run_id),
            "run_number": candidate_summary.run_number,
            "started_at": candidate_summary.started_at.isoformat() if candidate_summary.started_at else None,
            "summary": candidate_summary.summary or {},
        },
        "score_drop_threshold": score_drop,
        "regressions": regressions,
        "regression_count": len(regressions),
        "per_question": per_question_diff,
    }


def _index_by_id(rows: List[dict]) -> dict:
    return {r["id"]: r for r in rows if isinstance(r, dict) and "id" in r}


def _safe_score(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
