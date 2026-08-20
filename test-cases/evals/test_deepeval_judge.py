"""DeepEval judge tests — every dependency of the real DeepEval SDK is
stubbed via ``sys.modules`` before our judge modules import them, so the
tests exercise the wiring (adapter → registry → aggregator → legacy shape)
without pulling in the actual DeepEval install.

The stubs mirror only the surface our code uses:
- ``deepeval.models.base_model.DeepEvalBaseLLM`` — subclassed by the adapter.
- ``deepeval.metrics.*`` metric classes — instantiated by the registry.
- ``deepeval.metrics.base_metric.BaseMetric`` — the type our judge annotates
  the built list against (must satisfy ``isinstance`` for whatever the metric
  classes actually are, so we point every metric class at BaseMetric).
- ``deepeval.test_case.LLMTestCase`` / ``LLMTestCaseParams`` — constructed by
  the judge but never inspected further.
"""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch


# ── Stub the deepeval SDK BEFORE our modules import from it ───────────────

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

    # Every registry-built metric is a subclass of this so isinstance-style
    # checks (if any) pass and .a_measure() / .score / .threshold live in
    # a predictable place for tests to poke at.
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
        cls = type(name, (BaseMetric,), {"__module__": "deepeval.metrics"})
        return cls

    metrics_pkg.FaithfulnessMetric = _mk_metric("FaithfulnessMetric")
    metrics_pkg.AnswerRelevancyMetric = _mk_metric("AnswerRelevancyMetric")
    metrics_pkg.ContextualPrecisionMetric = _mk_metric("ContextualPrecisionMetric")
    metrics_pkg.ContextualRecallMetric = _mk_metric("ContextualRecallMetric")
    metrics_pkg.ContextualRelevancyMetric = _mk_metric("ContextualRelevancyMetric")
    metrics_pkg.HallucinationMetric = _mk_metric("HallucinationMetric")
    metrics_pkg.BiasMetric = _mk_metric("BiasMetric")
    metrics_pkg.ToxicityMetric = _mk_metric("ToxicityMetric")

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


# ── Imports under test — evaluated AFTER the stubs are installed ─────────

from core.services.evals.deepeval.judge_service import (  # noqa: E402
    DeepEvalJudgeService,
    _map_to_legacy,
)
from core.services.evals.deepeval.llm_adapter import ToneDeepEvalLLM  # noqa: E402
from core.services.evals.deepeval.metric_registry import (  # noqa: E402
    SUPPORTED_METRICS,
    build_metrics,
)
from core.services.evals.errors import EvalConfigurationError  # noqa: E402
from core.services.evals.judge import JudgeService  # noqa: E402
from core.services.evals.judge_factory import build_judge_service  # noqa: E402


# ── llm_adapter ───────────────────────────────────────────────────────────


def test_llm_adapter_forwards_to_chat_complete():
    """.generate() must pass the model, key, single-user-message shape,
    and temperature=0 to the shared router."""
    llm = ToneDeepEvalLLM(api_key="sk-x", model="gpt-4o")
    with patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="ok",
    ) as cc:
        out = llm.generate("hi")
    assert out == "ok"
    kwargs = cc.call_args.kwargs
    assert kwargs["model"] == "gpt-4o"
    assert kwargs["api_key"] == "sk-x"
    assert kwargs["temperature"] == 0.0
    assert kwargs["json_mode"] is False
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


def test_llm_adapter_a_generate_uses_to_thread():
    """The async path must invoke the sync chat_complete via asyncio.to_thread
    (never on the event loop) so blocking SDKs don't stall the gather()."""
    llm = ToneDeepEvalLLM(api_key="sk-x", model="gpt-4o")
    with patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="async-ok",
    ), patch(
        "asyncio.to_thread", wraps=asyncio.to_thread,
    ) as tt:
        out = asyncio.run(llm.a_generate("ping"))
    assert out == "async-ok"
    assert tt.called
    # First positional arg is the sync callable.
    assert tt.call_args.args[0] == llm.generate


def test_llm_adapter_get_model_name_returns_model():
    assert ToneDeepEvalLLM(api_key="k", model="gpt-4o-mini").get_model_name() == "gpt-4o-mini"


# ── metric_registry ───────────────────────────────────────────────────────


def test_registry_builds_all_supported_metrics():
    """Every name in the default enabled list must build a (name, metric)
    pair with the passed threshold — the name is authoritative (registry
    key), never derived from the DeepEval class name."""
    llm = ToneDeepEvalLLM(api_key="k", model="gpt-4o")
    names = list(SUPPORTED_METRICS.keys())
    pairs = build_metrics(llm, names, threshold=0.42)
    assert [name for name, _ in pairs] == names
    for name, metric in pairs:
        assert getattr(metric, "threshold") == 0.42
        # Class-name sanity check to catch a builder pointing at the wrong
        # metric class, without depending on the derived-name logic.
        cls_lc = metric.__class__.__name__.lower()
        assert name.replace("_", "") in cls_lc or metric.name == name


def test_registry_dedupes_repeated_names():
    """Duplicate names must NOT build twice — running the same LLM-scored
    metric a second time doubles cost and the scorecard would only keep
    the last write anyway."""
    llm = ToneDeepEvalLLM(api_key="k", model="gpt-4o")
    pairs = build_metrics(
        llm,
        ["faithfulness", "faithfulness", "answer_relevancy"],
        threshold=0.5,
    )
    assert [name for name, _ in pairs] == ["faithfulness", "answer_relevancy"]


def test_registry_rejects_out_of_range_threshold():
    llm = ToneDeepEvalLLM(api_key="k", model="gpt-4o")
    for bad in (0.0, -0.1, 1.5):
        try:
            build_metrics(llm, ["faithfulness"], threshold=bad)
        except EvalConfigurationError:
            continue
        raise AssertionError(f"expected EvalConfigurationError for threshold={bad}")


def test_registry_unknown_metric_raises_configuration_error():
    llm = ToneDeepEvalLLM(api_key="k", model="gpt-4o")
    try:
        build_metrics(llm, ["bogus_metric"], threshold=0.5)
    except EvalConfigurationError as e:
        assert "bogus_metric" in str(e)
        return
    raise AssertionError("expected EvalConfigurationError")


def test_registry_empty_list_raises_configuration_error():
    llm = ToneDeepEvalLLM(api_key="k", model="gpt-4o")
    try:
        build_metrics(llm, [], threshold=0.5)
    except EvalConfigurationError:
        return
    raise AssertionError("expected EvalConfigurationError for empty enabled list")


# ── DeepEvalJudgeService.judge → scorecard + legacy mapping ──────────────


def _fake_metric(name: str, score: float, success: bool, reason: str = ""):
    """Return a ``(name, fake-metric)`` pair matching the shape
    ``build_metrics`` now returns. The fake mimics the DeepEval BaseMetric
    API surface the judge relies on: ``a_measure``, ``score``, ``success``,
    ``reason``, ``threshold``."""

    class _Fake:
        pass

    inst = _Fake()
    inst.threshold = 0.5
    inst.score = score
    inst.success = success
    inst.reason = reason
    inst.name = name

    async def _measure(tc):
        inst.score = score
        inst.success = success
        inst.reason = reason
        return score

    inst.a_measure = _measure
    return name, inst


def _patched_build_metrics(*_args, **_kwargs):
    # Replaces registry.build_metrics with our fixed set of fake metrics.
    return [
        _fake_metric("faithfulness", 0.9, True, ""),
        _fake_metric("answer_relevancy", 0.8, True, ""),
        _fake_metric("contextual_precision", 0.7, True, ""),
        _fake_metric("contextual_recall", 0.6, True, ""),
        _fake_metric("contextual_relevancy", 0.55, True, ""),
        _fake_metric("hallucination", 0.2, True, ""),
        _fake_metric("correctness", 0.85, True, ""),
    ]


def _run_judge(**overrides) -> dict:
    svc = DeepEvalJudgeService()
    kwargs: dict[str, Any] = {
        "question": "Q?",
        "expected_answer": "E",
        "actual_answer": "A",
        "retrieved_chunks": [{"text": "chunk1"}],
        "api_key": "sk-x",
        "model": "gpt-4o",
    }
    kwargs.update(overrides)
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        side_effect=_patched_build_metrics,
    ), patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="unused",
    ):
        return svc.judge(**kwargs)


def test_judge_maps_metrics_to_legacy_columns():
    out = _run_judge()
    assert out["groundedness"] == 0.9  # from faithfulness
    assert out["relevance"] == 0.8     # from answer_relevancy
    assert out["correctness"] == 0.85  # from correctness (GEval)


def test_judge_captures_full_scorecard():
    out = _run_judge()
    scorecard = out["metric_scores"]
    expected = {
        "faithfulness", "answer_relevancy", "contextual_precision",
        "contextual_recall", "contextual_relevancy", "hallucination",
        "correctness",
    }
    assert set(scorecard.keys()) == expected
    for name, entry in scorecard.items():
        assert set(entry.keys()) == {"score", "verdict", "reason"}
        assert entry["verdict"] in {"pass", "fail"}


def test_judge_verdict_pass_when_all_metrics_succeed():
    out = _run_judge()
    assert out["verdict"] == "PASS"


def test_judge_verdict_partial_when_half_succeed():
    def _mix(*_a, **_kw):
        return [
            _fake_metric("faithfulness", 0.9, True),
            _fake_metric("answer_relevancy", 0.9, True),
            _fake_metric("hallucination", 0.9, False, "bad"),
            _fake_metric("correctness", 0.3, False, "wrong"),
        ]
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        side_effect=_mix,
    ), patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="x",
    ):
        out = DeepEvalJudgeService().judge(
            question="Q", expected_answer="E", actual_answer="A",
            retrieved_chunks=[], api_key="k", model="gpt-4o",
        )
    assert out["verdict"] == "PARTIAL"


def test_judge_verdict_fail_when_most_fail():
    def _mostly_fail(*_a, **_kw):
        return [
            _fake_metric("faithfulness", 0.1, False, "hallucinated"),
            _fake_metric("answer_relevancy", 0.1, False, "off-topic"),
            _fake_metric("hallucination", 0.9, False, "fabricated"),
            _fake_metric("correctness", 0.85, True),
        ]
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        side_effect=_mostly_fail,
    ), patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="x",
    ):
        out = DeepEvalJudgeService().judge(
            question="Q", expected_answer="E", actual_answer="A",
            retrieved_chunks=[], api_key="k", model="gpt-4o",
        )
    assert out["verdict"] == "FAIL"


def test_judge_reasoning_aggregates_failure_reasons_only():
    def _mix(*_a, **_kw):
        return [
            _fake_metric("faithfulness", 0.9, True, "grounded fine"),
            _fake_metric("answer_relevancy", 0.1, False, "off-topic"),
            _fake_metric("correctness", 0.2, False, "wrong entity"),
        ]
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        side_effect=_mix,
    ), patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="x",
    ):
        out = DeepEvalJudgeService().judge(
            question="Q", expected_answer="E", actual_answer="A",
            retrieved_chunks=[], api_key="k", model="gpt-4o",
        )
    reasoning = out["reasoning"]
    assert "off-topic" in reasoning
    assert "wrong entity" in reasoning
    assert "grounded fine" not in reasoning
    assert len(reasoning) <= 2000


def test_judge_survives_single_metric_exception():
    """One metric raising must NOT sink the whole judge — the offender is
    stamped fail with its exception; the others still contribute."""
    def _one_broken(*_a, **_kw):
        name, broken = _fake_metric("faithfulness", 0.9, True)

        async def _boom(tc):
            raise RuntimeError("upstream 500")

        broken.a_measure = _boom
        return [
            (name, broken),
            _fake_metric("answer_relevancy", 0.9, True),
            _fake_metric("correctness", 0.85, True),
        ]
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        side_effect=_one_broken,
    ), patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="x",
    ):
        out = DeepEvalJudgeService().judge(
            question="Q", expected_answer="E", actual_answer="A",
            retrieved_chunks=[], api_key="k", model="gpt-4o",
        )
    scorecard = out["metric_scores"]
    assert scorecard["faithfulness"]["verdict"] == "fail"
    assert "RuntimeError" in scorecard["faithfulness"]["reason"]
    assert scorecard["answer_relevancy"]["verdict"] == "pass"


def test_judge_reraises_configuration_error():
    """A systemic config error must ABORT the run (raised for the caller
    to handle) instead of silently persisting N identical fake-FAIL rows,
    one per question."""
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        side_effect=EvalConfigurationError("bad metric"),
    ):
        try:
            DeepEvalJudgeService().judge(
                question="Q", expected_answer="E", actual_answer="A",
                retrieved_chunks=[], api_key="k", model="gpt-4o",
            )
        except EvalConfigurationError as e:
            assert "bad metric" in str(e)
            return
        raise AssertionError("expected EvalConfigurationError to propagate")


def test_judge_survives_orchestrator_exception():
    """A non-configuration exception raised inside the async orchestrator
    (e.g., a metric raised in a way that escaped ``_safe_measure``) still
    returns the legacy fail-shape so a single anomaly doesn't break the run."""
    with patch(
        "core.services.evals.deepeval.judge_service.build_metrics",
        return_value=_patched_build_metrics(),
    ), patch(
        "core.services.evals.deepeval.judge_service.asyncio.run",
        side_effect=RuntimeError("boom"),
    ):
        out = DeepEvalJudgeService().judge(
            question="Q", expected_answer="E", actual_answer="A",
            retrieved_chunks=[], api_key="k", model="gpt-4o",
        )
    assert out["verdict"] == "FAIL"
    assert out["metric_scores"] == {}
    assert "boom" in out["reasoning"]


def test_map_to_legacy_empty_scorecard_yields_specific_reason():
    """Empty scorecard is distinguishable from a real all-metrics-failed
    run — the drawer otherwise shows FAIL with no signal that no metrics
    ran at all."""
    out = _map_to_legacy({})
    assert out["verdict"] == "FAIL"
    assert out["metric_scores"] == {}
    assert out["reasoning"] == "no metrics scored"


# ── judge_factory ─────────────────────────────────────────────────────────


def test_factory_returns_deepeval_when_configured(monkeypatch):
    from shared.config import settings
    monkeypatch.setattr(settings, "EVAL_JUDGE_ENGINE", "deepeval", raising=False)
    svc = build_judge_service()
    assert isinstance(svc, DeepEvalJudgeService)


def test_factory_returns_legacy_when_configured(monkeypatch):
    from shared.config import settings
    monkeypatch.setattr(settings, "EVAL_JUDGE_ENGINE", "legacy", raising=False)
    svc = build_judge_service()
    assert isinstance(svc, JudgeService)


def test_factory_rejects_unknown_engine(monkeypatch):
    from shared.config import settings
    monkeypatch.setattr(settings, "EVAL_JUDGE_ENGINE", "bogus", raising=False)
    try:
        build_judge_service()
    except EvalConfigurationError as e:
        assert "bogus" in str(e)
        return
    raise AssertionError("expected EvalConfigurationError")
