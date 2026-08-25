"""Shared chat-completion router — model name → LLM provider → SDK call.

Callers pass a model name, a pre-resolved API key, and OpenAI-shaped messages;
this module infers the provider from the model prefix (``gpt-*`` → openai,
``claude-*`` → anthropic, ``gemini-*``/``gemma-*`` → google), dispatches to the
right SDK, and normalises the response to plain text (or JSON-parseable text
when ``json_mode=True``).

Two public entry points:

- :func:`chat_complete` — the text-only path (unchanged) used everywhere in
  production for scenarios that don't need tool-calling.
- :func:`chat_complete_with_tools` — the tool-aware sibling used by the LLM
  eval executor: accepts an OpenAI-shaped ``tools=`` list and returns a
  :class:`ChatCompletion` carrying both the model's text ``content`` and any
  ``tool_calls`` (``[ToolCallIntent(name, arguments)]``) the model emitted.
  It does NOT execute the tools — the eval judge grades the intent
  deterministically.

Side-effect free — no DB access, no key lookup — so it stays unit-testable
without a session. Callers resolve the per-org API key via
``ProviderKeyService.get_key(db, org_id, resolve_provider(model))``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, List, Optional

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


# ── Tool-aware entry point + dataclasses ──────────────────────────────────


@dataclass
class ToolCallIntent:
    """One tool the model asked to call. The eval executor captures this
    as-is; it does NOT execute the tool. ``arguments`` is the parsed
    argument dict — providers return arguments as a JSON string, we
    ``json.loads`` it here so callers get a native dict."""

    name: str
    arguments: dict


@dataclass
class ChatCompletion:
    """The tool-aware completion shape returned by
    :func:`chat_complete_with_tools`.

    ``content`` may be ``None`` when the model emitted ONLY tool calls
    (some providers return empty text in that case). ``tool_calls`` is
    ``[]`` when the model replied purely in text — that's the common
    case and matches the today-behavior of :func:`chat_complete`."""

    content: Optional[str]
    tool_calls: List[ToolCallIntent] = field(default_factory=list)


def chat_complete_with_tools(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    tools: List[dict],
    temperature: float = 0.0,
    max_tokens: int = 4096,
    tool_choice: str = "auto",
) -> ChatCompletion:
    """Tool-aware sibling of :func:`chat_complete`.

    ``tools`` uses the OpenAI tool-schema shape:
    ``[{"type": "function", "function": {"name", "description", "parameters"}}]``.
    Anthropic + Google mappings live inside each per-provider dispatcher —
    callers never build provider-specific payloads.

    The model may choose to reply in text (``content`` populated,
    ``tool_calls`` empty), emit tool calls (``content`` may be ``None`` or
    a short preamble, ``tool_calls`` populated), or both.

    Does NOT execute any tool — this function only captures the model's
    tool-use INTENT so the eval judge can grade decision-making without
    real side effects.

    Raises:
        LLMProviderResolutionError: model prefix is unknown.
        LLMChatCompletionError: SDK call raised, or both content and
            tool_calls came back empty (nothing to score).
    """
    provider = resolve_provider(model)
    logger.info(
        "[llm] chat_complete_with_tools provider={} model={} tools={} messages={}",
        provider, model, len(tools or []), len(messages),
    )
    try:
        if provider == "openai":
            completion = _call_openai_with_tools(
                model=model,
                api_key=api_key,
                messages=messages,
                tools=tools,
                temperature=temperature,
                tool_choice=tool_choice,
                max_tokens=max_tokens,
            )
        elif provider == "anthropic":
            completion = _call_anthropic_with_tools(
                model=model,
                api_key=api_key,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif provider == "google":
            completion = _call_google_with_tools(
                model=model,
                api_key=api_key,
                messages=messages,
                tools=tools,
                temperature=temperature,
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
            "[llm] chat_complete_with_tools failed provider={} model={}",
            provider, model,
        )
        raise LLMChatCompletionError(
            f"chat_complete_with_tools failed (provider={provider}, "
            f"model={model}): {type(exc).__name__}: {exc}"
        ) from exc

    if not completion.content and not completion.tool_calls:
        raise LLMChatCompletionError(
            f"chat_complete_with_tools returned no content and no tool_calls "
            f"(provider={provider}, model={model}) — nothing to score."
        )
    # Tool argument values may contain PII scraped from the scenario — never
    # log them at INFO. Log names + counts here, arg dicts only at DEBUG.
    logger.info(
        "[llm] chat_complete_with_tools content_chars={} tool_calls={} names={}",
        len(completion.content or ""),
        len(completion.tool_calls),
        [t.name for t in completion.tool_calls],
    )
    return completion


def _parse_tool_arguments(raw: Any, *, tool_name: str) -> dict:
    """Coerce a provider's ``arguments`` payload to a JSON-safe native ``dict``.

    OpenAI + Anthropic return JSON strings; Google returns ``MapComposite``
    (a ``Mapping`` subclass, NOT a ``dict`` subclass) with values that may
    include ``proto`` messages / ``Struct`` / ``datetime`` — all of which
    ``psycopg2.json.dumps`` refuses at persist time.

    Guarantees:
    - Return value is ALWAYS a plain ``dict`` (never a Mapping subclass).
    - Every leaf value is JSON-serializable (``default=str`` coerces the
      leftover proto / datetime types).
    - On parse failure log a WARNING (non-fatal — the tool-call intent
      still counts) and fall back to ``{}``.

    Detecting ``Mapping`` first (before the ``in (None, "")`` guard) is
    load-bearing: Google's ``MapComposite`` is not a ``dict`` subclass but
    IS a ``Mapping``, so the old ``isinstance(raw, dict)`` check let it
    fall through to ``json.loads`` and silently lose every arg.
    """
    if raw is None or raw == "":
        return {}
    if isinstance(raw, Mapping):
        try:
            return json.loads(json.dumps(dict(raw), default=str))
        except (TypeError, ValueError):
            logger.warning(
                "[llm] tool-call arguments (Mapping) failed to json-normalize "
                "tool={} raw_type={}",
                tool_name, type(raw).__name__,
            )
            return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning(
            "[llm] tool-call arguments failed to parse tool={} raw_type={}",
            tool_name, type(raw).__name__,
        )
        return {}
    if not isinstance(parsed, Mapping):
        # Provider returned a valid JSON but non-object shape (e.g. list) —
        # we can't map it to named args, degrade to {} rather than crash.
        logger.warning(
            "[llm] tool-call arguments parsed to non-object tool={} type={}",
            tool_name, type(parsed).__name__,
        )
        return {}
    # Round-trip once more so any nested non-JSON-native values (Decimal,
    # datetime) that survived json.loads via a custom decoder get coerced.
    return json.loads(json.dumps(dict(parsed), default=str))


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


# ── Per-provider tool-aware dispatchers ────────────────────────────────────


def _call_openai_with_tools(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    tools: List[dict],
    temperature: float,
    tool_choice: str,
    max_tokens: int,
) -> "ChatCompletion":
    """OpenAI tool-calling native format matches our public ``tools=`` shape
    1:1 — pass-through, then extract ``choices[0].message.tool_calls``.

    Forwards ``max_tokens`` so behavior matches the Anthropic + Google
    branches — an eval that pins ``max_tokens=256`` for concise tool-call
    output MUST see the same cap on every provider or per-provider cost
    and latency numbers diverge in the scorecard."""
    import openai

    client = openai.OpenAI(api_key=api_key)
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message
    content = (msg.content or "").strip() or None
    intents: List[ToolCallIntent] = []
    for tc in getattr(msg, "tool_calls", None) or []:
        fn = getattr(tc, "function", None)
        if fn is None:
            continue
        intents.append(ToolCallIntent(
            name=fn.name,
            arguments=_parse_tool_arguments(fn.arguments, tool_name=fn.name),
        ))
    return ChatCompletion(content=content, tool_calls=intents)


def _call_anthropic_with_tools(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    tools: List[dict],
    temperature: float,
    max_tokens: int,
) -> "ChatCompletion":
    """Anthropic uses a different tool-schema shape (top-level ``name`` /
    ``description`` / ``input_schema``). Convert from OpenAI shape here so
    every caller in the codebase speaks one dialect."""
    import anthropic

    system_prompt, user_messages = _split_system_message(messages)
    anthropic_tools = [
        {
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "input_schema": t["function"].get(
                "parameters", {"type": "object", "properties": {}}
            ),
        }
        for t in (tools or [])
        if isinstance(t, dict) and isinstance(t.get("function"), dict)
    ]
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": user_messages,
        "temperature": temperature,
    }
    if anthropic_tools:
        kwargs["tools"] = anthropic_tools
    if system_prompt:
        kwargs["system"] = system_prompt
    resp = client.messages.create(**kwargs)

    text_parts: List[str] = []
    intents: List[ToolCallIntent] = []
    for block in resp.content or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(getattr(block, "text", "") or "")
        elif block_type == "tool_use":
            intents.append(ToolCallIntent(
                name=getattr(block, "name", "") or "",
                arguments=_parse_tool_arguments(
                    getattr(block, "input", None),
                    tool_name=getattr(block, "name", "") or "",
                ),
            ))
    content = "".join(text_parts).strip() or None
    return ChatCompletion(content=content, tool_calls=intents)


def _call_google_with_tools(
    *,
    model: str,
    api_key: str,
    messages: List[dict],
    tools: List[dict],
    temperature: float,
    max_tokens: int,
) -> "ChatCompletion":
    """Google Gemini expects a ``Tool(function_declarations=[...])`` wrapper;
    strips the ``type: object`` requirement on parameters when absent so the
    OpenAI-shape schemas pass through."""
    from google import genai as google_genai
    from google.genai import types as google_genai_types

    client = google_genai.Client(api_key=api_key)
    system_prompt, user_messages = _split_system_message(messages)
    contents = _messages_to_google_contents(user_messages)

    function_declarations = [
        {
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "parameters": t["function"].get(
                "parameters", {"type": "object", "properties": {}}
            ),
        }
        for t in (tools or [])
        if isinstance(t, dict) and isinstance(t.get("function"), dict)
    ]

    config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if system_prompt:
        config_kwargs["system_instruction"] = system_prompt
    if function_declarations:
        config_kwargs["tools"] = [
            google_genai_types.Tool(function_declarations=function_declarations)
        ]
    config = google_genai_types.GenerateContentConfig(**config_kwargs)

    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    text_parts: List[str] = []
    intents: List[ToolCallIntent] = []
    for candidate in getattr(resp, "candidates", None) or []:
        content_obj = getattr(candidate, "content", None)
        for part in getattr(content_obj, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                text_parts.append(part_text)
            fc = getattr(part, "function_call", None)
            if fc is not None:
                intents.append(ToolCallIntent(
                    name=getattr(fc, "name", "") or "",
                    arguments=_parse_tool_arguments(
                        getattr(fc, "args", None),
                        tool_name=getattr(fc, "name", "") or "",
                    ),
                ))
    content = "".join(text_parts).strip() or None
    return ChatCompletion(content=content, tool_calls=intents)


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
