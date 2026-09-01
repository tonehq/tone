"""Unit tests for the shared DeepEval verdict helpers
(``core/services/evals/deepeval/verdict.py``).

Also the regression guard for the inverted-metrics drift fix: ``bias`` and
``toxicity`` were missing from the RAG judge's ``_INVERTED_METRICS`` copy, so
their fallback verdict (when a metric didn't set ``.success``) was graded in the
wrong direction. All three judges now share ONE ``INVERTED_METRICS`` set.
"""

from types import SimpleNamespace

from core.services.evals.deepeval.verdict import (
    INVERTED_METRICS,
    to_float,
    verdict_for,
)


class TestToFloat:
    def test_coerces_numeric_and_string(self):
        assert to_float(0.5) == 0.5
        assert to_float("0.25") == 0.25

    def test_clamps_to_unit_interval(self):
        assert to_float(2.0) == 1.0
        assert to_float(-1.0) == 0.0

    def test_non_numeric_is_zero(self):
        assert to_float(None) == 0.0
        assert to_float("not-a-number") == 0.0


class TestVerdictFor:
    def test_trusts_success_when_set(self):
        # ``.success`` present → verdict comes straight from it, regardless of
        # score/threshold/direction.
        assert verdict_for("correctness", SimpleNamespace(success=True), 0.0) == "pass"
        assert verdict_for("correctness", SimpleNamespace(success=False), 1.0) == "fail"

    def test_fallback_normal_metric_uses_ge_threshold(self):
        m = SimpleNamespace(success=None, threshold=0.5)
        assert verdict_for("correctness", m, 0.6) == "pass"
        assert verdict_for("correctness", m, 0.4) == "fail"

    def test_fallback_inverted_metric_uses_lt_threshold(self):
        # Regression: for inverted metrics a HIGH score is bad, so the fallback
        # must pass only when score < threshold — for EVERY judge (shared set).
        for name in ("hallucination", "bias", "toxicity"):
            assert name in INVERTED_METRICS
            m = SimpleNamespace(success=None, threshold=0.5)
            assert verdict_for(name, m, 0.4) == "pass"  # low = good
            assert verdict_for(name, m, 0.6) == "fail"  # high = bad

    def test_fallback_without_threshold_is_fail(self):
        m = SimpleNamespace(success=None, threshold=None)
        assert verdict_for("correctness", m, 0.9) == "fail"
