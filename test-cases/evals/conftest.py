"""Shared fixtures for eval tests.

Stubs the ``deepeval`` SDK in ``sys.modules`` before any eval test imports
the judge modules — the real DeepEval install is a heavy optional
dependency and unit tests must not require it.
"""

from __future__ import annotations

import sys
import types


def _install_deepeval_stubs() -> None:
    if "deepeval" in sys.modules and hasattr(
        sys.modules["deepeval"], "_tone_stubbed"
    ):
        return

    pkg = types.ModuleType("deepeval")
    pkg._tone_stubbed = True  # type: ignore[attr-defined]

    base_model_mod = types.ModuleType("deepeval.models.base_model")

    class DeepEvalBaseLLM:
        def __init__(self, *args, **kwargs):
            pass

        def load_model(self):
            return self

        def generate(self, prompt: str) -> str:
            raise NotImplementedError

        async def a_generate(self, prompt: str) -> str:
            raise NotImplementedError

        def get_model_name(self) -> str:
            return "stub"

    base_model_mod.DeepEvalBaseLLM = DeepEvalBaseLLM
    models_pkg = types.ModuleType("deepeval.models")

    metrics_pkg = types.ModuleType("deepeval.metrics")
    base_metric_mod = types.ModuleType("deepeval.metrics.base_metric")

    class BaseMetric:
        threshold: float = 0.0
        score: float = 0.0
        success: bool = False
        reason: str = ""
        name: str = ""

        def __init__(self, *args, threshold: float = 0.5, **kwargs):
            self.threshold = threshold
            self.score = 0.0
            self.success = False
            self.reason = ""
            self.name = self.__class__.__name__

        async def a_measure(self, tc):
            self.score = 1.0
            self.success = True
            return self.score

    base_metric_mod.BaseMetric = BaseMetric

    def _mk_metric(name: str):
        return type(name, (BaseMetric,), {"__module__": "deepeval.metrics"})

    metrics_pkg.FaithfulnessMetric = _mk_metric("FaithfulnessMetric")
    metrics_pkg.AnswerRelevancyMetric = _mk_metric("AnswerRelevancyMetric")
    metrics_pkg.ContextualPrecisionMetric = _mk_metric("ContextualPrecisionMetric")
    metrics_pkg.ContextualRecallMetric = _mk_metric("ContextualRecallMetric")
    metrics_pkg.ContextualRelevancyMetric = _mk_metric("ContextualRelevancyMetric")
    metrics_pkg.HallucinationMetric = _mk_metric("HallucinationMetric")

    class GEval(BaseMetric):
        def __init__(self, *args, name: str = "correctness", **kwargs):
            super().__init__(*args, **kwargs)
            self.name = name

    metrics_pkg.GEval = GEval

    test_case_mod = types.ModuleType("deepeval.test_case")

    class LLMTestCase:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class LLMTestCaseParams:
        INPUT = "input"
        ACTUAL_OUTPUT = "actual_output"
        EXPECTED_OUTPUT = "expected_output"

    test_case_mod.LLMTestCase = LLMTestCase
    test_case_mod.LLMTestCaseParams = LLMTestCaseParams

    sys.modules["deepeval"] = pkg
    sys.modules["deepeval.models"] = models_pkg
    sys.modules["deepeval.models.base_model"] = base_model_mod
    sys.modules["deepeval.metrics"] = metrics_pkg
    sys.modules["deepeval.metrics.base_metric"] = base_metric_mod
    sys.modules["deepeval.test_case"] = test_case_mod


_install_deepeval_stubs()
