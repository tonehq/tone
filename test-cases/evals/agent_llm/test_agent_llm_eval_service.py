"""Unit tests for ``AgentLlmEvalService``.

The DB path is stubbed via ``MagicMock`` sessions and the judge is a plain
Python object injected through the ``judge=`` kwarg. ``chat_complete`` and
``SessionLocal`` are patched so no real LLM call or Postgres connection is
attempted.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from dataclasses import dataclass, field
from typing import List, Optional

from core.services.evals.agent_llm.agent_config_loader import AgentEvalConfig
from core.services.evals.agent_llm.service import AgentLlmEvalService
from core.services.evals.errors import (
    AgentLlmEvalConfigError,
    EvalConfigurationError,
)


# Local copy of the ``LLMScenario`` shape — the real one lives in
# ``evals/fixtures/agent_llm_scenarios.py`` but pytest's ``test-cases/evals/``
# package shadows the top-level ``evals`` package during collection, so we
# duck-type it here. The service reads scenarios via plain attribute access
# (``scenario.name``, ``scenario.prompt``, …); anything satisfying the same
# attribute surface plugs in unchanged.
@dataclass
class LLMScenario:
    name: str
    prompt: str
    agent_slug: Optional[str] = None
    expected_answer: Optional[str] = None
    metrics: Optional[List[str]] = None
    threshold: Optional[float] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    expected_tools: Optional[list] = None


def _config(**overrides) -> AgentEvalConfig:
    defaults = dict(
        agent_id=uuid4(),
        agent_name="sales-bot",
        organization_id=uuid4(),
        agent_config_id=uuid4(),
        llm_model="gpt-4o",
        llm_provider="openai",
        llm_api_key="sk-agent",
        system_prompt="You are helpful.",
        llm_settings_snapshot={"temperature": 0.4},
        temperature=0.4,
        max_tokens=512,
    )
    defaults.update(overrides)
    return AgentEvalConfig(**defaults)


def _scenario(name: str = "greet", **overrides) -> LLMScenario:
    defaults = {"prompt": "Hello!", "tags": ["greet"]}
    defaults.update(overrides)
    return LLMScenario(name=name, **defaults)


class _FakeJudge:
    """Duck-types AgentLlmJudgeService: returns a fixed judge dict per call
    so the service tests don't depend on DeepEval at all."""

    def __init__(self, response=None, *, raises=None):
        self.response = response or {
            "verdict": "PASS",
            "reasoning": "",
            "metric_scores": {"answer_relevancy": {"score": 0.9, "verdict": "pass", "reason": ""}},
        }
        self.raises = raises
        self.calls = []

    def judge(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises:
            raise self.raises
        return self.response


class _FakeLoader:
    """Duck-types AgentConfigLoader: returns a pre-baked ``AgentEvalConfig``."""

    def __init__(self, cfg: AgentEvalConfig):
        self._cfg = cfg

    def load_for_eval(self, db, agent_id):
        return self._cfg

    def resolve_agent_id(self, db, ref):
        return self._cfg.agent_id


def _mock_db_with_next_run_number(n: int = 1):
    """Return a MagicMock db whose scalar() call returns ``n`` (the sequence
    ``coalesce(max(run_number), 0) + 1``)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = n
    return db


class _FakeSession:
    def __init__(self, persisted: list) -> None:
        self._persisted = persisted

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def bulk_insert_mappings(self, cls, rows):
        self._persisted.extend(rows)

    def commit(self):
        pass

    def query(self, *a, **kw):
        return MagicMock()


class _EvalHarness:
    """Context manager that patches every external side-effect the service
    touches — ``SessionLocal`` (persistence + judge-key resolution),
    ``chat_complete`` (agent LLM), and ``ProviderKeyService.get_key`` (so a
    different-provider judge doesn't try to decrypt a MagicMock)."""

    def __init__(
        self,
        *,
        persisted: list,
        chat_return="hi",
        chat_side_effect=None,
        judge_key: str = "sk-judge",
        chat_with_tools_return=None,
        chat_with_tools_side_effect=None,
    ):
        self._persisted = persisted
        self._chat_return = chat_return
        self._chat_side_effect = chat_side_effect
        self._judge_key = judge_key
        # Only patched when a test opts in — a no-tool run must NEVER
        # touch chat_complete_with_tools (asserted via ``chat_with_tools_called``).
        self._chat_with_tools_return = chat_with_tools_return
        self._chat_with_tools_side_effect = chat_with_tools_side_effect
        self.chat_with_tools_calls: list = []
        self._patches: list = []

    def __enter__(self):
        self._patches.append(
            patch(
                "core.database.session.SessionLocal",
                return_value=_FakeSession(self._persisted),
            )
        )
        if self._chat_side_effect is not None:
            self._patches.append(
                patch(
                    "core.services.evals.agent_llm.service.chat_complete",
                    side_effect=self._chat_side_effect,
                )
            )
        else:
            self._patches.append(
                patch(
                    "core.services.evals.agent_llm.service.chat_complete",
                    return_value=self._chat_return,
                )
            )

        def _capture_tools(**kwargs):
            self.chat_with_tools_calls.append(kwargs)
            if self._chat_with_tools_side_effect is not None:
                return self._chat_with_tools_side_effect(**kwargs)
            return self._chat_with_tools_return
        self._patches.append(
            patch(
                "core.services.evals.agent_llm.service.chat_complete_with_tools",
                side_effect=_capture_tools,
            )
        )

        self._patches.append(
            patch(
                "core.services.rag.provider_keys.ProviderKeyService.get_key",
                return_value=self._judge_key,
            )
        )
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *a):
        for p in reversed(self._patches):
            p.stop()
        return False


# ── run_eval ─────────────────────────────────────────────────────────────


def test_run_eval_persists_row_per_scenario():
    cfg = _config()
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    scenarios = [_scenario("s1"), _scenario("s2"), _scenario("s3")]
    persisted: list = []
    with _EvalHarness(persisted=persisted):
        summary = svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=scenarios,
        )
    assert summary.status == "completed"
    assert summary.summary["pass"] == 3
    assert summary.summary["fail"] == 0
    assert {r["scenario_key"] for r in persisted} == {"s1", "s2", "s3"}
    for row in persisted:
        assert row["llm_model"] == "gpt-4o"
        assert row["llm_provider"] == "openai"
        assert row["system_prompt"] == "You are helpful."
        assert row["llm_settings_snapshot"] == {"temperature": 0.4}
        assert row["verdict"] == "PASS"
        assert row["status"] == "completed"
        assert row["run_id"] == summary.run_id
        assert row["run_number"] == summary.run_number
        assert row["triggered_by"] == "cli"


def test_run_eval_fail_soft_on_llm_error():
    """One scenario's LLM call raising must NOT abort the run — that row is
    stamped ``failed`` and the others keep going."""
    cfg = _config()
    svc = AgentLlmEvalService(judge=_FakeJudge(), agent_loader=_FakeLoader(cfg))

    call_count = {"n": 0}

    def _flaky(**kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("upstream 429")
        return "ok"

    persisted: list = []
    with _EvalHarness(persisted=persisted, chat_side_effect=_flaky):
        summary = svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[_scenario("bad"), _scenario("good")],
        )
    assert summary.status == "completed"  # run itself didn't crash
    by_key = {r["scenario_key"]: r for r in persisted}
    assert by_key["bad"]["status"] == "failed"
    # answer_error is humanized (humanize_provider_error) before it reaches the
    # UI — "upstream 429" maps to the user-safe rate-limit one-liner, not the
    # raw "RuntimeError: upstream 429".
    assert "rate limit" in by_key["bad"]["answer_error"].lower()
    assert by_key["good"]["status"] == "completed"


def test_run_eval_reraises_configuration_error():
    """A judge configuration error must abort the run WITHOUT persisting
    anything, so the CLI sees the actionable message."""
    cfg = _config()
    judge = _FakeJudge(raises=EvalConfigurationError("bad metric"))
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    with _EvalHarness(persisted=persisted):
        with pytest.raises(EvalConfigurationError, match="bad metric"):
            svc.run_eval(
                _mock_db_with_next_run_number(1),
                agent_id=cfg.agent_id,
                scenarios=[_scenario("s1")],
            )
    assert persisted == []


def test_run_eval_empty_scenarios_raises():
    cfg = _config()
    svc = AgentLlmEvalService(judge=_FakeJudge(), agent_loader=_FakeLoader(cfg))
    with pytest.raises(AgentLlmEvalConfigError, match="No scenarios"):
        svc.run_eval(MagicMock(), agent_id=cfg.agent_id, scenarios=[])


def test_run_eval_workflow_mode_uses_playbook_as_system_message():
    """Workflow-mode agents send the serialized playbook (NOT the raw
    ``system_prompt``) to both the answer LLM and the judge, and the
    persisted result row stamps the playbook text so operators can inspect
    what was actually scored. Verifies the ``effective_system_prompt``
    branching hits every downstream consumer in one code path."""
    playbook = (
        "# Conversation Workflow\n\n"
        "### Greet — Talk step\nSay hello warmly.\n"
    )
    cfg = _config(
        system_prompt=None,
        mode="workflow",
        workflow_id=uuid4(),
        workflow_serialized=playbook,
    )
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    captured_messages: list = []

    def _capture(**kwargs):
        captured_messages.append(kwargs.get("messages"))
        return "hi"

    with _EvalHarness(persisted=persisted, chat_side_effect=_capture):
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[_scenario("s1")],
        )

    # Answer LLM saw the playbook as the system message.
    assert len(captured_messages) == 1
    system_msg = next(m for m in captured_messages[0] if m["role"] == "system")
    assert system_msg["content"] == playbook

    # Judge received the same text on ``system_prompt=``.
    assert judge.calls[0]["system_prompt"] == playbook

    # Persisted row stamps the playbook so operators can inspect what
    # was actually scored (matches production-runtime behavior).
    assert persisted[0]["system_prompt"] == playbook


def test_run_eval_prompt_mode_still_uses_system_prompt():
    """Regression guard: prompt-mode agents (no ``workflow_serialized``)
    must still pass ``system_prompt`` verbatim to both the LLM and the
    judge — byte-identical to pre-workflow behavior."""
    cfg = _config()  # default prompt mode, system_prompt='You are helpful.'
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    captured_messages: list = []

    def _capture(**kwargs):
        captured_messages.append(kwargs.get("messages"))
        return "hi"

    with _EvalHarness(persisted=persisted, chat_side_effect=_capture):
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[_scenario("s1")],
        )

    system_msg = next(m for m in captured_messages[0] if m["role"] == "system")
    assert system_msg["content"] == "You are helpful."
    assert judge.calls[0]["system_prompt"] == "You are helpful."
    assert persisted[0]["system_prompt"] == "You are helpful."


def test_run_eval_uses_scenario_metric_override():
    """Per-scenario ``metrics`` list must reach the judge — otherwise a
    scenario can't override the default ``AGENT_LLM_EVAL_METRICS_ENABLED``."""
    cfg = _config()
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    scenario = _scenario(
        "custom",
        metrics=["bias", "toxicity"],
        threshold=0.9,
        persona_criteria="stay polite",
    )
    with _EvalHarness(persisted=persisted):
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[scenario],
        )
    call = judge.calls[0]
    assert call["metrics"] == ["bias", "toxicity"]
    assert call["threshold"] == 0.9
    assert call["persona_criteria"] == "stay polite"


def test_run_eval_rejects_unknown_triggered_by():
    cfg = _config()
    svc = AgentLlmEvalService(judge=_FakeJudge(), agent_loader=_FakeLoader(cfg))
    with pytest.raises(ValueError, match="triggered_by"):
        svc.run_eval(
            MagicMock(),
            agent_id=cfg.agent_id,
            scenarios=[_scenario()],
            triggered_by="worker",
        )


def test_run_eval_stamps_run_number_monotonically():
    cfg = _config()
    svc = AgentLlmEvalService(judge=_FakeJudge(), agent_loader=_FakeLoader(cfg))
    persisted: list = []
    with _EvalHarness(persisted=persisted):
        summary = svc.run_eval(
            _mock_db_with_next_run_number(7),
            agent_id=cfg.agent_id,
            scenarios=[_scenario("s1")],
        )
    assert summary.run_number == 7
    assert persisted[0]["run_number"] == 7


def test_run_eval_without_run_id_uses_allocator_not_runs_table_lookup():
    """Regression: ``run_eval(run_id=None)`` (the CLI / fixture / test path)
    must fall back to the results-table run-number allocator, NOT look up a
    non-existent ``agent_llm_eval_runs`` row and raise.

    Previously ``run_id`` was minted (``run_id = run_id or uuid4()``) BEFORE the
    ``if run_id is not None`` check, making that branch always true and the
    ``else`` allocator dead — so every CLI run minted a fresh id, found no
    matching runs-table row, and raised ``AgentLlmEvalConfigError``. A ``db``
    whose ``scalar()`` returns ``None`` reproduces "freshly-minted id has no
    row"; the allocator is stubbed so the else-branch yields a valid number
    without depending on the mock's ``scalar()``.
    """
    cfg = _config()
    svc = AgentLlmEvalService(judge=_FakeJudge(), agent_loader=_FakeLoader(cfg))
    persisted: list = []
    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = None
    with patch.object(svc, "_next_run_number", return_value=1) as alloc, _EvalHarness(
        persisted=persisted
    ):
        summary = svc.run_eval(
            db,
            agent_id=cfg.agent_id,
            scenarios=[_scenario("s1")],
            run_id=None,
        )
    alloc.assert_called_once()  # allocator path taken, not the runs-table lookup
    assert summary.status == "completed"
    assert summary.run_number == 1
    assert persisted[0]["run_number"] == 1


def test_run_eval_judge_key_reuses_agent_key_when_same_provider():
    """Judge model on same provider as agent → the agent's already-decrypted
    key is reused (no extra DB lookup)."""
    cfg = _config(llm_provider="openai", llm_api_key="sk-agent")
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    # Judge key from harness is deliberately set to something OTHER than the
    # agent's key so the reuse-agent-key path is provable: if the service
    # short-circuits (as it should for same-provider), we see 'sk-agent';
    # if it falls through to the harness's patched ``get_key``, we'd see
    # 'sk-judge'.
    with _EvalHarness(persisted=persisted, judge_key="sk-judge"):
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[_scenario("s1")],
            judge_model="gpt-4o",  # same provider (openai)
        )
    assert judge.calls[0]["api_key"] == "sk-agent"


# ── Phase 2: tool-aware execution ─────────────────────────────────────────


def _tool(name: str) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "description": "", "parameters": {}},
    }


def test_score_one_scenario_passes_tools_when_agent_has_them():
    """Agent with tools attached → ``chat_complete_with_tools`` is called
    with the tool array, the returned ``tool_calls`` are captured on the
    scored row, and both ``tools_called`` + ``execution_trace`` columns
    are populated on the persisted result. Judge receives
    ``actual_tools`` for deterministic grading."""
    from core.services.llm.chat_complete import ChatCompletion, ToolCallIntent

    cfg = _config(tools=[_tool("book")])
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    tool_completion = ChatCompletion(
        content=None,
        tool_calls=[ToolCallIntent(name="book", arguments={"date": "2026-08-26"})],
    )

    persisted: list = []
    scenario = _scenario(
        "book_slot",
        prompt="Book me a slot for Tuesday",
        expected_tools=[{"name": "book", "arguments": {"date": "2026-08-26"}}],
    )
    with _EvalHarness(
        persisted=persisted,
        chat_with_tools_return=tool_completion,
    ) as h:
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[scenario],
        )

    # Tool-aware chat WAS called and got the tool list.
    assert len(h.chat_with_tools_calls) == 1
    tc_call = h.chat_with_tools_calls[0]
    assert tc_call["tools"] == cfg.tools

    # Judge received the actual tool calls so it can score deterministically.
    assert judge.calls[0]["actual_tools"] == [
        {"name": "book", "arguments": {"date": "2026-08-26"}}
    ]
    assert judge.calls[0]["expected_tools"] == [
        {"name": "book", "arguments": {"date": "2026-08-26"}}
    ]

    # Persisted result stamps tool_calls + execution_trace.
    row = persisted[0]
    assert row["tools_called"] == [
        {"name": "book", "arguments": {"date": "2026-08-26"}}
    ]
    assert row["execution_trace"] == {
        "turns": [{
            "role": "assistant",
            "tool_calls": [{"name": "book", "arguments": {"date": "2026-08-26"}}],
        }],
    }


def test_score_one_scenario_skips_tools_branch_when_agent_has_none():
    """Regression guard: no tools attached → ``chat_complete`` is called
    (NOT ``chat_complete_with_tools``); ``tools_called`` +
    ``execution_trace`` stay ``NULL`` so the FE renders nothing extra.
    Byte-identical to Phase 1 executor behavior."""
    cfg = _config()  # tools default to []
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    with _EvalHarness(persisted=persisted) as h:
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[_scenario("s1")],
        )

    # Tool-aware chat MUST NOT be called on a no-tool agent.
    assert h.chat_with_tools_calls == []
    # Judge still receives the tool kwargs — always keyword — but they are
    # empty for a no-tool run.
    assert judge.calls[0]["actual_tools"] == []
    assert judge.calls[0]["expected_tools"] is None
    # Persisted row: tool columns stay NULL.
    assert persisted[0]["tools_called"] is None
    assert persisted[0]["execution_trace"] is None


def test_score_one_scenario_auto_enables_tool_selection_metric():
    """A scenario with ``expected_tools`` but NO explicit ``metrics``
    override → the executor auto-appends ``tool_selection`` so the judge
    grades intent without operator config. Env-default metrics still
    apply too (deterministic metric is additive, not replacement)."""
    cfg = _config(tools=[_tool("book")])
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    from core.services.llm.chat_complete import ChatCompletion
    completion = ChatCompletion(content=None, tool_calls=[])

    persisted: list = []
    scenario = _scenario(
        "book_slot",
        metrics=["persona_adherence"],  # explicit non-tool metric
        expected_tools=[{"name": "book", "arguments": {}}],
    )
    with _EvalHarness(persisted=persisted, chat_with_tools_return=completion):
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[scenario],
        )
    # Judge received BOTH the explicit metric AND the auto-appended one.
    metrics_passed = judge.calls[0]["metrics"]
    assert "persona_adherence" in metrics_passed
    assert "tool_selection" in metrics_passed


def test_score_one_scenario_captures_tool_calls_with_empty_content():
    """Post-review regression: when the LLM emits ONLY tool_calls (no text),
    actual_answer='' but tool_calls MUST still be captured + persisted.
    The judge is still invoked with actual_output='' so the deterministic
    tool_selection metric can score; the JUDGE (not the executor) skips
    text-based DeepEval metrics in this case."""
    from core.services.llm.chat_complete import ChatCompletion, ToolCallIntent

    cfg = _config(tools=[_tool("book")])
    completion = ChatCompletion(
        content=None,  # ← text absent
        tool_calls=[ToolCallIntent(name="book", arguments={"date": "2026-08-26"})],
    )
    judge = _FakeJudge()
    svc = AgentLlmEvalService(judge=judge, agent_loader=_FakeLoader(cfg))

    persisted: list = []
    scenario = _scenario(
        "book_slot",
        expected_tools=[{"name": "book", "arguments": {"date": "2026-08-26"}}],
    )
    with _EvalHarness(persisted=persisted, chat_with_tools_return=completion):
        svc.run_eval(
            _mock_db_with_next_run_number(1),
            agent_id=cfg.agent_id,
            scenarios=[scenario],
        )

    # Tool call captured and persisted despite empty text content.
    assert persisted[0]["tools_called"] == [
        {"name": "book", "arguments": {"date": "2026-08-26"}}
    ]
    # Executor persisted actual_answer as None (empty string coerced) — the
    # judge received the intent for grading.
    assert judge.calls[0]["actual_tools"] == [
        {"name": "book", "arguments": {"date": "2026-08-26"}}
    ]
