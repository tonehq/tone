"""Pre-computed per-call aggregate stats for the metrics-summary endpoint.

For a completed call we take its ``turn_metrics`` array and, for each of
four series (LLM TTFB, STT TTFB, TTS TTFB, end-to-end latency), compute a
two-step aggregation:

1. **Per-turn** — for each turn, ``avg``/``p50``/``p99`` over that turn's
   positive samples of the series' source key.
2. **Across-turn** — for each of those three per-turn lists, compute
   ``avg``/``p50``/``p99``.

The result is a 3×3 grid — outer key = per-turn stat, inner key =
across-turn stat — plus a ``unit`` scalar. Persisting this per call
lets ``CallMetricsAnalyticsService`` roll up across many calls without
re-walking every turn on every request.

The end-to-end series is a scalar per turn (not an array). Its per-turn
"avg", "p50", "p99" all collapse to that single value, so the resulting
3×3 grid has three distinct across-turn stats repeated across all three
outer keys — expected and intentional.

A series with no positive samples yields ``None`` for the whole block
(stored as ``null`` in JSONB). The reader treats that as "no data".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.services.call_metrics_service import _avg, _percentile, _positive

# Ordered so the JSONB rendering matches the frontend's expected order
# (avg first, then percentiles) at both nesting levels.
_STAT_OPS = (
    ("avg", _avg),
    ("p50", lambda vs: _percentile(vs, 0.50)),
    ("p99", lambda vs: _percentile(vs, 0.99)),
)

# ``computed_stats`` JSONB key, source key on each turn dict, scale factor
# (seconds → response unit), unit label, and whether the source is an
# array of samples (True for TTFB) or a single scalar (False for end_to_end).
_SERIES = (
    ("llm_series_stats",        "llm_ttfb_all", 1000.0, "ms", True),
    ("stt_series_stats",        "stt_ttfb_all", 1000.0, "ms", True),
    ("tts_series_stats",        "tts_ttfb_all", 1000.0, "ms", True),
    ("end_to_end_series_stats", "end_to_end",   1.0,    "s",  False),
)


def compute_series_stats(turn_metrics: Optional[List[dict]]) -> Dict[str, Optional[dict]]:
    """Return the four per-series 3×3 stat blocks for a call's turn_metrics.

    Missing/empty ``turn_metrics`` yields ``None`` for every series so the
    caller can merge the result verbatim into ``computed_stats`` and the
    read path sees "no data" instead of a zero.
    """
    turns = turn_metrics if isinstance(turn_metrics, list) else []
    return {
        stats_key: _series_stats(turns, source_key, scale, unit, is_array)
        for stats_key, source_key, scale, unit, is_array in _SERIES
    }


def _series_stats(
    turns: List[dict],
    source_key: str,
    scale: float,
    unit: str,
    is_array: bool,
) -> Optional[Dict[str, Any]]:
    per_turn_stats: Dict[str, List[float]] = {name: [] for name, _ in _STAT_OPS}

    for turn in turns:
        if not isinstance(turn, dict):
            continue
        scaled = _scaled_samples(turn.get(source_key), scale, is_array)
        if not scaled:
            continue
        for name, op in _STAT_OPS:
            value = op(scaled)
            if value is not None:
                per_turn_stats[name].append(value)

    if not per_turn_stats["avg"]:
        return None

    return {
        "unit": unit,
        **{
            outer: {inner: inner_op(per_turn_stats[outer]) for inner, inner_op in _STAT_OPS}
            for outer, _ in _STAT_OPS
        },
    }


def _scaled_samples(raw: Any, scale: float, is_array: bool) -> List[float]:
    """Return positive samples scaled into the response unit.

    Scaling before running avg/percentile keeps the 3-decimal rounding
    those helpers apply in the response unit — otherwise seconds-scale
    values would silently drop sub-millisecond precision on the way to ms.
    """
    if is_array:
        source = raw if isinstance(raw, list) else []
        return [v * scale for v in _positive(source)]
    if isinstance(raw, (int, float)) and raw > 0:
        return [raw * scale]
    return []


# Keys of the four blocks — public so callers merging into ``computed_stats``
# and the read-path fallback stay in sync with the compute path.
SERIES_STAT_KEYS = tuple(spec[0] for spec in _SERIES)
