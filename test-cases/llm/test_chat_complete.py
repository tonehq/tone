"""Tests for the shared chat-completion router.

Verifies (a) model-prefix → provider resolution and (b) each SDK dispatcher
gets the right shape of args. SDKs are patched at their import site inside
``chat_complete`` so no network I/O and no real API keys are needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.services.llm.chat_complete import chat_complete, resolve_provider
from core.services.llm.errors import (
    LLMChatCompletionError,
    LLMProviderResolutionError,
)


# ── resolve_provider ──────────────────────────────────────────────────────


def test_resolve_provider_openai_prefixes():
    assert resolve_provider("gpt-4o") == "openai"
    assert resolve_provider("gpt-4o-mini") == "openai"
    assert resolve_provider("o1-mini") == "openai"
    assert resolve_provider("chatgpt-4o-latest") == "openai"


def test_resolve_provider_anthropic_prefix():
    assert resolve_provider("claude-3-5-sonnet-20241022") == "anthropic"
    assert resolve_provider("claude-haiku-4-5") == "anthropic"


def test_resolve_provider_google_prefixes():
    assert resolve_provider("gemini-2.5-flash") == "google"
    assert resolve_provider("gemini-1.5-pro") == "google"
    assert resolve_provider("gemma-2-9b") == "google"
    assert resolve_provider("models/gemini-2.0-flash") == "google"


def test_resolve_provider_case_insensitive():
    assert resolve_provider("GPT-4O") == "openai"
    assert resolve_provider("Claude-3-Opus") == "anthropic"


def test_resolve_provider_unknown_raises():
    with pytest.raises(LLMProviderResolutionError) as exc:
        resolve_provider("my-custom-ft")
    assert "my-custom-ft" in str(exc.value)
    # error should hint at the known families so the operator can fix it
    assert "gpt-" in str(exc.value)
    assert "claude-" in str(exc.value)
    assert "gemini-" in str(exc.value)


def test_resolve_provider_empty_raises():
    with pytest.raises(LLMProviderResolutionError):
        resolve_provider("")


# ── chat_complete dispatch ────────────────────────────────────────────────


def _fake_openai_module(content: str = "hello"):
    """Build a stand-in for ``openai`` with a ``.OpenAI(...).chat.completions.create``
    chain that returns ``content``."""
    module = MagicMock()
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    module.OpenAI.return_value = client
    return module, client


def _fake_anthropic_module(text_blocks):
    module = MagicMock()
    client = MagicMock()
    blocks = [SimpleNamespace(type="text", text=t) for t in text_blocks]
    client.messages.create.return_value = SimpleNamespace(content=blocks)
    module.Anthropic.return_value = client
    return module, client


def test_chat_complete_dispatches_openai():
    fake_openai, client = _fake_openai_module(content="hi from gpt")
    with patch.dict("sys.modules", {"openai": fake_openai}):
        out = chat_complete(
            model="gpt-4o",
            api_key="sk-test",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.2,
            json_mode=True,
        )
    assert out == "hi from gpt"
    fake_openai.OpenAI.assert_called_once_with(api_key="sk-test")
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-4o"
    assert kwargs["messages"] == [{"role": "user", "content": "hello"}]
    assert kwargs["temperature"] == 0.2
    assert kwargs["response_format"] == {"type": "json_object"}


def test_chat_complete_openai_json_mode_off_omits_response_format():
    fake_openai, client = _fake_openai_module(content="prose answer")
    with patch.dict("sys.modules", {"openai": fake_openai}):
        chat_complete(
            model="gpt-4o",
            api_key="sk-test",
            messages=[{"role": "user", "content": "hi"}],
            json_mode=False,
        )
    _, kwargs = client.chat.completions.create.call_args
    assert "response_format" not in kwargs


def test_chat_complete_dispatches_anthropic():
    fake_anthropic, client = _fake_anthropic_module(["part-a", "part-b"])
    with patch.dict("sys.modules", {"anthropic": fake_anthropic}):
        out = chat_complete(
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-xxx",
            messages=[
                {"role": "system", "content": "You are terse."},
                {"role": "user", "content": "hello"},
            ],
            temperature=0.0,
            json_mode=True,
            max_tokens=1234,
        )
    assert out == "part-apart-b"
    fake_anthropic.Anthropic.assert_called_once_with(api_key="sk-ant-xxx")
    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-3-5-sonnet-20241022"
    assert kwargs["max_tokens"] == 1234
    assert kwargs["system"] == "You are terse."
    assert kwargs["temperature"] == 0.0
    # Anthropic has no response_format → json nudge appended to last user turn
    assert kwargs["messages"][-1]["role"] == "user"
    assert "Return valid JSON only" in kwargs["messages"][-1]["content"]
    assert "hello" in kwargs["messages"][-1]["content"]


def test_chat_complete_dispatches_google():
    pytest.importorskip("google.genai")
    from google.genai import types as google_genai_types

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(text="from gemini")
    with patch(
        "google.genai.Client", return_value=fake_client, create=True
    ) as ctor:
        out = chat_complete(
            model="gemini-2.5-flash",
            api_key="google-key",
            messages=[
                {"role": "system", "content": "answer briefly"},
                {"role": "user", "content": "hi"},
            ],
            temperature=0.1,
            json_mode=True,
            max_tokens=2048,
        )
    assert out == "from gemini"
    ctor.assert_called_once_with(api_key="google-key")
    _, kwargs = fake_client.models.generate_content.call_args
    assert kwargs["model"] == "gemini-2.5-flash"
    contents = kwargs["contents"]
    assert contents[-1]["role"] == "user"
    assert contents[-1]["parts"][0]["text"] == "hi"
    config = kwargs["config"]
    assert isinstance(config, google_genai_types.GenerateContentConfig)
    # Round-trip a few config fields via getattr so we don't couple to the
    # SDK's internal attribute names beyond what we set.
    assert getattr(config, "response_mime_type", None) == "application/json"
    assert getattr(config, "temperature", None) == 0.1
    assert getattr(config, "max_output_tokens", None) == 2048


def test_chat_complete_google_falls_back_to_candidates_when_text_empty():
    pytest.importorskip("google.genai")

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(
        text=None,
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text="fallback-text")]
                )
            )
        ],
    )
    with patch("google.genai.Client", return_value=fake_client, create=True):
        out = chat_complete(
            model="gemini-2.5-flash",
            api_key="google-key",
            messages=[{"role": "user", "content": "hi"}],
        )
    assert out == "fallback-text"


def test_chat_complete_empty_response_raises():
    fake_openai, _ = _fake_openai_module(content="")
    with patch.dict("sys.modules", {"openai": fake_openai}):
        with pytest.raises(LLMChatCompletionError) as exc:
            chat_complete(
                model="gpt-4o",
                api_key="sk-test",
                messages=[{"role": "user", "content": "hi"}],
            )
    assert "empty content" in str(exc.value)
    assert "gpt-4o" in str(exc.value)


def test_chat_complete_wraps_sdk_error():
    fake_openai = MagicMock()
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("upstream 500")
    fake_openai.OpenAI.return_value = client
    with patch.dict("sys.modules", {"openai": fake_openai}):
        with pytest.raises(LLMChatCompletionError) as exc:
            chat_complete(
                model="gpt-4o",
                api_key="sk-test",
                messages=[{"role": "user", "content": "hi"}],
            )
    assert "gpt-4o" in str(exc.value)
    assert "upstream 500" in str(exc.value)
    assert isinstance(exc.value.__cause__, RuntimeError)


def test_chat_complete_unknown_model_bubbles_resolution_error():
    with pytest.raises(LLMProviderResolutionError):
        chat_complete(
            model="unknown-model-xyz",
            api_key="k",
            messages=[{"role": "user", "content": "hi"}],
        )
