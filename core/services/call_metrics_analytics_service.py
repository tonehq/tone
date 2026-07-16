"""Nested-aggregate metrics for the "Show Metrics" view in Call History.

Given the same filter scope the user is looking at (date range + facets),
compute a **two-step** aggregation for each of four series:

1. **Per-call stats** — for each call in scope, compute that call's own
   ``avg``, ``p50`` and ``p99`` over its positive per-turn values.
2. **Across-call stats** — take each of the three per-call series (list of
   per-call avgs, list of per-call p50s, list of per-call p99s) and compute
   ``avg``, ``p50``, ``p99`` over that list.

The result per series is a 3×3 grid — three per-call rows × three
aggregation columns — describing not just "how bad was latency" but "how
bad was it *per call*" and "how consistent was that across calls". The
grid is symmetric and self-describing so the frontend can render it with a
generic table.

Applied identically to LLM TTFB, STT TTFB, TTS TTFB and end-to-end
(user→bot) latency. No per-metric special-casing — the collection function
just changes which JSONB key it pulls out.

**Data source**: per-turn values come from ``call_metrics.turn_metrics``
(already split by service by ``MetricsCollectorProcessor``). Rows without
``turn_metrics`` (legacy calls) contribute nothing and are excluded from
``calls_with_metrics``. A per-series ``call_sample_count`` further reports
how many calls contributed at least one positive sample for that specific
series — useful because a call may have LLM TTFB but no STT TTFB, for
example.
"""

from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.call_metrics import CallMetrics
from core.services.base import BaseService
from core.services.call_metrics_service import _avg, _percentile, _positive
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

# Series descriptor: which JSONB key to pull off each turn, the response
# key the frontend uses, and the scale factor to convert on-disk seconds
# into the response unit ("ms" for TTFB, "s" for latency).
_SERIES = (
    {"source_key": "llm_ttfb",   "response_key": "llm_ttfb",           "unit": "ms", "scale": 1000.0},
    {"source_key": "stt_ttfb",   "response_key": "stt_ttfb",           "unit": "ms", "scale": 1000.0},
    {"source_key": "tts_ttfb",   "response_key": "tts_ttfb",           "unit": "ms", "scale": 1000.0},
    {"source_key": "end_to_end", "response_key": "end_to_end_latency", "unit": "s",  "scale": 1.0},
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

        # One row per filtered call. turn_metrics is NULL for calls without
        # a metrics record (outer join) or for legacy calls persisted before
        # the column existed — both are handled by _summarize_series.
        rows = (
            call_svc.filtered_calls_query(start_date_time, end_date_time, filters)
            .with_entities(CallMetrics.turn_metrics)
            .all()
        )
        call_count = len(rows)
        turn_metrics_rows = [row[0] for row in rows if row[0]]
        calls_with_metrics = len(turn_metrics_rows)

        series_response: Dict[str, Dict[str, Any]] = {}
        for spec in _SERIES:
            series_response[spec["response_key"]] = _summarize_series(
                turn_metrics_rows, spec["source_key"], spec["scale"], spec["unit"]
            )

        return {
            "call_count": call_count,
            "calls_with_metrics": calls_with_metrics,
            "series": series_response,
        }


# ---------------------------------------------------------------------------
# Aggregation primitives
# ---------------------------------------------------------------------------

def _summarize_series(
    turn_metrics_rows: Iterable[List[Dict[str, Any]]],
    source_key: str,
    scale: float,
    unit: str,
) -> Dict[str, Any]:
    """Nested aggregate for one series across all calls in scope.

    Step 1 → for each call, compute per-call ``avg``/``p50``/``p99`` over
    its positive turn values for ``source_key``.
    Step 2 → for each per-call stat, aggregate the list of per-call values
    into ``avg``/``p50``/``p99``.

    Returns the ``per_call`` grid keyed as ``per_call[<row>][<col>]`` where
    row is the per-call stat (avg/p50/p99) and column is the across-call
    aggregate (avg/p50/p99). A call with no positive samples contributes
    nothing to the series (its per-call stats would be null); the
    ``call_sample_count`` reflects only calls that did contribute.
    """
    per_call_stats: Dict[str, List[float]] = {name: [] for name, _ in _STAT_OPS}

    for turns in turn_metrics_rows:
        if not isinstance(turns, list):
            continue
        raw = [turn.get(source_key) for turn in turns if isinstance(turn, dict)]
        # Scale before stat-computing so the 3-decimal rounding inside _avg /
        # _percentile is applied in the response unit — otherwise TTFB math in
        # seconds would silently drop sub-ms precision on the way to ms.
        scaled = [v * scale for v in _positive(raw)]
        if not scaled:
            continue
        for name, op in _STAT_OPS:
            value = op(scaled)
            if value is not None:
                per_call_stats[name].append(value)

    return {
        "unit": unit,
        "call_sample_count": len(per_call_stats["avg"]),
        "per_call": {
            row_name: {col_name: col_op(per_call_stats[row_name]) for col_name, col_op in _STAT_OPS}
            for row_name, _ in _STAT_OPS
        },
    }
