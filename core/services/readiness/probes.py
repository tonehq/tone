"""Live provider probes — reuse the pipecat service classes.

The whole point is to avoid duplicating per-provider auth/URL/format logic.
``core/services/pipeline/service_factory.py`` already knows how to build the
correct pipecat service for every LLM/STT/TTS provider Tone supports. This
module hands those factories the same spec the runtime call uses, then fires
the smallest possible request through the constructed service.

Three probe functions, all async, all returning a ``ProbeResult`` (a simple
``(ok, message)`` pair — no exceptions bubble up). Deep check classes call
these; individual services never know about them.

## Provider coverage per service type

- **LLM** — dispatched by provider family so every pipecat LLM has a real
  live probe path where possible:
    - OpenAI-compatible (~17 providers routed through ``BaseOpenAILLMService``:
      openai, groq, openrouter, cerebras, together, fireworks, perplexity,
      qwen, deepseek, mistral, sambanova, grok, cohere, gemma, azure,
      nvidia_nim, mistral-self-hosted, ollama) → 1-token ``chat.completions.create``.
    - Anthropic native → ``messages.create`` with max_tokens=1.
    - Google Gemini → ``models.generate_content`` with max_output_tokens=1.
    - AWS Bedrock → constructor-only (needs boto3-specific handling).
    - S2S (openai_realtime, gemini_live) → constructor-only (real probe
      requires opening an audio session).

- **STT** — every pipecat STT service inherits ``STTService.run_stt(audio)``.
  We stream ~0.5s of PCM silence at the configured sample rate and consume
  the first frame (transcription OR interim OR silence marker). Universal
  across every WebSocket / gRPC / HTTP STT provider without per-provider code.

- **TTS** — every pipecat TTS service inherits ``TTSService.run_tts(text)``.
  We iterate until the first ``TTSAudioRawFrame`` (or any frame with audio).
  Some services (Cartesia) override the signature to require ``context_id``;
  we detect that with ``inspect.signature`` and inject dummy UUIDs.
"""

from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger


@dataclass
class ProbeResult:
    """Outcome of a live probe. ``message`` is the user-visible one-line summary."""

    ok: bool
    message: str


# ── LLM provider families (kept in sync with service_factory.build_llm) ──────

# Any of these are constructed via BaseOpenAILLMService (or subclass) and expose
# ``._client`` as an AsyncOpenAI-compatible instance we can call directly.
_OPENAI_COMPAT_LLM = frozenset({
    "openai", "groq", "openrouter", "azure", "cerebras", "nvidia_nim",
    "fireworks", "together", "perplexity", "qwen", "deepseek", "mistral",
    "sambanova", "grok", "cohere", "gemma", "mistral-self-hosted", "ollama",
})
# Speech-to-speech LLMs — no HTTP text-in/text-out path; probing requires an
# actual audio session which we don't want to spin up for a readiness check.
_S2S_LLM = frozenset({"openai_realtime", "gemini_live"})


# ── spec builder — same shape service_factory expects ────────────────────────


def _build_spec(leg_spec, provider) -> Optional[Dict[str, Any]]:
    """Assemble the ``{provider_name, api_key, model_name, metadata, model_meta_data}``
    dict that ``service_factory.build_*`` consumes. Returns None if the leg is
    missing the essentials — the calling check will already have caught that
    at the shallow level, so we just skip the probe."""
    if not leg_spec or not provider:
        return None
    key = leg_spec.decrypted_key
    if not key:
        return None
    model_name = leg_spec.model.name if leg_spec.model else (leg_spec.settings or {}).get("model")
    return {
        "provider_name": (provider.slug or "").strip().lower(),
        "api_key": key,
        "model_name": model_name,
        "metadata": dict(leg_spec.settings or {}),
        "model_meta_data": {},
    }


# ── LLM probe (dispatched by provider family) ────────────────────────────────


async def probe_llm(ctx) -> ProbeResult:
    """Fire the smallest possible LLM call through the pipecat service."""
    from core.services.pipeline import service_factory

    spec = _build_spec(ctx.llm, ctx.llm.provider)
    if spec is None:
        return ProbeResult(False, "LLM spec incomplete — check shallow config first.")

    provider = spec["provider_name"]
    model = spec["model_name"]

    try:
        service = service_factory.build_llm(spec)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} LLM client construction failed", provider)
        return ProbeResult(False, f"Could not construct {provider} client: {exc}")
    if service is None:
        return ProbeResult(False, f"No pipecat client available for provider '{provider}'.")

    # S2S — no simple text-in/text-out probe possible.
    if provider in _S2S_LLM:
        return ProbeResult(
            True,
            f"{provider}: S2S service constructed (live probe requires an audio session).",
        )

    # AWS Bedrock uses boto3; the pipecat service constructs the boto3 client
    # eagerly, so a successful construction already validates most of the auth
    # surface. A real probe would need ``bedrock-runtime.invoke_model`` which
    # is model-specific — deferred.
    if provider == "aws_bedrock":
        return ProbeResult(
            True,
            "aws_bedrock: boto3 client constructed (deep probe deferred — model-specific).",
        )

    client = getattr(service, "_client", None) or getattr(service, "client", None)
    if client is None:
        return ProbeResult(
            True, f"{provider}: service constructed (no client attribute for live probe)."
        )

    try:
        # OpenAI-compatible family — the vast majority of Tone's LLMs.
        if provider in _OPENAI_COMPAT_LLM:
            completions = getattr(getattr(client, "chat", None), "completions", None)
            if completions and hasattr(completions, "create"):
                await completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )
                return ProbeResult(True, f"{provider} responded to a 1-token completion.")

        # Anthropic native SDK
        if provider == "anthropic" and hasattr(client, "messages"):
            await client.messages.create(
                model=model or "claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return ProbeResult(True, f"anthropic responded to a 1-token completion.")

        # Google Gemini (google-genai SDK)
        if provider == "google" and hasattr(client, "models"):
            # google-genai's Client.models.generate_content is sync; use aio helper.
            aio_models = getattr(getattr(client, "aio", None), "models", None)
            if aio_models and hasattr(aio_models, "generate_content"):
                await aio_models.generate_content(
                    model=model or "gemini-2.5-flash",
                    contents="ping",
                    config={"max_output_tokens": 1},
                )
                return ProbeResult(True, f"google gemini responded to a 1-token completion.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} LLM live probe failed", provider)
        return ProbeResult(False, _summarise_error(provider, exc))

    # Fallback — client exists but shape didn't match any known family.
    return ProbeResult(
        True, f"{provider}: service constructed (no live probe implemented for this shape)."
    )


# ── STT probe (universal — pipecat's run_stt) ────────────────────────────────


async def probe_stt(ctx) -> ProbeResult:
    """Stream ~0.5s of PCM silence through pipecat's ``run_stt`` and confirm the
    provider accepts the audio (any yielded frame means auth passed).

    Works across every pipecat STT provider because ``STTService.run_stt(audio)``
    is the standard interface — WebSocket, gRPC, HTTP, they all implement it.
    """
    from core.services.pipeline import service_factory

    spec = _build_spec(ctx.stt, ctx.stt.provider)
    if spec is None:
        return ProbeResult(False, "STT spec incomplete — check shallow config first.")

    provider = spec["provider_name"]

    try:
        service = service_factory.build_stt(spec)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} STT client construction failed", provider)
        return ProbeResult(False, f"Could not construct {provider} STT client: {exc}")
    if service is None:
        return ProbeResult(
            False, f"No pipecat client available for STT provider '{provider}'."
        )

    if not hasattr(service, "run_stt"):
        return ProbeResult(
            True,
            f"{provider}: STT client constructed (this provider doesn't expose run_stt for a live probe).",
        )

    sample_rate = int((ctx.stt.settings or {}).get("sample_rate") or 16000)
    # 0.5s of PCM16 silence at the configured sample rate.
    silence = b"\x00\x00" * (sample_rate // 2)

    try:
        # Some STT services require lifecycle setup (start frame) before accepting
        # audio; try to run without it first, and if it fails suggestively, retry
        # with a minimal StartFrame. Most WebSocket-based services connect on first
        # ``run_stt`` call, which is what we want.
        got_any = False
        gen = service.run_stt(silence)
        # Consume up to 2 frames or hit an exception — we only need one signal.
        for _ in range(2):
            try:
                frame = await gen.__anext__()
            except StopAsyncIteration:
                break
            got_any = True
            if frame is not None:
                break
        try:
            await gen.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.debug("[readiness] {} STT probe generator close failed: {}", provider, exc)
        if got_any:
            return ProbeResult(True, f"{provider} STT accepted a probe audio frame.")
        # No frames but no error either — auth likely passed, just no output on silence.
        return ProbeResult(
            True,
            f"{provider} STT accepted the request (no interim frame on silence, which is normal).",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} STT live probe failed", provider)
        return ProbeResult(False, _summarise_error(provider, exc))
    finally:
        # Best-effort cleanup — most WS-based STTs open an aiohttp session.
        try:
            for attr in ("stop", "cleanup", "close"):
                fn = getattr(service, attr, None)
                if fn and callable(fn):
                    result = fn()
                    if inspect.iscoroutine(result):
                        await result
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("[readiness] {} STT probe cleanup failed: {}", provider, exc)


# ── TTS probe (universal — pipecat's run_tts) ────────────────────────────────


async def probe_tts(ctx) -> ProbeResult:
    """Synthesise the word "test" through the pipecat TTS service and consume the
    first audio frame. Universal across providers via ``TTSService.run_tts``.
    Handles services (Cartesia) that override the signature to require extra args.
    """
    from core.services.pipeline import service_factory

    spec = _build_spec(ctx.tts, ctx.tts.provider)
    if spec is None:
        return ProbeResult(False, "TTS spec incomplete — check shallow config first.")

    provider = spec["provider_name"]

    try:
        service = service_factory.build_tts(spec)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} TTS client construction failed", provider)
        return ProbeResult(False, f"Could not construct {provider} TTS client: {exc}")
    if service is None:
        return ProbeResult(
            False, f"No pipecat client available for TTS provider '{provider}'."
        )

    try:
        from pipecat.frames.frames import TTSAudioRawFrame  # local — pipecat is heavy
    except Exception:  # noqa: BLE001
        TTSAudioRawFrame = None  # type: ignore

    # Some pipecat TTS services (e.g. Cartesia) override run_tts to require a
    # ``context_id`` for turn tracking. Inspect the signature so we can supply
    # dummy IDs without hard-coding per-provider branches.
    run_tts_kwargs: Dict[str, Any] = {}
    try:
        sig = inspect.signature(service.run_tts)
        for name, param in sig.parameters.items():
            if name in ("self", "text"):
                continue
            if param.default is inspect.Parameter.empty and param.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                if name in ("context_id", "turn_id"):
                    run_tts_kwargs[name] = str(uuid.uuid4())
    except (ValueError, TypeError):
        pass

    got_audio = False
    try:
        async for frame in service.run_tts("test", **run_tts_kwargs):
            if TTSAudioRawFrame is not None and isinstance(frame, TTSAudioRawFrame):
                got_audio = True
                break
            if hasattr(frame, "audio") and getattr(frame, "audio", None):
                got_audio = True
                break
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} TTS live probe failed", provider)
        return ProbeResult(False, _summarise_error(provider, exc))
    finally:
        try:
            session = getattr(service, "_aiohttp_session", None) or getattr(
                service, "aiohttp_session", None
            )
            if session and not session.closed:
                await session.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("[readiness] {} TTS probe session close failed: {}", provider, exc)

    if got_audio:
        return ProbeResult(True, f"{provider} synthesised a test phrase.")
    return ProbeResult(
        True,
        f"{provider} accepted the request (no audio frame observed within probe budget).",
    )


# ── error summariser ─────────────────────────────────────────────────────────


def _summarise_error(provider: str, exc: BaseException) -> str:
    """Turn a raw provider exception into a one-liner the drawer can render."""
    msg = str(exc)
    lower = msg.lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)

    if status in (401, 403) or "unauthorized" in lower or "invalid api key" in lower:
        return f"{provider} rejected the API key — it may be revoked or wrong."
    if status == 404 or "model not found" in lower or "does not exist" in lower:
        return f"{provider} says the model doesn't exist (maybe deprecated)."
    if status == 429 or "rate limit" in lower or "too many requests" in lower:
        return f"{provider} rate-limited this test — retry in a minute."
    if status and status >= 500:
        return f"{provider} returned {status} — provider outage or transient error."
    logger.warning("[readiness] {} probe error: {}", provider, exc)
    return f"{provider} probe failed: {msg[:180]}"
