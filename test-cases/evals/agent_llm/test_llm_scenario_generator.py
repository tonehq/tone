"""Unit tests for ``LlmGenerator`` — the LLM-backed scenario generator.

Isolates the mode-selection branch (prompt-mode vs workflow-mode meta-prompt)
so a future edit to the meta-prompts can't accidentally send the wrong
framing to the judge. External side-effects (``chat_complete``, judge-key
resolution, judge-model resolution) are patched — no real LLM call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from core.services.evals.agent_llm.agent_config_loader import AgentEvalConfig
from core.services.evals.agent_llm.scenario_generation.strategies.llm import (
    LlmGenerator,
)
from core.services.evals.errors import AgentLlmEvalConfigError


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
        llm_settings_snapshot={},
        temperature=0.0,
        max_tokens=1024,
    )
    defaults.update(overrides)
    return AgentEvalConfig(**defaults)


_JUDGE_JSON_ONE = (
    '{"scenarios": [{"scenario_key": "greet", "prompt": "Hello!", '
    '"tags": ["smoke"]}]}'
)


class _GeneratorHarness:
    """Patches every side-effect the LlmGenerator touches so tests only
    observe what got sent to ``chat_complete``."""

    def __init__(self, *, cfg: AgentEvalConfig, chat_return: str = _JUDGE_JSON_ONE):
        self._cfg = cfg
        self._chat_return = chat_return
        self.chat_calls: list = []
        self._patches: list = []

    def _fake_load_agent_config(self, db, agent_id):  # noqa: ARG002
        return self._cfg

    def _fake_resolve_judge_model(self, db, organization_id):  # noqa: ARG002
        return "gpt-4o-mini"

    def _fake_resolve_judge_key(self, agent_config, judge_model):  # noqa: ARG002
        return "sk-judge"

    def _fake_chat_complete(self, **kwargs):
        self.chat_calls.append(kwargs)
        return self._chat_return

    def __enter__(self):
        # Patch the generator's dependencies rather than the ``LlmGenerator``
        # instance methods so a caller-side signature drift is caught here too.
        self._patches.append(
            patch.object(LlmGenerator, "_load_agent_config", self._fake_load_agent_config)
        )
        self._patches.append(
            patch.object(LlmGenerator, "_resolve_judge_model", self._fake_resolve_judge_model)
        )
        self._patches.append(
            patch.object(LlmGenerator, "_resolve_judge_key", self._fake_resolve_judge_key)
        )
        self._patches.append(
            patch(
                "core.services.llm.chat_complete.chat_complete",
                side_effect=self._fake_chat_complete,
            )
        )
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *a):
        for p in reversed(self._patches):
            p.stop()
        return False


def test_generate_prompt_mode_frames_system_prompt():
    """Prompt-mode config → user message is the ``AGENT SYSTEM PROMPT:``
    framing and the meta-prompt is the ``_META_SYSTEM_PROMPT`` variant."""
    cfg = _config(system_prompt="You are a friendly guide.")
    with _GeneratorHarness(cfg=cfg) as h:
        out = LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)

    assert len(out) == 1
    assert out[0].scenario_key == "greet"

    call = h.chat_calls[0]
    system_msg = next(m for m in call["messages"] if m["role"] == "system")
    user_msg = next(m for m in call["messages"] if m["role"] == "user")
    assert "You are a QA test author" in system_msg["content"]
    # Prompt-mode meta-prompt has the "AGENT SYSTEM PROMPT" phrasing in
    # the user framing (not the workflow one).
    assert "AGENT SYSTEM PROMPT:" in user_msg["content"]
    assert "AGENT WORKFLOW PLAYBOOK:" not in user_msg["content"]
    assert "You are a friendly guide." in user_msg["content"]


def test_generate_workflow_mode_frames_playbook():
    """Workflow-mode config → user message is the ``AGENT WORKFLOW
    PLAYBOOK:`` framing and the meta-prompt is the workflow variant that
    talks about steps and branches."""
    playbook = (
        "# Conversation Workflow\n\n"
        "### Greet — Talk step\nSay hello warmly and ask for the caller's name.\n"
    )
    cfg = _config(
        system_prompt=None,
        mode="workflow",
        workflow_id=uuid4(),
        workflow_serialized=playbook,
    )
    with _GeneratorHarness(cfg=cfg) as h:
        LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)

    call = h.chat_calls[0]
    system_msg = next(m for m in call["messages"] if m["role"] == "system")
    user_msg = next(m for m in call["messages"] if m["role"] == "user")
    # Workflow meta-prompt has explicit workflow language (the exact text
    # contains a line break inside the phrase, so normalize whitespace for
    # the assertion so a future re-wrap of the constant doesn't break this).
    normalized_system = " ".join(system_msg["content"].split())
    assert "conversation" in normalized_system.lower()
    assert "steps and branches" in normalized_system
    # User framing references the playbook and contains its text.
    assert "AGENT WORKFLOW PLAYBOOK:" in user_msg["content"]
    assert "AGENT SYSTEM PROMPT:" not in user_msg["content"]
    assert playbook.strip() in user_msg["content"]


def test_generate_empty_response_raises_mode_aware_error():
    """Judge returns zero scenarios → error copy mentions ``system prompt``,
    ``workflow``, AND ``tool descriptions`` so the user isn't misdirected on
    any agent shape."""
    cfg = _config()
    with _GeneratorHarness(cfg=cfg, chat_return='{"scenarios": []}'):
        with pytest.raises(
            AgentLlmEvalConfigError, match="system prompt, workflow, or tool",
        ):
            LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)


# ── Phase 2: tool + MCP awareness ─────────────────────────────────────────


def _tool(name: str, description: str = "", required=()) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {k: {"type": "string"} for k in required},
                "required": list(required),
            },
        },
    }


def test_generate_appends_tools_section_when_agent_has_tools():
    """Agent with tools attached → user message carries an ``AGENT TOOLS:``
    block listing each tool by name + description. Meta-prompt instructs
    the judge to fill ``expected_tools``."""
    cfg = _config(
        tools=[
            _tool("book_appointment", "Book a salon appointment", required=("date",)),
            _tool("cancel_appointment", "Cancel an existing booking"),
        ],
    )
    with _GeneratorHarness(cfg=cfg) as h:
        LlmGenerator().generate(MagicMock(), cfg.agent_id, count=2)

    call = h.chat_calls[0]
    user_msg = next(m for m in call["messages"] if m["role"] == "user")
    system_msg = next(m for m in call["messages"] if m["role"] == "system")

    assert "AGENT TOOLS:" in user_msg["content"]
    assert "- book_appointment(date) — Book a salon appointment" in user_msg["content"]
    assert "- cancel_appointment() — Cancel an existing booking" in user_msg["content"]
    # Meta-prompt tells the judge to populate expected_tools
    assert "expected_tools" in system_msg["content"]


def test_generate_appends_mcp_section_when_agent_has_mcp_servers():
    """Agent with MCP servers attached → user message carries an
    ``AGENT MCP SERVERS:`` block (server-name-only; no per-tool listing)."""
    cfg = _config(
        mcp_server_summaries=[
            {"name": "calendar_mcp", "description": "Manages calendar events"},
        ],
    )
    with _GeneratorHarness(cfg=cfg) as h:
        LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)

    user_msg = next(m for m in h.chat_calls[0]["messages"] if m["role"] == "user")
    assert "AGENT MCP SERVERS:" in user_msg["content"]
    assert "- calendar_mcp — Manages calendar events" in user_msg["content"]


def test_generate_omits_tools_section_when_agent_has_none():
    """Regression guard: no tools attached → NO ``AGENT TOOLS:`` block
    appears (byte-identical to Phase 1 prompt-mode framing)."""
    cfg = _config()  # tools default to []
    with _GeneratorHarness(cfg=cfg) as h:
        LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)

    user_msg = next(m for m in h.chat_calls[0]["messages"] if m["role"] == "user")
    assert "AGENT TOOLS:" not in user_msg["content"]
    assert "AGENT MCP SERVERS:" not in user_msg["content"]


def test_generate_captures_expected_tools_from_judge_json():
    """Judge returns a scenario with ``expected_tools`` → the returned
    ``GeneratedScenario`` carries the same shape through unchanged so
    ``_generated_to_input`` can persist it into
    ``agent_llm_eval_scenarios.expected_tools``."""
    cfg = _config(
        tools=[_tool("book", "Book", required=("date",))],
    )
    judge_json = (
        '{"scenarios": [{"scenario_key": "book_slot", '
        '"prompt": "Book me a slot for Tuesday", '
        '"expected_tools": [{"name": "book", "arguments": {"date": "Tuesday"}}]}]}'
    )
    with _GeneratorHarness(cfg=cfg, chat_return=judge_json):
        out = LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)

    assert len(out) == 1
    assert out[0].expected_tools == [
        {"name": "book", "arguments": {"date": "Tuesday"}}
    ]


def test_generate_expected_tools_missing_defaults_to_none():
    """Regression guard: scenarios where the judge OMITS ``expected_tools``
    (text-only) get ``expected_tools=None``, NOT an empty list, so downstream
    ``if scenario.expected_tools`` guards keep the tool-metric quiet."""
    cfg = _config()
    with _GeneratorHarness(cfg=cfg) as h:  # noqa: F841 — using default JSON
        out = LlmGenerator().generate(MagicMock(), cfg.agent_id, count=1)
    assert out[0].expected_tools is None
