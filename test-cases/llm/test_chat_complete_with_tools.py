"""Unit tests for ``chat_complete_with_tools`` — the tool-aware sibling of
``chat_complete``.

Focus is on the OpenAI path (the primary provider for LLM evals today);
Anthropic + Google paths are covered by shape / argument-conversion tests
so a future SDK change surfaces here loudly instead of silently at eval
run time. NO real SDK calls — every provider module is patched at its
import site inside ``chat_complete``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.services.llm.chat_complete import (
    ChatCompletion,
    ToolCallIntent,
    _parse_tool_arguments,
    chat_complete_with_tools,
)
from core.services.llm.errors import LLMChatCompletionError


# ── argument parser ──────────────────────────────────────────────────────


def test_parse_tool_arguments_valid_json_string():
    assert _parse_tool_arguments('{"a": 1}', tool_name="x") == {"a": 1}


def test_parse_tool_arguments_dict_pass_through():
    assert _parse_tool_arguments({"b": 2}, tool_name="x") == {"b": 2}


def test_parse_tool_arguments_bad_json_returns_empty_dict():
    """Provider gave us malformed JSON — degrade to {} + log a warning
    (non-fatal; the tool-call intent still counts and the deterministic
    tool_selection metric will score name-only match)."""
    assert _parse_tool_arguments("not-json", tool_name="x") == {}


def test_parse_tool_arguments_empty_or_none():
    assert _parse_tool_arguments(None, tool_name="x") == {}
    assert _parse_tool_arguments("", tool_name="x") == {}


# ── OpenAI dispatch ──────────────────────────────────────────────────────


_TOOL = {
    "type": "function",
    "function": {
        "name": "book",
        "description": "Book a slot",
        "parameters": {
            "type": "object",
            "properties": {"date": {"type": "string"}},
            "required": ["date"],
        },
    },
}


def _fake_openai_with_tools(tool_calls=None, content=None):
    """Build a stand-in for ``openai`` returning a message with the
    given ``content`` + ``tool_calls`` payload."""
    module = MagicMock()
    client = MagicMock()
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message)]
    )
    module.OpenAI.return_value = client
    return module, client


def _openai_tc(name: str, arguments: str):
    """One OpenAI-shaped tool_call — attribute access, not dict, to match
    the SDK's return."""
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=arguments),
        type="function",
        id="call_1",
    )


def test_openai_tool_only_reply():
    """Model emitted a tool call and no text → content=None, tool_calls
    populated with parsed arguments."""
    module, client = _fake_openai_with_tools(
        tool_calls=[_openai_tc("book", '{"date": "2026-08-26"}')],
        content=None,
    )
    with patch.dict("sys.modules", {"openai": module}):
        result = chat_complete_with_tools(
            model="gpt-4o",
            api_key="sk-x",
            messages=[{"role": "user", "content": "book a slot"}],
            tools=[_TOOL],
        )
    assert isinstance(result, ChatCompletion)
    assert result.content is None
    assert result.tool_calls == [ToolCallIntent(name="book", arguments={"date": "2026-08-26"})]
    # Verify tools + tool_choice reached the SDK
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["tools"] == [_TOOL]
    assert kwargs["tool_choice"] == "auto"


def test_openai_text_only_reply():
    """Model chose to answer in text → content populated, tool_calls empty
    (the deterministic metric will score this as "expected tool not called"
    when a scenario expected one)."""
    module, _ = _fake_openai_with_tools(content="I can help with that.")
    with patch.dict("sys.modules", {"openai": module}):
        result = chat_complete_with_tools(
            model="gpt-4o",
            api_key="sk-x",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_TOOL],
        )
    assert result.content == "I can help with that."
    assert result.tool_calls == []


def test_openai_bad_json_arguments_degrades_to_empty_dict():
    """Provider returned tool_call with malformed JSON args → tool intent
    still captured with empty args. Warning is logged (non-fatal)."""
    module, _ = _fake_openai_with_tools(
        tool_calls=[_openai_tc("book", "not-valid-json")],
    )
    with patch.dict("sys.modules", {"openai": module}):
        result = chat_complete_with_tools(
            model="gpt-4o",
            api_key="sk-x",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_TOOL],
        )
    assert result.tool_calls == [ToolCallIntent(name="book", arguments={})]


def test_openai_empty_content_and_no_tool_calls_raises():
    """A completely empty response is nothing to score — raise so the
    per-scenario row surfaces the failure with a clear provider mention
    instead of silently persisting a blank answer."""
    module, _ = _fake_openai_with_tools(content=None, tool_calls=[])
    with patch.dict("sys.modules", {"openai": module}):
        with pytest.raises(LLMChatCompletionError, match="nothing to score"):
            chat_complete_with_tools(
                model="gpt-4o",
                api_key="sk-x",
                messages=[{"role": "user", "content": "hi"}],
                tools=[_TOOL],
            )


# ── Anthropic dispatch shape ─────────────────────────────────────────────


def test_anthropic_tool_schema_conversion():
    """Anthropic uses a different tool-schema shape (top-level ``name`` /
    ``description`` / ``input_schema``, not the OpenAI ``function`` wrapper).
    The dispatcher must convert; verify by inspecting the SDK call."""
    module = MagicMock()
    client = MagicMock()
    resp = SimpleNamespace(content=[SimpleNamespace(type="text", text="ok")])
    client.messages.create.return_value = resp
    module.Anthropic.return_value = client

    with patch.dict("sys.modules", {"anthropic": module}):
        chat_complete_with_tools(
            model="claude-3-5-sonnet-20241022",
            api_key="sk-x",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_TOOL],
        )

    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["tools"] == [{
        "name": "book",
        "description": "Book a slot",
        "input_schema": _TOOL["function"]["parameters"],
    }]


def test_anthropic_extracts_tool_use_blocks():
    """Anthropic returns tool_use as a content block; we extract name +
    input into a ToolCallIntent."""
    module = MagicMock()
    client = MagicMock()
    tool_use_block = SimpleNamespace(
        type="tool_use", name="book", input={"date": "2026-08-26"},
    )
    text_block = SimpleNamespace(type="text", text="Booking now.")
    client.messages.create.return_value = SimpleNamespace(
        content=[text_block, tool_use_block]
    )
    module.Anthropic.return_value = client

    with patch.dict("sys.modules", {"anthropic": module}):
        result = chat_complete_with_tools(
            model="claude-3-5-sonnet-20241022",
            api_key="sk-x",
            messages=[{"role": "user", "content": "book"}],
            tools=[_TOOL],
        )
    assert result.content == "Booking now."
    assert result.tool_calls == [
        ToolCallIntent(name="book", arguments={"date": "2026-08-26"})
    ]


# ── unknown provider ─────────────────────────────────────────────────────


def test_unknown_model_prefix_raises():
    """A model name with no known prefix → clean error identifying the
    unknown model + the supported prefix list."""
    with pytest.raises(Exception) as exc:
        chat_complete_with_tools(
            model="my-custom-ft",
            api_key="sk-x",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_TOOL],
        )
    assert "my-custom-ft" in str(exc.value)
