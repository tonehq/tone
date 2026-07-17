"""Nested-aggregate metrics for the "Show Metrics" view in Call History.

Given the same filter scope the user is looking at (date range + facets),
compute a **two-step** aggregation for each of four series:

1. **Per-call stats** — for each call in scope, take that call's own
   ``call_metrics.<series>_series_stats`` block (pre-computed at
   call-end by ``ComputeCallAggregatesAction``) and pick the diagonal
   ``block[<row>][<row>]`` as the canonical per-call scalar for that
   row — the ``<row>``-across-turns of the per-turn ``<row>`` stat. In
   the single-sample-per-turn case (the common case), this collapses to
   ``<row>`` over the call's per-turn headline values, matching what
   the pre-refactor endpoint reported.
2. **Across-call stats** — take each of the three per-call series (list
   of per-call avgs, list of per-call p50s, list of per-call p99s) and
   compute ``avg``, ``p50``, ``p99`` over that list.

The result per series is a 3×3 grid — three per-call rows × three
aggregation columns — describing not just "how bad was latency" but "how
bad was it *per call*" and "how consistent was that across calls". The
grid is symmetric and self-describing so the frontend can render it with
a generic table.

Applied identically to LLM TTFB, STT TTFB, TTS TTFB and end-to-end
(user→bot) latency. Per-metric behavior lives entirely in the source
``_SERIES`` table on the compute side; the roll-up here is metric-agnostic.

**Data source**: prefers the pre-computed per-call blocks in the four
``call_metrics.*_series_stats`` columns. Rows without them (legacy
calls persisted before this change, or a race where the aggregate job
hasn't run yet) fall back to computing the block inline from
``turn_metrics``, so the endpoint stays correct without a blocking
backfill.
"""

from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.call_metrics import CallMetrics
from core.services.base import BaseService
from core.services.call_metrics_aggregates import compute_series_stats
from core.services.call_metrics_service import _avg, _percentile
from core.services.call_service import CallService

# The three stat operators used at BOTH levels (per-call and across-calls),
# in the order the frontend renders them (avg first, then percentiles). A
# single tuple drives compute + response shape so adding/removing a stat
# is a one-line change and both levels stay in sync.
_STAT_OPS = (
    ("avg", _avg),
    ("p50", lambda vs: _percentile(vs, 0.50)),
    ("p99", lambda vs: _percentile(vs, 0.99)),
)

# Response descriptor: the frontend-facing key, the JSONB key under
# ``computed_stats`` where the per-call block lives, and the constant
# unit label reported in the response. ``unit`` is fixed per series
# (not derived from data) so an empty filter still reports a real unit
# string instead of ``null``, which the frontend renders in the axis
# labels regardless of sample count.
_SERIES = (
    {"response_key": "llm_ttfb",           "stats_key": "llm_series_stats",        "unit": "ms"},
    {"response_key": "stt_ttfb",           "stats_key": "stt_series_stats",        "unit": "ms"},
    {"response_key": "tts_ttfb",           "stats_key": "tts_series_stats",        "unit": "ms"},
    {"response_key": "end_to_end_latency", "stats_key": "end_to_end_series_stats", "unit": "s"},
)


class CallMetricsAnalyticsService(BaseService):
    """2-step nested aggregation over a filter scope."""

    def __init__(self, db: Session, user_id: Optional[UUID] = None, org_id: Optional[UUID] = None):
        super().__init__(db, user_id, org_id)

    def summarize(
        self,
        start_date_time: Optional[str] = None,
        end_date_time: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Compute the nested aggregation for every series.

        Filter scope matches ``CallService.get_calls`` exactly (via
        :meth:`CallService.filtered_calls_query`), so what the user sees
        in the table and what these numbers describe are the same set of
        calls.
        """
        call_svc = CallService(self.db, org_id=self.org_id)

        # Select the four series columns in ``_SERIES`` order followed by
        # ``turn_metrics`` (the fallback source). Driving the projection
        # off ``_SERIES`` guarantees the tuple positions ``_resolve_blocks``
        # reads match this order even if a series is added or reordered.
        # Every ``*_series_stats`` column is NULL for calls without a
        # metrics record (outer join) or for calls persisted before the
        # aggregate job ran — both are handled downstream.
        series_columns = [getattr(CallMetrics, spec["stats_key"]) for spec in _SERIES]
        rows = (
            call_svc.filtered_calls_query(start_date_time, end_date_time, filters)
            .with_entities(*series_columns, CallMetrics.turn_metrics)
            .all()
        )
        call_count = len(rows)
        per_call_blocks = [_resolve_blocks(row) for row in rows]
        calls_with_metrics = sum(1 for blocks in per_call_blocks if blocks)

        series_response: Dict[str, Dict[str, Any]] = {}
        for spec in _SERIES:
            series_response[spec["response_key"]] = _summarize_series(
                per_call_blocks, spec["stats_key"], spec["unit"]
            )

        return {
            "call_count": call_count,
            "calls_with_metrics": calls_with_metrics,
            "series": series_response,
        }


# ---------------------------------------------------------------------------
# Aggregation primitives
# ---------------------------------------------------------------------------

def _resolve_blocks(row: Any) -> Optional[Dict[str, Any]]:
    """Return the four per-series blocks for one call, or ``None`` if none.

    ``row`` is the SQLAlchemy result tuple in ``_SERIES`` order followed
    by ``turn_metrics`` — see the ``with_entities`` call in ``summarize``.
    Prefers the four persisted columns; falls back to an inline compute
    for calls that don't have them yet (legacy row, or aggregate job
    hasn't run yet) so no blocking backfill is required. Returns
    ``None`` only when the call has neither persisted stats nor any
    usable ``turn_metrics`` — those calls contribute to no series and
    shouldn't inflate ``calls_with_metrics``.
    """
    persisted = {spec["stats_key"]: row[i] for i, spec in enumerate(_SERIES)}
    if any(value is not None for value in persisted.values()):
        return persisted
    turn_metrics = row[len(_SERIES)]
    if turn_metrics:
        return compute_series_stats(turn_metrics)
    return None


def _summarize_series(
    per_call_blocks: Iterable[Optional[Dict[str, Any]]],
    stats_key: str,
    unit: str,
) -> Dict[str, Any]:
    """Across-call roll-up for one series.

    Frontend contract (see ``callLog.ts::MetricsSummarySeries``):
    ``per_call[R][C] = C-across-calls applied to the list of per-call R``.
    So we need one "per-call R" scalar per call before applying C.

    The per-call block is a 3×3 grid: ``block[outer][inner]`` = ``inner``
    applied across turns to per-turn ``outer``. The **diagonal**
    ``block[R][R]`` is the natural per-call R: for each turn compute R
    over that turn's samples, then take R over the resulting per-turn
    values. In the common single-sample-per-turn case (where a turn's
    ``*_ttfb_all`` reduces to its scalar headline), the diagonal collapses
    to ``R(turn_scalars)`` — exactly what the pre-change endpoint reported
    when it read ``llm_ttfb``/``stt_ttfb``/``tts_ttfb``/``end_to_end``
    directly. Off-diagonal cells would break that equivalence: e.g. reading
    ``block[R]["avg"]`` makes every row collapse to the call's mean in the
    single-sample case, which is a real regression against the old numbers.

    A call whose block is missing this series (``None``) contributes
    nothing; ``call_sample_count`` reflects only calls that did.
    """
    per_call_stats: Dict[str, List[float]] = {name: [] for name, _ in _STAT_OPS}

    for blocks in per_call_blocks:
        if not blocks:
            continue
        series_block = blocks.get(stats_key)
        if not series_block:
            continue
        for row_name, _ in _STAT_OPS:
            row = series_block.get(row_name)
            if not row:
                continue
            value = row.get(row_name)
            if value is not None:
                per_call_stats[row_name].append(value)

    return {
        "unit": unit,
        "call_sample_count": len(per_call_stats["avg"]),
        "per_call": {
            row_name: {col_name: col_op(per_call_stats[row_name]) for col_name, col_op in _STAT_OPS}
            for row_name, _ in _STAT_OPS
        },
    }
