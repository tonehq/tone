"""Unit tests for ``AgentLlmJudgeService`` — DeepEval SDK is stubbed via
``test-cases/evals/conftest.py`` (``sys.modules`` install) so no real
DeepEval install is required.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from core.services.evals.agent_llm.agent_llm_judge import (  # noqa: E402
    AgentLlmJudgeService,
)
from core.services.evals.errors import EvalConfigurationError  # noqa: E402


def _fake_metric(name: str, score: float, success: bool, reason: str = ""):
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


def _run_judge(fake_metrics, **overrides) -> dict:
    svc = AgentLlmJudgeService()
    kwargs: dict[str, Any] = {
        "prompt": "Hi there",
        "system_prompt": "You are a polite assistant.",
        "actual_output": "Hello — how can I help?",
        "api_key": "sk-x",
        "model": "gpt-4o",
        "metrics": [name for name, _ in fake_metrics],
        "threshold": 0.7,
    }
    kwargs.update(overrides)
    with patch(
        "core.services.evals.agent_llm.agent_llm_judge.build_metrics",
        return_value=fake_metrics,
    ), patch(
        "core.services.evals.deepeval.llm_adapter.chat_complete",
        return_value="unused",
    ):
        return svc.judge(**kwargs)


def test_judge_returns_pass_when_all_metrics_pass():
    out = _run_judge(
        [
            _fake_metric("answer_relevancy", 0.9, True),
            _fake_metric("bias", 0.0, True),
            _fake_metric("toxicity", 0.0, True),
        ]
    )
    assert out["verdict"] == "PASS"
    assert set(out["metric_scores"].keys()) == {"answer_relevancy", "bias", "toxicity"}


def test_judge_returns_partial_when_half_succeed():
    out = _run_judge(
        [
            _fake_metric("answer_relevancy", 0.9, True),
            _fake_metric("bias", 0.9, False, "biased content"),
            _fake_metric("toxicity", 0.9, False, "toxic phrasing"),
            _fake_metric("persona_adherence", 0.9, True),
        ]
    )
    assert out["verdict"] == "PARTIAL"


def test_judge_returns_fail_when_most_fail():
    out = _run_judge(
        [
            _fake_metric("answer_relevancy", 0.1, False, "off-topic"),
            _fake_metric("bias", 0.9, False, "biased"),
            _fake_metric("toxicity", 0.9, False, "toxic"),
            _fake_metric("persona_adherence", 0.9, True),
        ]
    )
    assert out["verdict"] == "FAIL"


def test_judge_reasoning_only_lists_failures():
    out = _run_judge(
        [
            _fake_metric("answer_relevancy", 0.9, True, "grounded fine"),
            _fake_metric("bias", 0.9, False, "biased phrasing"),
        ]
    )
    assert "biased phrasing" in out["reasoning"]
    assert "grounded fine" not in out["reasoning"]


def test_judge_survives_single_metric_exception():
    """One metric raising must NOT sink the whole judge — the offender is
    stamped fail with its exception; the others still contribute."""
    name, broken = _fake_metric("bias", 0.9, True)

    async def _boom(tc):
        raise RuntimeError("upstream 500")

    broken.a_measure = _boom
    out = _run_judge(
        [
            (name, broken),
            _fake_metric("answer_relevancy", 0.9, True),
        ]
    )
    scorecard = out["metric_scores"]
    assert scorecard["bias"]["verdict"] == "fail"
    assert "RuntimeError" in scorecard["bias"]["reason"]
    assert scorecard["answer_relevancy"]["verdict"] == "pass"


def test_judge_reraises_configuration_error():
    """A systemic config error must ABORT the run (raised for the caller
    to handle) instead of silently persisting fake-FAIL rows."""
    with patch(
        "core.services.evals.agent_llm.agent_llm_judge.build_metrics",
        side_effect=EvalConfigurationError("bad metric"),
    ):
        try:
            AgentLlmJudgeService().judge(
                prompt="Q",
                system_prompt="S",
                actual_output="A",
                api_key="k",
                model="gpt-4o",
                metrics=["bogus"],
                threshold=0.7,
            )
        except EvalConfigurationError as e:
            assert "bad metric" in str(e)
            return
        raise AssertionError("expected EvalConfigurationError to propagate")


def test_judge_forwards_geval_criteria():
    """Scenario-supplied ``persona_criteria`` / ``instruction_criteria`` must
    reach ``build_metrics`` via the ``criteria=`` kwarg."""
    captured: dict = {}

    def _capture(llm, names, threshold, *, criteria=None):
        captured["criteria"] = criteria
        return [_fake_metric(n, 0.9, True) for n in names]

    with patch(
        "core.services.evals.agent_llm.agent_llm_judge.build_metrics",
        side_effect=_capture,
    ):
        AgentLlmJudgeService().judge(
            prompt="Hi",
            system_prompt="Persona X",
            actual_output="Hello",
            api_key="k",
            model="gpt-4o",
            metrics=["persona_adherence", "instruction_following"],
            threshold=0.7,
            persona_criteria="stay in character",
            instruction_criteria="answer briefly",
        )
    assert captured["criteria"] == {
        "persona_adherence": "stay in character",
        "instruction_following": "answer briefly",
    }


def test_judge_orchestrator_exception_returns_fail_shape():
    """An unexpected exception inside the async orchestrator (not per-metric)
    yields the fail-shape so a single anomaly doesn't kill the batch."""
    with patch(
        "core.services.evals.agent_llm.agent_llm_judge.build_metrics",
        return_value=[_fake_metric("answer_relevancy", 0.9, True)],
    ), patch(
        "core.services.evals.agent_llm.agent_llm_judge.asyncio.run",
        side_effect=RuntimeError("boom"),
    ):
        out = AgentLlmJudgeService().judge(
            prompt="Q",
            system_prompt="S",
            actual_output="A",
            api_key="k",
            model="gpt-4o",
            metrics=["answer_relevancy"],
            threshold=0.7,
        )
    assert out["verdict"] == "FAIL"
    assert out["metric_scores"] == {}
    assert "boom" in out["reasoning"]
