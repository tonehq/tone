"""Unit tests for the per-call series-stat compute function.

Pure logic — no DB, no procrastinate. Run:
    pytest test-cases/test_call_metrics_aggregates.py -v -o "addopts="
"""

import pytest

from core.services.call_metrics_aggregates import (
    SERIES_STAT_KEYS,
    compute_series_stats,
)


# ---------------------------------------------------------------------------
# Fixture: two-turn synthetic call
# ---------------------------------------------------------------------------
#
# TTFB series carry per-service-call arrays in seconds. Values chosen so
# per-turn avg/p50/p99 land on distinct numbers, then across-turn stats
# on the mean of those numbers are easy to reason about by hand.
# end_to_end is a scalar per turn in seconds.
#
# Turn 1 llm scaled = [100, 300] → avg=200, p50=200, p99=100+200*0.99=298
# Turn 2 llm scaled = [200, 400] → avg=300, p50=300, p99=200+200*0.99=398
#
# Across turns, per-turn "avg" list = [200, 300] → avg=250 p50=250 p99=299
# Across turns, per-turn "p50" list = [200, 300] → avg=250 p50=250 p99=299
# Across turns, per-turn "p99" list = [298, 398] → avg=348 p50=348 p99=397

_TURN_METRICS = [
    {
        "turn": 1,
        "llm_ttfb_all": [0.1, 0.3],
        "stt_ttfb_all": [0.05],
        "tts_ttfb_all": [0.4, 0.6],
        "end_to_end":   1.0,
    },
    {
        "turn": 2,
        "llm_ttfb_all": [0.2, 0.4],
        "stt_ttfb_all": [0.1],
        "tts_ttfb_all": [0.5, 0.7],
        "end_to_end":   2.0,
    },
]


def _approx(actual, expected, tol=0.01):
    assert actual == pytest.approx(expected, abs=tol), (
        f"got {actual!r}, expected {expected!r}"
    )


class TestComputeSeriesStats:
    def test_returns_all_four_series_keys(self):
        result = compute_series_stats(_TURN_METRICS)
        assert set(result.keys()) == set(SERIES_STAT_KEYS)

    def test_llm_series_math(self):
        block = compute_series_stats(_TURN_METRICS)["llm_series_stats"]
        assert block["unit"] == "ms"
        # outer "avg" = across-turn stats of per-turn avg (200, 300 in ms)
        _approx(block["avg"]["avg"], 250)
        _approx(block["avg"]["p50"], 250)
        _approx(block["avg"]["p99"], 299)
        # outer "p50" = across-turn stats of per-turn p50 (200, 300)
        _approx(block["p50"]["avg"], 250)
        # outer "p99" = across-turn stats of per-turn p99 (298, 398)
        _approx(block["p99"]["avg"], 348)
        _approx(block["p99"]["p99"], 397)

    def test_end_to_end_grid_collapses(self):
        """A single scalar per turn → per-turn avg/p50/p99 all equal that scalar.

        Across turns, that gives the same three-number list for every outer
        key, so all three outer rows produce identical inner blocks. Called
        out in the plan as expected behavior — this test locks it in.
        """
        block = compute_series_stats(_TURN_METRICS)["end_to_end_series_stats"]
        assert block["unit"] == "s"
        assert block["avg"] == block["p50"] == block["p99"]
        _approx(block["avg"]["avg"], 1.5)
        _approx(block["avg"]["p50"], 1.5)
        _approx(block["avg"]["p99"], 1.99)

    def test_tts_unit_and_scaling(self):
        block = compute_series_stats(_TURN_METRICS)["tts_series_stats"]
        assert block["unit"] == "ms"
        # Turn 1: [400, 600] → avg=500 p99=598. Turn 2: [500, 700] → avg=600.
        _approx(block["avg"]["avg"], 550)
        _approx(block["p99"]["avg"], (598 + 698) / 2)


class TestNoDataCases:
    def test_none_input_returns_null_blocks(self):
        result = compute_series_stats(None)
        assert result == {key: None for key in SERIES_STAT_KEYS}

    def test_empty_list_returns_null_blocks(self):
        assert compute_series_stats([]) == {key: None for key in SERIES_STAT_KEYS}

    def test_all_zero_samples_drops_series(self):
        """Zeros are placeholder frames (see ``_positive``) — a series with
        no real samples must be ``None``, not a grid of zeros."""
        turns = [{"llm_ttfb_all": [0, 0], "stt_ttfb_all": [], "tts_ttfb_all": [None], "end_to_end": 0}]
        result = compute_series_stats(turns)
        assert result["llm_series_stats"] is None
        assert result["stt_series_stats"] is None
        assert result["tts_series_stats"] is None
        assert result["end_to_end_series_stats"] is None

    def test_partial_series_populated(self):
        """Only one series has real samples → the others stay null."""
        turns = [{"llm_ttfb_all": [0.1], "stt_ttfb_all": [], "tts_ttfb_all": [], "end_to_end": None}]
        result = compute_series_stats(turns)
        assert result["llm_series_stats"] is not None
        assert result["stt_series_stats"] is None
        assert result["tts_series_stats"] is None
        assert result["end_to_end_series_stats"] is None


class TestAnalyticsReader:
    """Pin the diagonal reader — regression guard for the "collapse to mean" bug.

    Frontend contract: ``per_call[R][C]`` = C-across-calls of per-call R.
    The reader must therefore pull ``block[R][R]`` (diagonal), not ``block[R]["avg"]``
    or any other off-diagonal cell. In the single-sample-per-turn case
    (headline-value only), this collapses to R over the call's turn scalars —
    the same number the pre-refactor endpoint reported.
    """

    def _summarize(self, per_call_blocks, stats_key, unit):
        from core.services.call_metrics_analytics_service import _summarize_series
        return _summarize_series(per_call_blocks, stats_key=stats_key, unit=unit)

    def _blocks_from(self, turns):
        return compute_series_stats(turns)

    def test_single_sample_per_turn_matches_old_semantics(self):
        # Two "calls" with single-sample-per-turn arrays. Old endpoint would have
        # computed R over the flat list of turn scalars per call.
        call_a = self._blocks_from([
            {"llm_ttfb_all": [0.100]},
            {"llm_ttfb_all": [0.300]},
        ])
        call_b = self._blocks_from([
            {"llm_ttfb_all": [0.200]},
            {"llm_ttfb_all": [0.400]},
        ])
        out = self._summarize([call_a, call_b], stats_key="llm_series_stats", unit="ms")

        # Old per-call "avg" = mean of turn samples: call_a=200, call_b=300
        # Old per-call "p50" = median: call_a=200, call_b=300
        # Old per-call "p99" = p99: call_a=100+200*0.99=298, call_b=200+200*0.99=398
        # Across-call avg / p50 / p99 of each per-call list:
        #   avg-row: [200,300] → avg=250,  p50=250,  p99=299
        #   p50-row: [200,300] → avg=250,  p50=250,  p99=299
        #   p99-row: [298,398] → avg=348,  p50=348,  p99=397
        _approx(out["per_call"]["avg"]["avg"], 250)
        _approx(out["per_call"]["avg"]["p50"], 250)
        _approx(out["per_call"]["p50"]["avg"], 250)  # would be 250 for any correct reducer
        _approx(out["per_call"]["p99"]["avg"], 348)  # ← THIS is the bug pin: would be 250 with the "avg" cell reducer
        _approx(out["per_call"]["p99"]["p99"], 397)

    def test_empty_scope_still_reports_unit(self):
        out = self._summarize([], stats_key="llm_series_stats", unit="ms")
        assert out["unit"] == "ms"
        assert out["call_sample_count"] == 0
        assert out["per_call"]["avg"]["avg"] is None


class TestMalformedInput:
    def test_non_dict_turn_ignored(self):
        turns = ["not-a-turn", None, {"llm_ttfb_all": [0.1]}]
        result = compute_series_stats(turns)
        assert result["llm_series_stats"] is not None

    def test_non_list_array_field_ignored(self):
        turns = [{"llm_ttfb_all": "oops"}, {"llm_ttfb_all": [0.1]}]
        result = compute_series_stats(turns)
        assert result["llm_series_stats"] is not None
        _approx(result["llm_series_stats"]["avg"]["avg"], 100)
