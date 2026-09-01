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

- **LLM** — every non-S2S pipecat LLM (OpenAI-compat family, Anthropic,
  Google Gemini, AWS Bedrock) accepts ``LLMContextFrame`` through
  ``LLMService.process_frame``. We feed one via the shared pipeline harness,
  cap the response with ``LLMUpdateSettingsFrame`` (max_completion_tokens=16
  covers OpenAI reasoning models too), and wait for the first ``LLMTextFrame``
  or ``LLMFullResponseEndFrame``. S2S (openai_realtime, gemini_live) still
  skips the live probe — the frame flow needs a real audio session.

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
import io
import re
import uuid
import wave
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Dict, Optional, Tuple

from loguru import logger


# pipecat STT service classes that upload a full audio file (multipart HTTP)
# instead of streaming raw PCM over a WebSocket. Matched by ``type().__name__``
# because pipecat's module paths vary and duck-typing is more resilient than
# an isinstance check across many optional-import paths. Add a class here when
# a new HTTP-batch STT provider is wired in.
_HTTP_STT_SERVICE_CLASSES = frozenset({
    "OpenAISTTService",       # Whisper via /audio/transcriptions
    "GroqSTTService",         # Whisper-family via /audio/transcriptions
    "SarvamHttpSTTService",   # Sarvam HTTP endpoint
    "ElevenLabsSTTService",   # ElevenLabs speech-to-text is HTTP
})


# ── Probe payloads (fixed constants — see plan for rationale) ────────────────
# Kept module-level so all three probe functions read from ONE source of truth.
# Changing them is a one-line edit; no per-provider text lives in this file.

_LLM_PROBE_PROMPT = "Reply with the single word OK."
_TTS_PROBE_TEXT = "This is a readiness test."
# Hard cap on the probe's completion length — the probe only needs to prove the
# provider streamed a token, so keep it tiny to bound cost. Small enough that a
# reasoning model spends its budget on reasoning and closes with an
# LLMFullResponseEndFrame (still a valid round-trip), which the probe accepts.
_LLM_PROBE_TOKEN_CAP = 32

# Bundled STT audio asset — native rate the WAV is encoded at. Resampled per
# provider at probe time via `audioop.ratecv` when the STT service is
# configured for a different rate.
_STT_PROBE_SAMPLE_RATE = 16000
_STT_PROBE_ASSET = "probe_sample.wav"


@dataclass
class ProbeResult:
    """Outcome of a live probe. ``message`` is the user-visible one-line summary.

    ``timed_out`` distinguishes "the provider didn't answer within the budget"
    (slow / warming up — a WARNING, must NOT block publish) from a confirmed
    failure like a bad key or exhausted credit (a BLOCKER). Deep checks read
    this to pick the severity.
    """

    ok: bool
    message: str
    timed_out: bool = False


# Speech-to-speech LLMs — probing requires an actual audio session which we
# don't want to spin up for a readiness check. The pipecat pipeline path is
# skipped for these; construction alone still validates most of the auth
# surface.
_S2S_LLM = frozenset({"openai_realtime", "gemini_live"})


# ── spec builder — same shape service_factory expects ────────────────────────


def _build_spec(ctx, service_type: str) -> Optional[Dict[str, Any]]:
    """Resolve the ``{provider_name, api_key, model_name, metadata, model_meta_data}``
    spec by delegating to the SAME resolver real calls use
    (``service_resolver._build_service_specs``).

    Historical bugs (Cartesia ``voice_not_found``, Google ``extra_forbidden
    max_completion_tokens``, MiniMax language enum validation, ``base_url``
    ignored on self-hosted deployments) all traced to the probe hand-rolling
    a simplified copy of the resolver and missing individual transformations
    one by one. Routing through the resolver instead means every
    transformation flows automatically: voice-ID resolution, ``language_code``
    preference, ``Model.base_url`` injection with provider-match guard,
    model-schema filtering, ``ApiKey`` fallback by service_type, S2S
    system-prompt injection — and any future transformation the resolver
    adds for real calls.

    The resolver's output is cached on the readiness ``ctx`` so probing all
    three service types (LLM/STT/TTS) only builds specs once per readiness
    run.

    Returns ``None`` if the required inputs (config/org_id/db, or the leg
    itself) aren't resolvable — the calling shallow checks will already have
    surfaced that as a specific FAIL, so we just skip the deep probe.
    """
    config = getattr(ctx, "config", None)
    org_id = getattr(ctx, "org_id", None)
    db = getattr(ctx, "db", None)
    if config is None or org_id is None or db is None:
        return None

    cached = getattr(ctx, "_probe_service_specs_cache", None)
    if cached is None:
        try:
            from core.services.pipeline.service_resolver import _build_service_specs
            llm_spec, stt_spec, tts_spec, _is_s2s = _build_service_specs(
                db, org_id, config
            )
        except Exception:
            logger.exception(
                "[readiness] service_resolver._build_service_specs failed — "
                "probe cannot proceed without a resolved spec"
            )
            return None
        cached = {"llm": llm_spec, "stt": stt_spec, "tts": tts_spec}
        try:
            ctx._probe_service_specs_cache = cached  # type: ignore[attr-defined]
        except AttributeError:
            # ctx may be a dataclass with slots or immutable — caching is an
            # optimization, not correctness-critical. Fall through and pay
            # the resolver cost per probe.
            pass

    return cached.get(service_type)


# ── LLM probe (dispatched by provider family) ────────────────────────────────


async def probe_llm(ctx) -> ProbeResult:
    """Run a one-message inference through the pipecat LLM pipeline.

    Same frame flow as production: ``LLMContextFrame(context=LLMContext([user
    msg])) -> service -> LLMFullResponseStartFrame + LLMTextFrame(s) +
    LLMFullResponseEndFrame``. Waiting on ``LLMTextFrame`` proves the provider
    accepted the request AND the pipecat ``LLMService`` wrapper streams
    tokens correctly — the wrapper is the thing that would silently break if
    a provider tweaks their stream format, and it's exactly what runs on a
    real call.
    """
    from core.services.pipeline import service_factory

    spec = _build_spec(ctx, "llm")
    if spec is None:
        return ProbeResult(False, "LLM spec incomplete — check shallow config first.")

    provider = spec["provider_name"]

    # Bake the probe's cost cap into metadata so ``build_input_params``
    # (see service_factory) filters each key against the provider's
    # ``InputParams.model_fields`` before construction. Keys the provider
    # doesn't declare are dropped silently — e.g. Google/Anthropic/AWS
    # Bedrock don't have ``max_completion_tokens``; sending it via
    # ``LLMUpdateSettingsFrame`` at runtime instead trips Google's
    # strict-mode ``GenerateContentConfig`` (``extra_forbidden``) and
    # false-flags a healthy provider. Overriding the user's own
    # ``max_tokens`` is intentional: probe cost must stay bounded even
    # when the agent's model is configured with a large budget.
    # Provider-aware token cap: send EXACTLY ONE cap key per provider family.
    # Sending BOTH ``max_tokens`` and ``max_completion_tokens`` is rejected by
    # both Cohere (HTTP 422) and OpenAI (HTTP 400 "Setting 'max_tokens' and
    # 'max_completion_tokens' at the same time is not supported"). Pipecat's
    # ``InputParams`` for OpenAI-family services declares BOTH fields — so
    # ``build_input_params`` doesn't filter either out — but the underlying
    # SDK/API server insists we pick one. We pick:
    #   * OpenAI-family (openai, azure, groq, openrouter, deepseek, cerebras,
    #     fireworks, perplexity, sambanova, nebius, together, xai, grok,
    #     novita, qwen, inception) → ``max_completion_tokens`` (the newer,
    #     non-deprecated field; required by reasoning models o1/o3/o4/gpt-5
    #     and accepted by legacy chat models on modern SDK versions).
    #   * Everyone else (Anthropic, Google, Bedrock, Cohere, Mistral, Nvidia,
    #     Sarvam, Ollama) → ``max_tokens`` (their SDKs only declare this).
    _OPENAI_FAMILY = {
        "openai", "azure", "groq", "openrouter", "deepseek", "cerebras",
        "fireworks", "perplexity", "sambanova", "nebius", "together",
        "xai", "grok", "novita", "qwen", "inception",
    }
    if provider in _OPENAI_FAMILY:
        token_cap: Dict[str, Any] = {"max_completion_tokens": _LLM_PROBE_TOKEN_CAP}
    else:
        token_cap = {"max_tokens": _LLM_PROBE_TOKEN_CAP}
    spec["metadata"] = {**(spec["metadata"] or {}), **token_cap}

    try:
        service = service_factory.build_llm(spec)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} LLM client construction failed", provider)
        return ProbeResult(False, f"Could not construct {provider} client: {exc}")
    if service is None:
        return ProbeResult(False, f"No pipecat client available for provider '{provider}'.")

    # S2S LLMs are gated OUT at the check's ``applies()`` level (see
    # LLMProviderReachableCheck), so we should never reach here with one.
    # Guard defensively — returning a False PASS here would re-open the
    # silent-pass bug we just fixed.
    if provider in _S2S_LLM:
        return ProbeResult(
            False,
            f"{provider}: S2S LLM cannot be live-probed without an audio session.",
        )

    from pipecat.frames.frames import (
        EndFrame,
        LLMContextFrame,
        LLMFullResponseEndFrame,
        LLMTextFrame,
    )
    from pipecat.pipeline.task import PipelineParams
    from pipecat.processors.aggregators.llm_context import LLMContext
    from core.services.readiness.probe_pipeline import probe_in_pipeline

    def _is_llm_response(frame) -> bool:
        # An LLMTextFrame with any non-empty text is unambiguous proof the
        # provider streamed a token through the pipecat wrapper.
        if isinstance(frame, LLMTextFrame):
            return bool((getattr(frame, "text", "") or "").strip())
        # LLMFullResponseEndFrame covers edge cases where a provider closes the
        # response without emitting visible text (e.g. all tokens spent on
        # reasoning within our tiny budget). The auth/wrapper path is still
        # proven; we just can't quote a snippet.
        return isinstance(frame, LLMFullResponseEndFrame)

    llm_context = LLMContext(messages=[{"role": "user", "content": _LLM_PROBE_PROMPT}])
    input_frames = [
        LLMContextFrame(context=llm_context),
        EndFrame(),
    ]
    params = PipelineParams(
        audio_in_sample_rate=16000,
        audio_out_sample_rate=24000,
        enable_metrics=False,
    )

    try:
        ok, frame, err_msg = await probe_in_pipeline(
            service,
            input_frames,
            _is_llm_response,
            params=params,
            timeout_s=20.0,   # under the check's 25s wrapper — leave room for teardown
            provider=provider,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} LLM pipeline harness raised", provider)
        return ProbeResult(False, _summarise_error(provider, exc))

    if ok and isinstance(frame, LLMTextFrame):
        snippet = (getattr(frame, "text", "") or "").strip().replace("\n", " ")[:60]
        return ProbeResult(True, f"{provider} LLM responded: '{snippet}'")
    if ok:
        # Response end without visible text — still a valid pipeline round-trip.
        return ProbeResult(
            True, f"{provider} LLM completed the round-trip (no visible text within budget)."
        )
    if err_msg:
        return ProbeResult(False, _summarise_error_text(provider, err_msg))
    # err_msg is None → pure timeout: no frame, no ErrorFrame, no exception.
    # Slow / warming up, NOT confirmed-broken → flag it so the check renders a
    # WARNING instead of a publish-blocking BLOCKER.
    return ProbeResult(
        False,
        f"{provider} didn't respond within the time limit — it may be slow or "
        "warming up. Run the deep test again in a moment.",
        timed_out=True,
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

    spec = _build_spec(ctx, "stt")
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

    target_rate = int((ctx.stt.settings or {}).get("sample_rate") or _STT_PROBE_SAMPLE_RATE)
    audio_bytes, using_real_audio = _load_stt_audio(target_rate, service)

    # Feed the service inside a minimal pipecat pipeline — same
    # PipelineTask + StartFrame + lifecycle as production, minus the
    # transport.
    #
    # Frame classes MATTER here. Pipecat's ``STTService`` base handles
    # ``VADUserStartedSpeakingFrame`` / ``VADUserStoppedSpeakingFrame``
    # (see ``pipecat/services/stt_service.py:267-271``). The runtime
    # transport (``pipecat/transports/base_input.py:394-396``) emits those
    # VAD-prefixed classes, not the plain ``UserStartedSpeakingFrame`` /
    # ``UserStoppedSpeakingFrame`` — those two are separate SystemFrame
    # subclasses (no inheritance relationship), so ``isinstance`` checks in
    # the STT base don't match them. Sending the plain ones here made
    # streaming STTs (Deepgram, AssemblyAI, Soniox) never call
    # ``_handle_vad_user_stopped_speaking`` → never finalise → probe times
    # out on a HEALTHY provider. Using the VAD classes mirrors what the
    # transport does and is what every STT service is written to consume.
    from pipecat.frames.frames import (
        InputAudioRawFrame,
        InterimTranscriptionFrame,
        TranscriptionFrame,
        VADUserStartedSpeakingFrame,
        VADUserStoppedSpeakingFrame,
    )
    from pipecat.pipeline.task import PipelineParams
    from core.services.readiness.probe_pipeline import probe_in_pipeline

    def _is_transcript(frame) -> bool:
        if isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)):
            text = (getattr(frame, "text", "") or "").strip()
            return bool(text)
        return False

    # NO ``EndFrame`` — sending it here triggers the service's ``stop()`` →
    # ``_disconnect()`` which closes the WebSocket immediately. Streaming STTs
    # emit their final transcript ASYNC ~100-500ms after ``send_finalize``;
    # closing the WS in that window drops the response and the probe times
    # out on a HEALTHY provider. The harness's ``_teardown`` will
    # ``task.cancel()`` once we've captured a transcript OR hit the timeout.
    # Chunk audio into 20ms frames to mirror real-transport delivery.
    # Streaming STTs (Cartesia ink-whisper, Gladia solaria-1) run inference
    # on chunks as they arrive; dumping all 5.3s as ONE giant frame confuses
    # some servers into never emitting a final transcript (probe times out
    # on a HEALTHY provider). 20ms is the standard telephony/WebRTC frame
    # size — 640 bytes at 16 kHz mono 16-bit. Deepgram/AssemblyAI/Whisper
    # already worked with single-shot; chunking keeps them working (same
    # total audio, same VAD boundaries) while fixing Cartesia/Gladia.
    bytes_per_sample = 2  # linear16
    ms_per_chunk = 20
    chunk_bytes = int(target_rate * ms_per_chunk / 1000) * bytes_per_sample
    # Append 1s of trailing silence so server-side endpointing (Gladia
    # solaria-1, some Whisper deployments, Sarvam) can naturally detect
    # end-of-speech and emit a final transcript. Real calls always have
    # natural post-utterance pauses; the bundled probe WAV is dense speech
    # right up to the end, and pure-server-side-VAD providers keep waiting
    # for more audio until we force a shutdown — which is too late.
    trailing_silence = b"\x00\x00" * target_rate  # 1s of PCM silence
    padded_audio = audio_bytes + trailing_silence
    audio_chunks = [
        padded_audio[i:i + chunk_bytes]
        for i in range(0, len(padded_audio), chunk_bytes)
    ]

    input_frames = [
        # Start the "user turn" — resets TTFB tracking, kicks metrics, and
        # tells segmented STTs to begin buffering. Without this, some
        # services never see a turn boundary and silently discard audio.
        VADUserStartedSpeakingFrame(),
        *[
            InputAudioRawFrame(audio=c, sample_rate=target_rate, num_channels=1)
            for c in audio_chunks
        ],
        # Stop the turn — triggers ``request_finalize()`` on streaming STTs
        # (Deepgram: connection.finalize; AssemblyAI: force_endpoint;
        # Cartesia: WS "finalize"; Sarvam: socket.flush()) so the provider
        # flushes buffered audio and emits its final transcript.
        VADUserStoppedSpeakingFrame(),
    ]
    params = PipelineParams(
        audio_in_sample_rate=target_rate,
        audio_out_sample_rate=24000,
        enable_metrics=False,
    )

    try:
        ok, frame, err_msg = await probe_in_pipeline(
            service,
            input_frames,
            _is_transcript,
            params=params,
            timeout_s=25.0,   # under the check's 30s wrapper — leave room for teardown
            provider=provider,
            # Streaming STTs (Deepgram, AssemblyAI, Soniox, Gladia, Sarvam,
            # Azure, Speechmatics) schedule their WebSocket handshake in a
            # background task from ``_connect``; audio pushed before the
            # handshake completes is silently dropped by their per-service
            # ``if self._connection/._websocket:`` guards. 3s covers a cold
            # WS handshake in unusual regions (Deepgram nova-3 India, etc.).
            # Deepgram exits early via ``_connection_ready`` if ready sooner;
            # other providers fall back to a fixed sleep of this length.
            warmup_s=3.0,
            # Delayed EndFrame for Gladia and any future streaming STT that
            # only emits a final transcript from ``stop(EndFrame)`` (Gladia's
            # ``_send_stop_recording`` runs there, not on the VAD frame).
            # Well-behaved services (Deepgram, Speechmatics, ElevenLabs
            # Realtime, Soniox, AssemblyAI, Sarvam) finalize on the VAD frame
            # and complete before the sleep — teardown cancels the pending
            # EndFrame, so they're unaffected.
            end_frame_after_s=3.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} STT pipeline harness raised", provider)
        return ProbeResult(False, _summarise_error(provider, exc))

    if ok and frame is not None:
        text = (getattr(frame, "text", "") or "").strip().replace("\n", " ")
        snippet = text[:60]
        return ProbeResult(True, f"{provider} STT transcribed: '{snippet}'")

    if err_msg:
        return ProbeResult(False, _summarise_error_text(provider, err_msg))

    if not using_real_audio:
        # Silence-only probe cannot prove the provider actually works — a
        # broken key would accept a WebSocket open and never emit anything,
        # yielding a "successful" no-frame session indistinguishable from a
        # healthy one. Fail hard so the deploy is fixed (WAV missing from
        # the image) instead of silently passing every STT readiness check.
        return ProbeResult(
            False,
            f"{provider} STT probe unavailable: bundled probe WAV missing — "
            f"redeploy with core/services/readiness/assets/probe_sample.wav.",
        )

    # Real audio was sent but no transcript arrived within budget. We can't
    # tell "slow provider" from "silently broken", so treat it as a timeout
    # (WARNING) — the missing-WAV deploy bug above is the only hard STT failure.
    return ProbeResult(
        False,
        f"{provider} didn't return a transcript in time — it may be slow. Run "
        "the deep test again in a moment.",
        timed_out=True,
    )


# ── STT audio helpers ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_probe_pcm16() -> Optional[Tuple[bytes, int, bytes]]:
    """Read the bundled PCM16 mono WAV once.

    Returns ``(pcm_bytes, sample_rate, full_wav_bytes)`` or ``None``:

    * ``pcm_bytes`` — headerless PCM frames, what streaming STTs (Deepgram,
      AssemblyAI, Sarvam, Soniox, …) expect on their persistent WebSocket.
    * ``sample_rate`` — native rate of the asset (16 kHz).
    * ``full_wav_bytes`` — the whole file including the RIFF header, what
      HTTP-batch STTs (OpenAI Whisper, Groq, …) expect as a multipart upload
      payload. Reading it once here avoids a second disk hit per probe.

    Cached because the file is small and re-reading on every probe is wasteful.
    """
    try:
        asset = files("core.services.readiness.assets") / _STT_PROBE_ASSET
    except (ModuleNotFoundError, FileNotFoundError):
        return None
    try:
        raw_bytes = asset.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        logger.debug("[readiness] STT probe asset unavailable: {}", exc)
        return None
    try:
        with wave.open(io.BytesIO(raw_bytes), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                logger.warning(
                    "[readiness] STT probe asset must be mono PCM16; "
                    "got channels={}, sampwidth={}",
                    wav.getnchannels(),
                    wav.getsampwidth(),
                )
                return None
            return wav.readframes(wav.getnframes()), wav.getframerate(), raw_bytes
    except wave.Error as exc:
        logger.debug("[readiness] STT probe asset invalid WAV: {}", exc)
        return None


def _load_stt_audio(target_rate: int, service) -> Tuple[bytes, bool]:
    """Return ``(audio_bytes, using_real_audio)`` for the STT probe.

    Dispatch is by service class:

    * **HTTP-batch STTs** (Whisper family: OpenAI, Groq, some ElevenLabs) —
      return the full WAV file bytes (RIFF header + PCM). Their ``run_stt``
      uploads the payload as a file to ``/audio/transcriptions``; raw PCM
      without a container gets rejected as "could not decode".
    * **Streaming STTs** (Deepgram, AssemblyAI, Soniox, Gladia, …) — return
      headerless PCM at ``target_rate``, resampled from the asset's native
      16 kHz via stdlib ``audioop.ratecv`` when the rates differ. Their
      persistent WebSocket expects raw PCM chunks.

    Falls back to 0.5s of silence when the WAV asset isn't committed yet;
    the ``using_real_audio`` flag tells the caller whether to expect a
    transcript at all.
    """
    loaded = _load_probe_pcm16()
    if loaded is None:
        silence = b"\x00\x00" * (target_rate // 2)
        return silence, False
    pcm, native_rate, full_wav = loaded

    if type(service).__name__ in _HTTP_STT_SERVICE_CLASSES:
        # HTTP services parse the WAV header themselves + resample internally
        # if needed — don't touch the buffer.
        return full_wav, True

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


def _extract_error_frame_message(frame, error_frame_type) -> Optional[str]:
    """Return the error message when ``frame`` is a pipecat ``ErrorFrame``.

    Pipecat WebSocket-based providers (Fish Audio TTS, Deepgram STT, ElevenLabs,
    etc.) don't raise Python exceptions on connection failure — they push an
    ``ErrorFrame`` into the frame stream. Runtime pipelines log these and keep
    going; the readiness probes need to catch them explicitly, otherwise a 402
    / 401 / model-not-found quietly yields "no audio observed" (or "no frames")
    and the probe silently PASSes.

    Duck-typed fallback: when the ``ErrorFrame`` type couldn't be imported we
    still detect any frame whose class name ends in ``ErrorFrame`` and carries
    an ``.error`` attribute.
    """
    if error_frame_type is not None and isinstance(frame, error_frame_type):
        return str(getattr(frame, "error", "") or "provider emitted an error frame")
    cls_name = type(frame).__name__
    if cls_name.endswith("ErrorFrame") and hasattr(frame, "error"):
        return str(getattr(frame, "error", "") or "provider emitted an error frame")
    return None


# ── TTS probe (universal — pipecat's run_tts) ────────────────────────────────


async def probe_tts(ctx) -> ProbeResult:
    """Synthesise the word "test" through the pipecat TTS service and consume the
    first audio frame. Universal across providers via ``TTSService.run_tts``.
    Handles services (Cartesia) that override the signature to require extra args.
    """
    from core.services.pipeline import service_factory

    spec = _build_spec(ctx, "tts")
    if spec is None:
        return ProbeResult(False, "TTS spec incomplete — check shallow config first.")

    provider = spec["provider_name"]

    # Voice-ID resolution is now handled centrally by
    # ``service_resolver._build_service_specs`` (see resolver line 283-287).
    # The old manual ``ctx.voice.voice_id`` injection here was made
    # redundant by the resolver refactor — removing it prevents double-
    # writes / drift between probe and real-call spec shapes.

    try:
        service = service_factory.build_tts(spec)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} TTS client construction failed", provider)
        return ProbeResult(False, f"Could not construct {provider} TTS client: {exc}")
    if service is None:
        return ProbeResult(
            False, f"No pipecat client available for TTS provider '{provider}'."
        )

    # Feed the service through a minimal pipecat pipeline. Runtime uses
    # exactly this frame flow for the first-message greeting (see
    # ``core/services/pipeline/runner/pipecat.py`` — ``task.queue_frame(
    # TTSSpeakFrame(text=first_message_text))``). Using it here means every
    # TTS service that works in production works in the probe — WS lifecycle,
    # StartFrame setup, TaskManager, all provided by ``PipelineTask``.
    from pipecat.frames.frames import TTSAudioRawFrame, TTSSpeakFrame
    from pipecat.pipeline.task import PipelineParams
    from core.services.readiness.probe_pipeline import probe_in_pipeline

    def _is_audio(frame) -> bool:
        if isinstance(frame, TTSAudioRawFrame) and getattr(frame, "audio", None):
            return True
        # Some providers wrap audio in their own subclass; duck-type as a
        # safety net so we don't miss real synth.
        audio = getattr(frame, "audio", None)
        return bool(audio) and hasattr(frame, "sample_rate")

    # NO ``EndFrame`` — same reason as probe_stt: EndFrame triggers
    # ``service.stop()`` → ``_disconnect()`` which closes the WebSocket.
    # Streaming TTSs (MiniMax, ElevenLabs, Cartesia, LMNT, Play.ht, …)
    # stream synthesized audio back ASYNC over that same WS a few hundred
    # ms after receiving TTSSpeakFrame; closing the WS in that window
    # drops the audio and the probe times out on a HEALTHY provider. The
    # harness's ``_teardown`` will ``task.cancel()`` once we've captured
    # the first audio frame OR hit the timeout.
    input_frames = [TTSSpeakFrame(text=_TTS_PROBE_TEXT)]
    params = PipelineParams(
        audio_in_sample_rate=16000,
        audio_out_sample_rate=int(
            (ctx.tts.settings or {}).get("sample_rate") or 24000
        ),
        enable_metrics=False,
    )

    try:
        ok, frame, err_msg = await probe_in_pipeline(
            service,
            input_frames,
            _is_audio,
            params=params,
            timeout_s=18.0,   # under the check's 22s wrapper — leave room for teardown
            provider=provider,
            # Streaming TTSs (ElevenLabs, Cartesia, LMNT, Play.ht, Fish,
            # Rime, Neuphonic, Sarvam, Deepgram TTS, MiniMax) use the same
            # background-handshake pattern as streaming STTs: ``_connect``
            # schedules the WS handshake, and each ``send`` call is guarded
            # by ``if self._websocket and .state is OPEN``. A TTSSpeakFrame
            # pushed before the handshake completes is silently dropped and
            # no audio comes back — a healthy provider looks broken. 2s is
            # enough for typical WS-TTS handshakes without inflating probe
            # latency; services with a readiness event exit early via the
            # harness's ``_connection_ready`` fast path.
            warmup_s=2.0,
            # NO delayed EndFrame for TTS. Unlike STT (where Gladia needs
            # EndFrame to trigger ``_send_stop_recording``), TTS providers
            # stream audio naturally as they synthesize — no explicit
            # "flush" signal exists. Sending EndFrame mid-synthesis triggers
            # ``service.stop()`` → ``_disconnect()`` which for HTTP-based
            # streaming TTS (MiniMax via aiohttp, OpenAI, Google, Azure,
            # Hume) cancels the in-flight response BEFORE first audio bytes
            # arrive in slower regions. Result: probe times out on a
            # healthy provider that just needed a few more seconds of
            # streaming. Natural teardown (``task.cancel()`` on capture or
            # timeout) handles cleanup correctly for both WS and HTTP TTS.
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} TTS pipeline harness raised", provider)
        return ProbeResult(False, _summarise_error(provider, exc))

    if ok:
        return ProbeResult(True, f"{provider} synthesised a sentence.")
    if err_msg:
        return ProbeResult(False, _summarise_error_text(provider, err_msg))
    # err_msg is None → pure timeout: no audio frame within budget. Slow /
    # warming up, not confirmed-broken → WARNING, not a publish blocker.
    return ProbeResult(
        False,
        f"{provider} didn't return audio in time — it may be slow or warming "
        "up. Run the deep test again in a moment.",
        timed_out=True,
    )


# ── Transport probe (telephony account balance / credit) ─────────────────────
#
# One dispatcher, one branch per provider. Every telephony provider we
# support exposes a small, cheap "account status / balance" endpoint that
# (a) fails fast with 401/403 on a revoked or wrong credential, and
# (b) returns a balance we can inspect to decide "out of credit". Rather
# than duplicate per-provider adapters (like the LLM probe does for
# OpenAI-family vs Anthropic vs Google), the shape is uniform enough to
# keep as one function that switches on ``channel_type``. Add a provider
# by adding one branch.
#
# Provider reference:
# * Twilio  — GET /2010-04-01/Accounts/{sid}/Balance.json  (Basic sid:token)
# * Telnyx  — GET /v2/balance                              (Bearer api_key)
# * Plivo   — GET /v1/Account/{auth_id}/                   (Basic auth_id:token)
# * Exotel  — GET /v1/Accounts/{sid}/Balance.json          (Basic key:token,
#             subdomain configurable, e.g. api.exotel.com / @sg.exotel.com)


_TRANSPORT_PROBE_TIMEOUT = 6.0

# Below this native-currency balance, we report the account as effectively
# out of credit. Sub-1 balances can't fund even a minute of talk time on any
# of the four providers, so this floor holds regardless of currency (USD,
# EUR, INR). If a provider ever needs a different threshold, add a per-
# provider override next to that provider's probe function.
_LOW_BALANCE_FLOOR = 1.0


async def probe_transport(
    client, channel_config: Dict[str, Any], channel_type: str
) -> ProbeResult:
    """Hit the provider's account endpoint to verify credentials + credit.

    Takes a caller-owned ``httpx.AsyncClient`` so a check probing several
    channels reuses one connection pool — same pattern as ``ToolReachableCheck``
    and ``McpServerReachableCheck``. ``channel_config`` is the decrypted
    ``Channel.encrypted_config`` dict — the same shape the transport
    serializers consume at call time. Returns a ``ProbeResult`` where
    ``ok=False`` means a real call would fail (bad credential, suspended
    account, empty balance, or unreachable API).
    """
    import httpx

    slug = (channel_type or "").strip().lower()
    cfg = channel_config or {}

    try:
        if slug == "twilio":
            return await _probe_twilio(client, cfg)
        if slug == "telnyx":
            return await _probe_telnyx(client, cfg)
        if slug == "plivo":
            return await _probe_plivo(client, cfg)
        if slug == "exotel":
            return await _probe_exotel(client, cfg)
    except httpx.HTTPError as exc:
        logger.warning("[readiness] {} transport probe network error: {}", slug, exc)
        return ProbeResult(False, _summarise_error(slug, exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} transport probe unexpected error", slug)
        return ProbeResult(False, _summarise_error(slug, exc))

    return ProbeResult(
        True,
        f"{slug or 'transport'}: no credit probe implemented for this channel type.",
    )


async def _probe_twilio(client, cfg: Dict[str, Any]) -> ProbeResult:
    account_sid = (cfg.get("account_sid") or "").strip()
    auth_token = (cfg.get("auth_token") or "").strip()
    if not account_sid or not auth_token:
        return ProbeResult(False, "twilio: account_sid / auth_token missing on the channel.")
    resp = await client.get(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Balance.json",
        auth=(account_sid, auth_token),
    )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "twilio rejected the credentials — account_sid / auth_token invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("twilio", resp))
    balance, currency = _parse_amount(resp, "balance", "currency")
    if balance is not None and balance < _LOW_BALANCE_FLOOR:
        return ProbeResult(
            False,
            f"twilio account balance is {balance:.2f} {currency or ''} — top up before making calls.",
        )
    return ProbeResult(True, _balance_ok_message("twilio", balance, currency))


async def _probe_telnyx(client, cfg: Dict[str, Any]) -> ProbeResult:
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        return ProbeResult(False, "telnyx: api_key missing on the channel.")
    resp = await client.get(
        "https://api.telnyx.com/v2/balance",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "telnyx rejected the credentials — api_key invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("telnyx", resp))
    data = _json_or_empty(resp).get("data") or {}
    balance = _to_float(data.get("balance") or data.get("available_credit"))
    currency = data.get("currency")
    if balance is not None and balance < _LOW_BALANCE_FLOOR:
        return ProbeResult(
            False,
            f"telnyx account balance is {balance:.2f} {currency or ''} — top up before making calls.",
        )
    return ProbeResult(True, _balance_ok_message("telnyx", balance, currency))


async def _probe_plivo(client, cfg: Dict[str, Any]) -> ProbeResult:
    auth_id = (cfg.get("auth_id") or "").strip()
    auth_token = (cfg.get("auth_token") or "").strip()
    if not auth_id or not auth_token:
        return ProbeResult(False, "plivo: auth_id / auth_token missing on the channel.")
    resp = await client.get(
        f"https://api.plivo.com/v1/Account/{auth_id}/",
        auth=(auth_id, auth_token),
    )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "plivo rejected the credentials — auth_id / auth_token invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("plivo", resp))
    data = _json_or_empty(resp)
    # Plivo reports credits in USD by convention (no currency field on this endpoint).
    balance = _to_float(data.get("cash_credits") or data.get("credit_limit"))
    if balance is not None and balance < _LOW_BALANCE_FLOOR:
        return ProbeResult(
            False,
            f"plivo cash credits are {balance:.2f} USD — top up before making calls.",
        )
    return ProbeResult(True, _balance_ok_message("plivo", balance, "USD"))


async def _probe_exotel(client, cfg: Dict[str, Any]) -> ProbeResult:
    # Exotel uses (api_key, api_token) as HTTP Basic and (account_sid,
    # subdomain) to route the request. ``subdomain`` defaults to the primary
    # region so accounts on regional shards (e.g. ``sg.exotel.com``) can
    # override without a code change.
    api_key = (cfg.get("api_key") or "").strip()
    api_token = (cfg.get("api_token") or "").strip()
    account_sid = (cfg.get("account_sid") or cfg.get("sid") or "").strip()
    subdomain = (cfg.get("subdomain") or "api.exotel.com").strip()
    if not api_key or not api_token or not account_sid:
        return ProbeResult(
            False,
            "exotel: api_key / api_token / account_sid missing on the channel.",
        )
    resp = await client.get(
        f"https://{subdomain}/v1/Accounts/{account_sid}/Balance.json",
        auth=(api_key, api_token),
    )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "exotel rejected the credentials — api_key / api_token invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("exotel", resp))
    # Exotel wraps the payload as ``{"Balance": {"Balance": "10.00", ...}}``.
    body = _json_or_empty(resp)
    payload = body.get("Balance") if isinstance(body.get("Balance"), dict) else body
    balance = _to_float(payload.get("Balance") or payload.get("balance"))
    currency = payload.get("Currency") or payload.get("currency")
    if balance is not None and balance < _LOW_BALANCE_FLOOR:
        return ProbeResult(
            False,
            f"exotel account balance is {balance:.2f} {currency or ''} — top up before making calls.",
        )
    return ProbeResult(True, _balance_ok_message("exotel", balance, currency))


def _json_or_empty(resp) -> Dict[str, Any]:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _parse_amount(resp, balance_key: str, currency_key: str) -> Tuple[Optional[float], Optional[str]]:
    data = _json_or_empty(resp)
    return _to_float(data.get(balance_key)), data.get(currency_key)


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _balance_ok_message(provider: str, balance: Optional[float], currency: Optional[str]) -> str:
    if balance is None:
        return f"{provider}: credentials valid (balance not reported by API)."
    return f"{provider}: credentials valid, balance {balance:.2f} {currency or ''}".rstrip()


def _summarise_http(provider: str, resp) -> str:
    """Turn a non-2xx transport response into a one-liner via the shared
    summariser. Attaches ``status_code`` to a plain ``Exception`` so the
    credit-hint / 5xx buckets in ``_summarise_error`` fire uniformly for
    transport, LLM, STT, and TTS."""
    exc = Exception(f"HTTP {resp.status_code}: {resp.text[:180]}")
    exc.status_code = resp.status_code  # type: ignore[attr-defined]
    return _summarise_error(provider, exc)


# ── Phone number verification probe ──────────────────────────────────────────
#
# For every assigned phone number, hit the telephony provider's per-number
# endpoint to verify three things at once:
#   (a) the number is actually owned by the account (credentials + real number)
#   (b) the number is voice-capable (not SMS-only)
#   (c) for inbound-capable providers with webhook routing (Twilio, Telnyx),
#       the inbound webhook prefix points at Tone (``BASE_CALL_URL``).
#
# Same dispatcher shape as ``probe_transport`` above — one branch per provider.
# Plivo/Exotel don't have first-class inbound routes in Tone today, so the
# webhook prefix argument is optional and those branches only check (a) and (b).
#
# Provider endpoints:
#   * Twilio  — GET /2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json
#               ?PhoneNumber={e164}   (Basic sid:token)
#   * Telnyx  — GET /v2/phone_numbers?filter[phone_number]={e164}
#               (Bearer api_key)
#   * Plivo   — GET /v1/Account/{auth_id}/Number/{e164}/  (Basic auth_id:token)
#   * Exotel  — GET /v1/Accounts/{sid}/IncomingPhoneNumbers/{e164}.json
#               (Basic key:token)


_PHONE_NUMBER_PROBE_TIMEOUT = 6.0


async def probe_phone_number(
    client,
    channel_config: Dict[str, Any],
    channel_type: str,
    e164_number: str,
    expected_webhook_prefix: Optional[str] = None,
) -> ProbeResult:
    """Verify a specific phone number exists at the provider, is voice-capable,
    and (Twilio/Telnyx only) is wired to Tone's inbound webhook.

    Follows the same pattern as ``probe_transport`` — one shared client, per-
    provider branches, ``ProbeResult`` return. Never raises: every failure
    mode maps to a user-visible message so the enclosing DeepCheck can
    aggregate results without try/except at the call site.
    """
    import httpx

    slug = (channel_type or "").strip().lower()
    cfg = channel_config or {}
    number = (e164_number or "").strip()
    if not number:
        return ProbeResult(False, f"{slug}: phone number is empty on the record.")

    try:
        if slug == "twilio":
            return await _probe_twilio_number(client, cfg, number, expected_webhook_prefix)
        if slug == "telnyx":
            return await _probe_telnyx_number(client, cfg, number, expected_webhook_prefix)
        if slug == "plivo":
            return await _probe_plivo_number(client, cfg, number)
        if slug == "exotel":
            return await _probe_exotel_number(client, cfg, number)
    except httpx.HTTPError as exc:
        logger.warning("[readiness] {} number probe network error: {}", slug, exc)
        return ProbeResult(False, _summarise_error(slug, exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("[readiness] {} number probe unexpected error", slug)
        return ProbeResult(False, _summarise_error(slug, exc))

    return ProbeResult(
        True,
        f"{slug or 'transport'}: no number-verification probe implemented for this channel type.",
    )


async def _probe_twilio_number(
    client, cfg: Dict[str, Any], number: str, expected_prefix: Optional[str]
) -> ProbeResult:
    account_sid = (cfg.get("account_sid") or "").strip()
    auth_token = (cfg.get("auth_token") or "").strip()
    if not account_sid or not auth_token:
        return ProbeResult(False, "twilio: account_sid / auth_token missing on the channel.")
    resp = await client.get(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json",
        params={"PhoneNumber": number},
        auth=(account_sid, auth_token),
    )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "twilio rejected the credentials — account_sid / auth_token invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("twilio", resp))
    numbers = _json_or_empty(resp).get("incoming_phone_numbers") or []
    if not numbers:
        return ProbeResult(
            False,
            f"twilio: number {number} is not owned by this account.",
        )
    entry = numbers[0]
    capabilities = entry.get("capabilities") or {}
    if not capabilities.get("voice"):
        return ProbeResult(
            False,
            f"twilio: number {number} is not voice-capable (SMS/MMS only).",
        )
    if expected_prefix:
        voice_url = (entry.get("voice_url") or "").strip()
        if not voice_url.startswith(expected_prefix):
            return ProbeResult(
                False,
                f"twilio: number {number} voice webhook does not point to Tone "
                f"(got '{voice_url or 'unset'}').",
            )
    return ProbeResult(True, f"twilio: {number} verified (owned, voice-capable, webhook routed).")


async def _probe_telnyx_number(
    client, cfg: Dict[str, Any], number: str, expected_prefix: Optional[str]
) -> ProbeResult:
    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        return ProbeResult(False, "telnyx: api_key missing on the channel.")
    resp = await client.get(
        "https://api.telnyx.com/v2/phone_numbers",
        params={"filter[phone_number]": number},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "telnyx rejected the credentials — api_key invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("telnyx", resp))
    data = _json_or_empty(resp).get("data") or []
    if not data:
        return ProbeResult(
            False,
            f"telnyx: number {number} is not owned by this account.",
        )
    entry = data[0]
    features = entry.get("features") or []
    # Telnyx feature entries can be strings or objects — normalize both, and
    # skip anything that doesn't resolve to a non-empty string (a dict with
    # ``{"name": None, ...}`` would otherwise crash on ``None.lower()``).
    feature_names: set[str] = set()
    for f in features:
        if not f:
            continue
        raw = f.get("name") if isinstance(f, dict) else f
        if not isinstance(raw, str) or not raw:
            continue
        feature_names.add(raw.lower())
    if "voice" not in feature_names:
        return ProbeResult(
            False,
            f"telnyx: number {number} is not voice-enabled.",
        )
    # Webhook routing on Telnyx lives on the linked "voice connection"
    # (connection_id) rather than the number row itself. We surface the
    # coarser signal — the number is voice-enabled and owned — and let
    # inbound wire-up failures show up in call logs. Verifying the
    # connection's webhook_event_url would need a second API call per
    # number, which is heavy for the readiness path.
    if expected_prefix:
        # Best-effort: some Telnyx account setups expose ``voice_url`` on the
        # number itself; if present, validate; if absent, skip silently.
        voice_url = (entry.get("voice_url") or "").strip()
        if voice_url and not voice_url.startswith(expected_prefix):
            return ProbeResult(
                False,
                f"telnyx: number {number} voice webhook does not point to Tone "
                f"(got '{voice_url}').",
            )
    return ProbeResult(True, f"telnyx: {number} verified (owned, voice-enabled).")


async def _probe_plivo_number(
    client, cfg: Dict[str, Any], number: str
) -> ProbeResult:
    auth_id = (cfg.get("auth_id") or "").strip()
    auth_token = (cfg.get("auth_token") or "").strip()
    if not auth_id or not auth_token:
        return ProbeResult(False, "plivo: auth_id / auth_token missing on the channel.")
    # Plivo number lookup uses the raw E.164 without the leading '+'.
    plivo_number = number.lstrip("+")
    resp = await client.get(
        f"https://api.plivo.com/v1/Account/{auth_id}/Number/{plivo_number}/",
        auth=(auth_id, auth_token),
    )
    if resp.status_code == 404:
        return ProbeResult(
            False,
            f"plivo: number {number} is not owned by this account.",
        )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "plivo rejected the credentials — auth_id / auth_token invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("plivo", resp))
    data = _json_or_empty(resp)
    # Plivo returns ``voice_enabled`` (bool) on the number resource.
    if data.get("voice_enabled") is False:
        return ProbeResult(
            False,
            f"plivo: number {number} is not voice-enabled.",
        )
    return ProbeResult(True, f"plivo: {number} verified (owned, voice-enabled).")


async def _probe_exotel_number(
    client, cfg: Dict[str, Any], number: str
) -> ProbeResult:
    api_key = (cfg.get("api_key") or "").strip()
    api_token = (cfg.get("api_token") or "").strip()
    account_sid = (cfg.get("account_sid") or cfg.get("sid") or "").strip()
    subdomain = (cfg.get("subdomain") or "api.exotel.com").strip()
    if not api_key or not api_token or not account_sid:
        return ProbeResult(
            False,
            "exotel: api_key / api_token / account_sid missing on the channel.",
        )
    # Exotel forked from Twilio; both reject percent-encoded '+' ('%2B') in
    # phone-number path segments. Strip the leading '+' the same way the Plivo
    # branch does so httpx doesn't encode it in the URL path.
    exotel_number = number.lstrip("+")
    resp = await client.get(
        f"https://{subdomain}/v1/Accounts/{account_sid}/IncomingPhoneNumbers/{exotel_number}.json",
        auth=(api_key, api_token),
    )
    if resp.status_code == 404:
        return ProbeResult(
            False,
            f"exotel: number {number} is not owned by this account.",
        )
    if resp.status_code in (401, 403):
        return ProbeResult(False, "exotel rejected the credentials — api_key / api_token invalid.")
    if resp.status_code >= 400:
        return ProbeResult(False, _summarise_http("exotel", resp))
    # Exotel wraps as ``{"IncomingPhoneNumber": {...}}``; the presence of the
    # row is enough to prove ownership, and voice is the default capability
    # for Exotel virtual numbers.
    return ProbeResult(True, f"exotel: {number} verified (owned).")


# ── error summariser ─────────────────────────────────────────────────────────


def _classify_by_bucket(provider: str, lower: str, status: Optional[int]) -> Optional[str]:
    """Map a lower-cased provider error + optional HTTP status onto ONE clear,
    user-facing sentence, or ``None`` when it fits no known bucket.

    Single source of truth for provider-error copy: reused by both the
    raised-exception path (:func:`_summarise_error`) and the ErrorFrame-message
    path (:func:`_summarise_error_text`) so a wrong key / out-of-credit / dead
    model reads identically no matter which path surfaced it.
    """
    # Auth failure — 401/403 are canonical, but providers ship plenty of
    # variants with only a text body. Match the common credential phrasings so
    # a wrong key doesn't fall through to the raw bucket.
    auth_hints = (
        "unauthorized", "invalid api key", "invalid_api_key",
        "invalid token", "invalid_token", "incorrect api key",
        "authentication failed", "authentication_error",
        "bad credentials", "invalid credentials", "credentials are not valid",
        "api key not valid", "not authenticated", "missing api key",
        "forbidden", "access denied", "permission denied",
    )
    if status in (401, 403) or any(h in lower for h in auth_hints):
        return f"{provider} rejected the API key — it may be revoked or wrong."
    if status == 404 or "model not found" in lower or "does not exist" in lower:
        return f"{provider} says the model doesn't exist (maybe deprecated)."
    if status == 429 or "rate limit" in lower or "too many requests" in lower:
        return f"{provider} rate-limited this test — retry in a minute."
    # Credit / quota exhaustion — providers spell this many ways; a common
    # cause of "green yesterday, fails today". Deepseek → 402; Anthropic → 400
    # with a text hint; OpenAI/Groq → 429 + "quota"; others use "credit"/
    # "balance"/"payment".
    credit_hints = (
        "insufficient balance", "credit balance", "credit_balance",
        "insufficient_quota", "quota exceeded", "exceeded your current quota",
        "payment required", "billing",
    )
    if status == 402 or any(h in lower for h in credit_hints):
        return (
            f"{provider} account is out of credit / quota — top up billing "
            f"with the provider, then re-run."
        )
    if status and status >= 500:
        return f"{provider} returned {status} — provider outage or transient error."
    return None


# Framework-side quirks — pipecat / tone internals rather than a provider
# health issue. The marker lets the UI style these as "please file a bug".
_FRAMEWORK_BUG_PATTERNS = (
    "range() arg 3 must not be zero",              # OpenAI TTS chunk-size default
    "invalid value: integer `0`",                  # Deepgram TTS query-param default
    "taskmanager is not initialized",              # Should not fire post-harness
)


def _summarise_error(provider: str, exc: BaseException) -> str:
    """Turn a raw provider exception into a one-liner the drawer can render."""
    msg = str(exc)
    lower = msg.lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)

    bucketed = _classify_by_bucket(provider, lower, status)
    if bucketed is not None:
        return bucketed
    if any(p in lower for p in _FRAMEWORK_BUG_PATTERNS):
        logger.warning("[readiness] {} framework-bug pattern in probe error: {}", provider, exc)
        return f"[framework_bug] {provider} probe failed: {_extract_error_message(msg)}"
    logger.warning("[readiness] {} probe error: {}", provider, exc)
    return f"[provider_error] {provider} probe failed: {_extract_error_message(msg)}"


def _summarise_error_text(provider: str, text: str) -> str:
    """Clean an ErrorFrame message (a raw provider error body) the same way
    :func:`_summarise_error` cleans an exception.

    The pipeline harness surfaces provider 4xx/5xx as ErrorFrames whose text is
    the raw provider payload (e.g. ``Unknown error occurred: Error code: 400 -
    {'error': {'message': "Invalid language 'english'"}}``). Route it through
    the shared buckets; when nothing matches, extract the human ``message``
    field so the drawer shows the real reason instead of raw JSON.
    """
    lower = (text or "").lower()
    status = _parse_status_code(text)
    bucketed = _classify_by_bucket(provider, lower, status)
    if bucketed is not None:
        return bucketed
    if any(p in lower for p in _FRAMEWORK_BUG_PATTERNS):
        return f"[framework_bug] {provider} probe failed: {_extract_error_message(text)}"
    return f"{provider} returned an error: {_extract_error_message(text)}"


def _parse_status_code(text: Optional[str]) -> Optional[int]:
    """Pull an HTTP status out of a free-text error (``Error code: 400``,
    ``status: 429``) so bucketing works on ErrorFrame text that has no status
    attribute. Returns ``None`` when no 3-digit code is present."""
    if not text:
        return None
    m = re.search(r"(?i)(?:error code|status(?:[ _]code)?|http)\D{0,3}(\d{3})", text)
    return int(m.group(1)) if m else None


def _extract_error_message(text: Optional[str]) -> str:
    """Extract the human-readable reason from a raw provider error string.

    Provider errors usually embed the real message in a ``'message': '...'``
    field of a serialised dict/JSON; pull that out. Otherwise strip the
    ``Unknown error occurred:`` / ``Error code: NNN -`` noise and return the
    remainder. Always bounded so one row never dumps a wall of JSON.
    """
    raw = (text or "").strip()
    if not raw:
        return "the provider returned an error with no details."
    # Prefer the inner ``message`` field — capture up to the matching quote so
    # apostrophes inside the message (``'english'``) don't cut it short.
    m = re.search(r"""['"]message['"]\s*:\s*(['"])(.*?)\1""", raw, re.DOTALL)
    candidate = m.group(2) if m else raw
    # Strip common noise prefixes from the non-message path.
    candidate = re.sub(r"(?i)^\s*unknown error occurred:\s*", "", candidate)
    candidate = re.sub(r"(?i)^\s*error code:\s*\d+\s*-\s*", "", candidate)
    candidate = candidate.splitlines()[0].strip()
    if len(candidate) > 180:
        candidate = candidate[:177].rstrip() + "…"
    return candidate or "the provider returned an error."
