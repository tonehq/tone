"""Standalone readiness probe for LLM / STT / TTS providers.

Runs the SAME pipecat frame flow that a real call uses (via
``core.services.pipeline.service_factory`` + ``core.services.readiness.probe_pipeline``)
so a green result here means the provider is ready to attend a call — no DB,
no HTTP, no fake mocks.

Usage:
    python dev/test_agent_readiness.py                # test everything below
    python dev/test_agent_readiness.py --only openai  # test just one provider
    python dev/test_agent_readiness.py --kind llm     # only LLM probes

API keys are read from `.env` (loaded via python-dotenv). Model / voice /
language pinned per provider below — pick the cheapest/fastest defaults.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import warnings
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- .env + import path ------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


# --- logging setup -----------------------------------------------------------
# Pipecat is loguru-heavy — every WorkerRunner / FrameProcessor / WS connect
# emits DEBUG/INFO lines that swamp the console and hide the [PASS]/[FAIL]
# rows we actually care about. Route everything into a per-run log file so
# nothing is lost, and keep the console limited to WARNING+ from loguru
# plus our own print() lines.

LOG_DIR = REPO_ROOT / "dev" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"test_agent_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def setup_logging() -> Path:
    """Route loguru + warnings module into ``LOG_FILE``; keep console quiet.

    Called once at startup, BEFORE importing anything that uses loguru
    (pipecat / core.services) — otherwise those modules will have already
    grabbed the default sink and their output will still hit stderr.

    Returns the absolute log-file path so main() can print it.
    """
    from loguru import logger

    logger.remove()
    # Full-fidelity sink — every level, every module, appended per run.
    logger.add(
        str(LOG_FILE),
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        enqueue=False,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
    )
    # Console: only surface real problems from loguru; our print()s carry the
    # PASS/FAIL summary and are untouched.
    logger.add(sys.stderr, level="WARNING", format="{level}: {message}")

    # python-dotenv, DeprecationWarnings, etc. use the stdlib `warnings`
    # module — route them through loguru so they land in the file too and
    # don't clutter the console.
    def _warn_to_log(message, category, filename, lineno, file=None, line=None):
        logger.opt(depth=2).warning(
            "{}:{}: {}: {}", filename, lineno, category.__name__, message
        )

    warnings.showwarning = _warn_to_log
    return LOG_FILE.resolve()


LOG_PATH = setup_logging()


# --- provider matrix ---------------------------------------------------------
# One row per provider you want to probe. `env_key` is the .env var to read;
# rows with no key set at runtime are skipped with a "no key" note.

@dataclass
class ProbeSpec:
    kind: str                  # "llm" | "stt" | "tts"
    provider: str              # matches service_factory branch (provider_name)
    env_key: str               # .env variable holding the API key
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None    # extra kwargs (voice_id, language, sample_rate, ...)
    model_meta_data: Optional[Dict[str, Any]] = None


# --- provider catalog ------------------------------------------------------
# Static map of every provider `service_factory` supports via a plain API key.
# For each provider we list the env var to look for, plus per-kind defaults
# (model/voice/language/sample_rate) that mirror `service_factory` defaults
# and what agents actually use in production. At runtime we filter this down
# to only the providers whose env key is set — no manual probe list.
#
# NOT included on purpose (they need extra config beyond a single API key):
#   minimax (group_id), playht (user_id), aws_bedrock/aws_polly (access_key+region),
#   azure (region), google STT/TTS (service-account JSON, not the same API key),
#   ollama (base_url), openai_realtime/gemini_live (S2S — no headless probe),
#   voxtral/nemotron/parakeet/granite/gemma/qwen*/cosyvoice/chatterbox/piper
#   /mistral-self-hosted (self-hosted, no API key).

PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "llm": {"model": "gpt-4o-mini"},
        "stt": {"model": "gpt-4o-transcribe", "metadata": {"language": "en"}},
        "tts": {"model": "gpt-4o-mini-tts", "metadata": {"voice_id": "alloy"}},
    },
    "anthropic": {"env_key": "ANTHROPIC_API_KEY",
                  "llm": {"model": "claude-haiku-4-5-20251001"}},
    "groq": {
        "env_key": "GROQ_API_KEY",
        "llm": {"model": "llama-3.3-70b-versatile"},
        "stt": {"model": "whisper-large-v3-turbo", "metadata": {"language": "en"}},
    },
    "google":     {"env_key": "GOOGLE_API_KEY",     "llm": {"model": "gemini-2.5-flash"}},
    "cerebras":   {"env_key": "CEREBRAS_API_KEY",   "llm": {"model": "llama-4-scout-17b-16e-instruct"}},
    "deepseek":   {"env_key": "DEEPSEEK_API_KEY",   "llm": {"model": "deepseek-chat"}},
    "fireworks":  {"env_key": "FIREWORKS_API_KEY",  "llm": {"model": "accounts/fireworks/models/deepseek-v3p1"}},
    "openrouter": {"env_key": "OPENROUTER_API_KEY", "llm": {"model": "openai/gpt-4o-mini"}},
    "together":   {"env_key": "TOGETHER_API_KEY",   "llm": {"model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"}},
    "cohere":     {"env_key": "COHERE_API_KEY",     "llm": {"model": "command-a-03-2025"}},
    "grok":       {"env_key": "GROK_API_KEY",       "llm": {"model": "grok-3"}},
    "sambanova": {
        "env_key": "SAMBANOVA_API_KEY",
        "llm": {"model": "Meta-Llama-3.1-8B-Instruct"},
        "stt": {"model": "Whisper-Large-v3"},
    },
    "deepgram": {
        "env_key": "DEEPGRAM_API_KEY",
        "stt": {"model": "nova-3", "metadata": {"language": "en", "sample_rate": 16000}},
        "tts": {"model": "aura-2",
                "metadata": {"voice_id": "aura-2-helena-en", "sample_rate": 24000}},
    },
    "cartesia": {
        "env_key": "CARTESIA_API_KEY",
        "stt": {"metadata": {"language": "en", "sample_rate": 16000}},
        "tts": {"model": "sonic-3",
                "metadata": {"voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b",
                             "language": "en", "sample_rate": 24000}},
    },
    "elevenlabs": {
        "env_key": "ELEVENLABS_API_KEY",
        "stt": {"model": "scribe_v1_experimental"},
        "tts": {"model": "eleven_flash_v2_5",
                "metadata": {"voice_id": "CwhRBWXzGAHq8TQ4Fs17"}},
    },
    "sarvam": {
        "env_key": "SARVAM_API_KEY",
        "stt": {"model": "saarika:v2.5",
                "metadata": {"language": "en-IN", "sample_rate": 16000}},
        "tts": {"model": "bulbul:v3",
                "metadata": {"voice_id": "shubh", "language": "en-IN", "sample_rate": 24000}},
    },
    "assemblyai": {"env_key": "ASSEMBLYAI_API_KEY", "stt": {"metadata": {"sample_rate": 16000}}},
    "gladia":     {"env_key": "GLADIA_API_KEY",     "stt": {"model": "solaria-1"}},
    "soniox":     {"env_key": "SONIOX_API_KEY",     "stt": {}},
    "hathora": {
        "env_key": "HATHORA_API_KEY",
        "stt": {"model": "parakeet"},
        "tts": {"model": "hexgrad-kokoro-82m", "metadata": {"voice_id": "af_alloy"}},
    },
    "hume":    {"env_key": "HUME_API_KEY",
                "tts": {"metadata": {"voice_id": "d8ab67c6-953d-4bd8-9370-8fa53a0f1453"}}},
    "inworld": {"env_key": "INWORLD_API_KEY",
                "tts": {"model": "inworld-tts-1.5-max", "metadata": {"voice_id": "Ashley"}}},
    "neuphonic": {"env_key": "NEUPHONIC_API_KEY",
                  "tts": {"model": "neu_hq",
                          "metadata": {"voice_id": "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6",
                                       "language": "en"}}},
    "resemble": {"env_key": "RESEMBLE_API_KEY",
                 "tts": {"metadata": {"voice_id": "55592656", "language": "en"}}},
    "lmnt":     {"env_key": "LMNT_API_KEY",      "tts": {"metadata": {"voice_id": "ava"}}},
    "fish":     {"env_key": "FISHER_API_KEY",
                 "tts": {"model": "s1",
                         "metadata": {"voice_id": "0eb2bd3576714dbcad7cd4c6b2b6e12f"}}},
    "camb":     {"env_key": "CAMB_API_KEY",      "tts": {"metadata": {"voice_id": "1"}}},
    "asyncai_http": {"env_key": "ASYNC_API_KEY",
                     "tts": {"metadata": {"voice_id": "13616e5f-6fda-4247-b548-8821cb71fb54"}}},
}


def discover_probes() -> List[ProbeSpec]:
    """Auto-build probes for every provider whose env key is set in `.env`.

    One row per (provider, kind) — so if a provider ships LLM+STT+TTS and its
    key is set, all three are probed. Providers whose env key isn't set are
    silently skipped (no noise in the output).
    """
    probes: List[ProbeSpec] = []
    for provider, cfg in PROVIDER_CATALOG.items():
        env_key = cfg["env_key"]
        if not os.environ.get(env_key, "").strip():
            continue
        for kind in ("llm", "stt", "tts"):
            defaults = cfg.get(kind)
            if defaults is None:
                continue
            probes.append(ProbeSpec(
                kind=kind,
                provider=provider,
                env_key=env_key,
                model=defaults.get("model"),
                metadata=defaults.get("metadata") or {},
                model_meta_data=defaults.get("model_meta_data") or {},
            ))
    return probes


# --- probe payloads (mirror core/services/readiness/probes.py) --------------
_LLM_PROBE_PROMPT = "Reply with the single word OK."
_TTS_PROBE_TEXT = "This is a readiness test."
_STT_ASSET = REPO_ROOT / "core" / "services" / "readiness" / "assets" / "probe_sample.wav"


def _load_stt_audio(target_rate: int, provider: str) -> tuple[bytes, bool]:
    """Return (audio_bytes, is_real_audio).

    HTTP-batch STTs (OpenAI/Groq) want the full WAV; streaming STTs
    (Deepgram, AssemblyAI, Sarvam, ...) want headerless PCM. Falls back to
    0.5s of silence when the bundled asset is missing.
    """
    if not _STT_ASSET.exists():
        return b"\x00\x00" * (target_rate // 2), False

    raw = _STT_ASSET.read_bytes()
    if provider in {"openai", "groq"}:
        return raw, True

    import audioop, io
    with wave.open(io.BytesIO(raw), "rb") as w:
        pcm = w.readframes(w.getnframes())
        native = w.getframerate()
    if native == target_rate:
        return pcm, True
    converted, _ = audioop.ratecv(pcm, 2, 1, native, target_rate, None)
    return converted, True


# --- probes ------------------------------------------------------------------
async def _probe_llm(spec: ProbeSpec, service) -> tuple[bool, str]:
    from pipecat.frames.frames import (
        EndFrame, LLMContextFrame, LLMFullResponseEndFrame, LLMTextFrame,
    )
    from pipecat.pipeline.task import PipelineParams
    from pipecat.processors.aggregators.llm_context import LLMContext
    from core.services.readiness.probe_pipeline import probe_in_pipeline

    def is_response(f):
        if isinstance(f, LLMTextFrame):
            return bool((getattr(f, "text", "") or "").strip())
        return isinstance(f, LLMFullResponseEndFrame)

    ctx = LLMContext(messages=[{"role": "user", "content": _LLM_PROBE_PROMPT}])
    frames = [LLMContextFrame(context=ctx), EndFrame()]
    params = PipelineParams(audio_in_sample_rate=16000, audio_out_sample_rate=24000,
                            enable_metrics=False)
    ok, frame, err = await probe_in_pipeline(
        service, frames, is_response, params=params,
        timeout_s=20.0, provider=spec.provider,
    )
    if ok and isinstance(frame, LLMTextFrame):
        snippet = (frame.text or "").strip().replace("\n", " ")[:60]
        return True, f"responded: {snippet!r}"
    if ok:
        return True, "round-trip ok (no text within budget)"
    return False, err or "no response within budget"


async def _probe_stt(spec: ProbeSpec, service) -> tuple[bool, str]:
    from pipecat.frames.frames import (
        InputAudioRawFrame, InterimTranscriptionFrame, TranscriptionFrame,
        VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame,
    )
    from pipecat.pipeline.task import PipelineParams
    from core.services.readiness.probe_pipeline import probe_in_pipeline

    target_rate = int((spec.metadata or {}).get("sample_rate") or 16000)
    audio, real = _load_stt_audio(target_rate, spec.provider)

    def is_transcript(f):
        if isinstance(f, (TranscriptionFrame, InterimTranscriptionFrame)):
            return bool((getattr(f, "text", "") or "").strip())
        return False

    frames = [
        VADUserStartedSpeakingFrame(),
        InputAudioRawFrame(audio=audio, sample_rate=target_rate, num_channels=1),
        VADUserStoppedSpeakingFrame(),
    ]
    params = PipelineParams(audio_in_sample_rate=target_rate, audio_out_sample_rate=24000,
                            enable_metrics=False)
    ok, frame, err = await probe_in_pipeline(
        service, frames, is_transcript, params=params,
        timeout_s=25.0, provider=spec.provider,
        warmup_s=3.0, end_frame_after_s=3.0,
    )
    if ok and frame is not None:
        text = (getattr(frame, "text", "") or "").strip().replace("\n", " ")[:60]
        return True, f"transcribed: {text!r}"
    if not real:
        return False, "no probe WAV available (silence-only probe can't confirm)"
    return False, err or "no transcript within budget"


async def _probe_tts(spec: ProbeSpec, service) -> tuple[bool, str]:
    from pipecat.frames.frames import TTSAudioRawFrame, TTSSpeakFrame
    from pipecat.pipeline.task import PipelineParams
    from core.services.readiness.probe_pipeline import probe_in_pipeline

    def is_audio(f):
        if isinstance(f, TTSAudioRawFrame) and getattr(f, "audio", None):
            return True
        return bool(getattr(f, "audio", None)) and hasattr(f, "sample_rate")

    frames = [TTSSpeakFrame(text=_TTS_PROBE_TEXT)]
    out_rate = int((spec.metadata or {}).get("sample_rate") or 24000)
    params = PipelineParams(audio_in_sample_rate=16000, audio_out_sample_rate=out_rate,
                            enable_metrics=False)
    ok, _frame, err = await probe_in_pipeline(
        service, frames, is_audio, params=params,
        timeout_s=18.0, provider=spec.provider, warmup_s=2.0,
    )
    if ok:
        return True, "synthesised audio ok"
    return False, err or "no audio within budget"


# --- driver ------------------------------------------------------------------
async def run_probe(spec: ProbeSpec) -> tuple[str, bool, str]:
    """Return (label, ok, message) for one spec."""
    label = f"{spec.kind.upper():3s}  {spec.provider:<12s} ({spec.model or '-'})"

    api_key = os.environ.get(spec.env_key, "").strip()
    if not api_key:
        return label, False, f"no key in .env ({spec.env_key})"

    from core.services.pipeline import service_factory
    build_spec = {
        "provider_name": spec.provider,
        "api_key": api_key,
        "model_name": spec.model,
        "metadata": dict(spec.metadata or {}),
        "model_meta_data": dict(spec.model_meta_data or {}),
    }

    if spec.kind == "llm":
        # Only cap via max_completion_tokens — newer OpenAI models (gpt-4o-mini,
        # o1, ...) reject having both max_tokens AND max_completion_tokens set.
        # Providers whose InputParams don't declare this key (Anthropic, Google,
        # AWS Bedrock) silently drop it via `build_input_params`.
        build_spec["metadata"].setdefault("max_completion_tokens", 1024)

    try:
        if spec.kind == "llm":
            service = service_factory.build_llm(build_spec)
        elif spec.kind == "stt":
            service = service_factory.build_stt(build_spec)
        elif spec.kind == "tts":
            service = service_factory.build_tts(build_spec)
        else:
            return label, False, f"unknown kind: {spec.kind}"
    except Exception as exc:  # noqa: BLE001
        return label, False, f"construct failed: {exc}"

    if service is None:
        return label, False, "factory returned None (provider not supported?)"

    try:
        if spec.kind == "llm":
            ok, msg = await _probe_llm(spec, service)
        elif spec.kind == "stt":
            ok, msg = await _probe_stt(spec, service)
        else:
            ok, msg = await _probe_tts(spec, service)
    except Exception as exc:  # noqa: BLE001
        return label, False, f"probe raised: {exc}"

    return label, ok, msg


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--only", help="filter by provider name (e.g. openai)")
    parser.add_argument("--kind", choices=["llm", "stt", "tts"],
                        help="filter by service kind")
    args = parser.parse_args()

    all_probes = discover_probes()
    selected = [
        s for s in all_probes
        if (args.only is None or s.provider == args.only)
        and (args.kind is None or s.kind == args.kind)
    ]
    if not selected:
        if not all_probes:
            print("no provider API keys found in .env — nothing to probe", file=sys.stderr)
        else:
            print("no probes match filter", file=sys.stderr)
        return 2

    print(f"Discovered {len(all_probes)} probe(s) from .env; running {len(selected)}.")
    print(f"Full log -> {LOG_PATH}\n")
    results = []
    for spec in selected:
        label, ok, msg = await run_probe(spec)
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {label} - {msg}")
        results.append(ok)

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    print(f"Full log -> {LOG_PATH}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
