"""Shared chat-completion router — model name → LLM provider → SDK call.

Callers pass a model name, a pre-resolved API key, and OpenAI-shaped messages;
this module infers the provider from the model prefix (``gpt-*`` → openai,
``claude-*`` → anthropic, ``gemini-*``/``gemma-*`` → google), dispatches to the
right SDK, and normalises the response to plain text (or JSON-parseable text
when ``json_mode=True``).

Side-effect free — no DB access, no key lookup — so it stays unit-testable
without a session. Callers resolve the per-org API key via
``ProviderKeyService.get_key(db, org_id, resolve_provider(model))``.
"""

from __future__ import annotations

from typing import List, Optional

from loguru import logger

from core.services.llm.errors import (
    LLMChatCompletionError,
    LLMProviderResolutionError,
)


# Prefix → provider slug. Matches the ``model_providers.provider_id`` values
# used by ``ProviderKeyService``. Case-insensitive matching in
# ``resolve_provider``.
_PROVIDER_PREFIXES: List[tuple] = [
    ("openai", ("gpt-", "o1-", "o3-", "o4-", "chatgpt-", "davinci-", "text-embedding-")),
    ("anthropic", ("claude-",)),
    ("google", ("gemini-", "gemma-", "models/gemini-")),
]

_KNOWN_PREFIXES_HINT = ", ".join(
    prefix for _, prefixes in _PROVIDER_PREFIXES for prefix in prefixes
)


def resolve_provider(model: str) -> str:
    """Return the provider slug for ``model`` (``"openai"`` / ``"anthropic"``
    / ``"google"``). Raises ``LLMProviderResolutionError`` for unknown
    prefixes so the caller can surface an actionable error on the eval-run row.
    """
    if not model:
        raise LLMProviderResolutionError(
            "Model name is empty — cannot resolve provider."
        )
    lowered = model.strip().lower()
    for provider, prefixes in _PROVIDER_PREFIXES:
        if any(lowered.startswith(p) for p in prefixes):
            return provider
    raise LLMProviderResolutionError(
        f"Unknown model {model!r} — no provider prefix matched "
        f"(known prefixes: {_KNOWN_PREFIXES_HINT})."
    )


def chat_complete(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    temperature: float = 0.0,
    json_mode: bool = False,
    max_tokens: int = 4096,
) -> str:
    """Send a chat completion to the provider inferred from ``model`` and
    return the response as a plain string.

    ``messages`` uses OpenAI shape: ``[{"role": "system"|"user"|"assistant",
    "content": str}, ...]``. Anthropic and Google mappings live inside this
    function; callers never build provider-specific payloads.

    Raises:
        LLMProviderResolutionError: model prefix is unknown.
        LLMChatCompletionError: SDK call raised, or returned empty content.
    """
    provider = resolve_provider(model)
    logger.info(
        "[llm] chat_complete provider={} model={} json_mode={} messages={}",
        provider, model, json_mode, len(messages),
    )
    try:
        if provider == "openai":
            content = _call_openai(
                model=model,
                api_key=api_key,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
            )
        elif provider == "anthropic":
            content = _call_anthropic(
                model=model,
                api_key=api_key,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=max_tokens,
            )
        elif provider == "google":
            content = _call_google(
                model=model,
                api_key=api_key,
                messages=messages,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=max_tokens,
            )
        else:  # pragma: no cover — resolve_provider guarantees one of the above
            raise LLMChatCompletionError(
                f"Unsupported provider {provider!r} for model {model!r}"
            )
    except LLMChatCompletionError:
        raise
    except Exception as exc:
        logger.exception(
            "[llm] chat_complete failed provider={} model={}", provider, model,
        )
        raise LLMChatCompletionError(
            f"chat_complete failed (provider={provider}, model={model}): "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if not content:
        raise LLMChatCompletionError(
            f"chat_complete returned empty content (provider={provider}, "
            f"model={model})"
        )
    return content


# ── Per-provider dispatchers ──────────────────────────────────────────────


def _call_openai(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    temperature: float,
    json_mode: bool,
) -> str:
    import openai

    client = openai.OpenAI(api_key=api_key)
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def _call_anthropic(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    temperature: float,
    json_mode: bool,
    max_tokens: int,
) -> str:
    import anthropic

    system_prompt, user_messages = _split_system_message(messages)
    if json_mode and user_messages:
        # Anthropic has no native ``response_format``; nudge the last user
        # message so the model stays inside the JSON contract the eval prompts
        # already ask for. Belt-and-braces — the prompt itself is authoritative.
        last = dict(user_messages[-1])
        last["content"] = (
            f"{last.get('content', '')}\n\nReturn valid JSON only, no prose."
        )
        user_messages = user_messages[:-1] + [last]

    client = anthropic.Anthropic(api_key=api_key)
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": user_messages,
        "temperature": temperature,
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    resp = client.messages.create(**kwargs)
    return "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    ).strip()


def _call_google(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    temperature: float,
    json_mode: bool,
    max_tokens: int,
) -> str:
    from google import genai as google_genai
    from google.genai import types as google_genai_types

    client = google_genai.Client(api_key=api_key)
    system_prompt, user_messages = _split_system_message(messages)
    contents = _messages_to_google_contents(user_messages)

    config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    if system_prompt:
        config_kwargs["system_instruction"] = system_prompt
    config = google_genai_types.GenerateContentConfig(**config_kwargs)

    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    text = getattr(resp, "text", None)
    if text:
        return text.strip()
    # Fallback: walk candidates/parts. Some SDK builds only populate
    # ``.text`` for single-candidate responses.
    parts_text: List[str] = []
    for candidate in getattr(resp, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                parts_text.append(part_text)
    return "".join(parts_text).strip()


# ── Helpers ───────────────────────────────────────────────────────────────


def _split_system_message(messages: List[dict]) -> tuple:
    """Split OpenAI-shaped messages into (system_prompt, user_messages).

    Anthropic and Google both take the system prompt separately from the
    conversation turns; OpenAI mixes them into a single list. Concatenates
    multiple system messages (rare in the eval flow, but preserves them).
    """
    system_parts: List[str] = []
    remaining: List[dict] = []
    for m in messages:
        if m.get("role") == "system":
            content = m.get("content")
            if content:
                system_parts.append(str(content))
        else:
            remaining.append(m)
    system_prompt: Optional[str] = "\n\n".join(system_parts) if system_parts else None
    return system_prompt, remaining


def _messages_to_google_contents(messages: List[dict]) -> List[dict]:
    """Convert OpenAI-shaped turns to google-genai ``contents`` shape.

    ``role`` maps ``assistant`` → ``model``; everything else defaults to
    ``user``. ``content`` is wrapped as a single text part.
    """
    contents: List[dict] = []
    for m in messages:
        role = "model" if m.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})
    return contents
