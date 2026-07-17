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

import audioop
import inspect
import uuid
import wave
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Dict, Optional, Tuple

from loguru import logger


# ── Probe payloads (fixed constants — see plan for rationale) ────────────────
# Kept module-level so all three probe functions read from ONE source of truth.
# Changing them is a one-line edit; no per-provider text lives in this file.

_LLM_PROBE_PROMPT = "Reply with the single word OK."
_TTS_PROBE_TEXT = "This is a readiness test."

# Bundled STT audio asset — native rate the WAV is encoded at. Resampled per
# provider at probe time via `audioop.ratecv` when the STT service is
# configured for a different rate.
_STT_PROBE_SAMPLE_RATE = 16000
_STT_PROBE_ASSET = "probe_sample.wav"


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
                    messages=[{"role": "user", "content": _LLM_PROBE_PROMPT}],
                    max_tokens=1,
                )
                return ProbeResult(True, f"{provider} responded to a sentence prompt.")

        # Anthropic native SDK
        if provider == "anthropic" and hasattr(client, "messages"):
            await client.messages.create(
                model=model or "claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": _LLM_PROBE_PROMPT}],
            )
            return ProbeResult(True, "anthropic responded to a sentence prompt.")

        # Google Gemini (google-genai SDK)
        if provider == "google" and hasattr(client, "models"):
            # google-genai's Client.models.generate_content is sync; use aio helper.
            aio_models = getattr(getattr(client, "aio", None), "models", None)
            if aio_models and hasattr(aio_models, "generate_content"):
                await aio_models.generate_content(
                    model=model or "gemini-2.5-flash",
                    contents=_LLM_PROBE_PROMPT,
                    config={"max_output_tokens": 1},
                )
                return ProbeResult(True, "google gemini responded to a sentence prompt.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} LLM live probe failed", provider)
        return ProbeResult(False, _summarise_error(provider, exc))

    # Fallback — client exists but shape didn't match any known family.
    return ProbeResult(
        True, f"{provider}: service constructed (no live probe implemented for this shape)."
    )


# ── STT probe (universal — pipecat's run_stt) ────────────────────────────────


async def probe_stt(ctx) -> ProbeResult:
    """Stream ~5-7s of real recorded speech through pipecat's ``run_stt`` and
    confirm the provider returns a non-empty transcript.

    Works across every pipecat STT provider because ``STTService.run_stt(audio)``
    is the standard interface. When the bundled audio asset is unavailable
    (fresh clone before someone commits the WAV), we fall back to a 0.5s
    silence probe — enough to prove auth + session but not transcription
    quality — and say so in the message so the caller isn't misled.
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

    target_rate = int((ctx.stt.settings or {}).get("sample_rate") or _STT_PROBE_SAMPLE_RATE)
    audio_bytes, using_real_audio = _load_stt_audio(target_rate)

    # Lazy import — pipecat is heavy and this module is imported at API startup.
    try:
        from pipecat.frames.frames import (
            InterimTranscriptionFrame,
            TranscriptionFrame,
        )
        _transcript_types: Tuple[type, ...] = (TranscriptionFrame, InterimTranscriptionFrame)
    except Exception:  # noqa: BLE001
        _transcript_types = ()

    try:
        transcript_text: Optional[str] = None
        got_any = False
        async for frame in service.run_stt(audio_bytes):
            got_any = True
            if frame is None:
                continue
            # Providers vary in which frame type carries the final vs interim
            # text — accept either, since both prove the model decoded speech.
            text = _extract_transcript_text(frame, _transcript_types)
            if text:
                transcript_text = text
                break
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

    if transcript_text:
        snippet = transcript_text.strip().replace("\n", " ")[:60]
        return ProbeResult(True, f"{provider} STT transcribed: '{snippet}'")

    if not using_real_audio:
        # No transcript expected — the WAV asset wasn't available so we sent
        # silence. Auth + session are still verified.
        return ProbeResult(
            True,
            f"{provider} STT accepted the request (bundled probe WAV missing — silence-only probe).",
        )

    if got_any:
        # We got frames but none carried transcribed text within the window —
        # likely a provider that only emits finals after the whole session
        # closes, or a language-mismatch that produced empty text.
        return ProbeResult(
            False,
            f"{provider} STT returned frames but no transcript text — check language/model settings.",
        )
    return ProbeResult(
        False, f"{provider} STT returned no frames for the probe audio."
    )


# ── STT audio helpers ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_probe_pcm16() -> Optional[Tuple[bytes, int]]:
    """Read the bundled PCM16 mono WAV once. Returns ``(pcm_bytes, sample_rate)``
    or ``None`` when the asset is missing/invalid — callers handle the fallback.

    Cached because the file is small and re-reading on every probe is wasteful.
    Uses stdlib ``wave`` + ``importlib.resources`` so the asset stays inside the
    package and works both from source and from a wheel install.
    """
    try:
        asset = files("core.services.readiness.assets") / _STT_PROBE_ASSET
    except (ModuleNotFoundError, FileNotFoundError):
        return None
    try:
        with asset.open("rb") as raw:
            with wave.open(raw, "rb") as wav:
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                    logger.warning(
                        "[readiness] STT probe asset must be mono PCM16; "
                        "got channels={}, sampwidth={}",
                        wav.getnchannels(),
                        wav.getsampwidth(),
                    )
                    return None
                return wav.readframes(wav.getnframes()), wav.getframerate()
    except (FileNotFoundError, OSError, wave.Error) as exc:
        logger.debug("[readiness] STT probe asset unavailable: {}", exc)
        return None


def _load_stt_audio(target_rate: int) -> Tuple[bytes, bool]:
    """Return ``(pcm_bytes, using_real_audio)`` for the STT probe.

    Prefers the bundled WAV, resampled to ``target_rate`` via stdlib
    ``audioop.ratecv``. Falls back to 0.5s of PCM16 silence at ``target_rate``
    when the asset isn't committed yet — the second-return-value tells the
    caller whether transcription is a valid expectation.
    """
    loaded = _load_probe_pcm16()
    if loaded is None:
        silence = b"\x00\x00" * (target_rate // 2)
        return silence, False
    pcm, native_rate = loaded
    if target_rate == native_rate:
        return pcm, True
    # ``ratecv`` needs an opaque state on first call; None is the seed.
    converted, _ = audioop.ratecv(pcm, 2, 1, native_rate, target_rate, None)
    return converted, True


def _extract_transcript_text(frame, transcript_types: Tuple[type, ...]) -> Optional[str]:
    """Pull a non-empty ``.text`` out of a pipecat transcript frame, if present.

    Matches on ``TranscriptionFrame`` / ``InterimTranscriptionFrame`` via
    ``isinstance`` when the types are importable, else falls back to duck-typing
    on the ``.text`` attribute. Both paths ignore whitespace-only strings so a
    provider that emits `" "` between real chunks isn't treated as a transcript.
    """
    if transcript_types and isinstance(frame, transcript_types):
        text = getattr(frame, "text", None)
    else:
        text = getattr(frame, "text", None) if hasattr(frame, "text") else None
    if isinstance(text, str) and text.strip():
        return text
    return None


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
        async for frame in service.run_tts(_TTS_PROBE_TEXT, **run_tts_kwargs):
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
        return ProbeResult(True, f"{provider} synthesised a sentence.")
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
