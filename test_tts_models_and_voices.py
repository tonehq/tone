"""
Test TTS service providers by iterating: Provider → Models → Voices.

For each given service provider ID:
  1. Fetch all active TTS models for that provider
  2. Fetch all active voices for that provider
  3. Test every (model, voice) combination by generating speech

Usage:
    python test_tts_models_and_voices.py 47              # single provider
    python test_tts_models_and_voices.py 47 51 55        # multiple providers
    python test_tts_models_and_voices.py 47,51,55        # comma-separated
    python test_tts_models_and_voices.py                  # uses default list
"""

import argparse
import asyncio
import io
import sys
import os
import time
import wave

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import Optional
from sqlalchemy.orm import Session

from core.database.session import get_db_script
from core.models.voice import Voice
from core.models.service_provider import ServiceProvider
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.models import Model
from core.models.api_key import ApiKey
from core.services.agent_factory_service import AgentFactoryService
from core.context import set_tenant_context
from core.models.organization import Organization
from core.utils.encryption import decrypt

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_SERVICE_PROVIDER_IDS = [47]

TEST_TEXT = "Hello, this is a test of the text to speech system."

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Default languages per provider (used when voice has no language set)
DEFAULT_LANGUAGES = {
    "cartesia": "en",
    "openai": "en",
    "elevenlabs": "en",
    "playht": "english",
    "asyncai_http": "en",
    "aws_polly": "en-US",
    "camb": "en",
    "deepgram": "en",
    "google_base": "en-US",
    "groq": "en",
    "hathora": "en",
    "minimax": "en",
    "neuphonic": "en",
    "nvidia": "en-US",
    "rime": "en",
    "sarvam": "hi-IN",
    "speechmatics": "en",
    "azure": "en-US",
    "fish": "en",
    "hume": "en",
    "inworld": "en",
    "lmnt": "en",
    "resemble": "en",
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_provider(db: Session, service_provider_id: int) -> ServiceProvider | None:
    """Get the ServiceProvider record."""
    return (
        db.query(ServiceProvider)
        .filter(ServiceProvider.id == service_provider_id)
        .first()
    )


def get_tts_models(db: Session, service_provider_id: int) -> list[Model]:
    """Get all active TTS models for a service provider."""
    return (
        db.query(Model)
        .filter(
            Model.service_provider_id == service_provider_id,
            Model.service_type == "tts",
            Model.status == "active",
        )
        .all()
    )


def get_voices(db: Session, service_provider_id: int) -> list[Voice]:
    """Get all active voices for a service provider."""
    return (
        db.query(Voice)
        .filter(
            Voice.service_provider_id == service_provider_id,
            Voice.is_active == True,
        )
        .all()
    )


# ---------------------------------------------------------------------------
# Test agent creation
# ---------------------------------------------------------------------------

def create_test_agent(
    db: Session,
    service_provider_id: int,
    model_id: int | None,
    voice_id: str | None,
    language: str | None,
) -> Agent:
    """Create a temporary Agent + AgentConfig in the session (not committed).

    Passes model_id in tts_metadata so the factory resolves the correct model name.
    """
    ts = int(time.time() * 1000)
    agent = Agent(
        name=f"__tts_test_{service_provider_id}_{ts}",
        status="active",
    )
    db.add(agent)
    db.flush()

    tts_metadata = {}
    if model_id is not None:
        tts_metadata["model_id"] = model_id
    if voice_id is not None:
        tts_metadata["voice_id"] = voice_id
    if language is not None:
        tts_metadata["language"] = language

    config = AgentConfig(
        agent_id=agent.id,
        tts_service_id=service_provider_id,
        tts_metadata=tts_metadata,
        system_prompt="You are a test assistant.",
        status="active",
    )
    db.add(config)
    db.flush()

    return agent


# ---------------------------------------------------------------------------
# STT verification helpers
# ---------------------------------------------------------------------------

def get_stt_api_key(db: Session, stt_provider_id: int) -> Optional[str]:
    """Get decrypted API key for the provider.

    First tries STT models, then falls back to any active model with an API key
    (providers like Groq share the same key across LLM/STT/TTS).
    """
    # Try STT models first, then any model type
    for type_filter in ["stt", None]:
        query = db.query(Model).filter(
            Model.service_provider_id == stt_provider_id,
            Model.status == "active",
            Model.api_key_id.isnot(None),
        )
        if type_filter:
            query = query.filter(Model.service_type == type_filter)
        model_record = query.first()
        if model_record:
            api_key_record = db.query(ApiKey).filter(ApiKey.id == model_record.api_key_id).first()
            if api_key_record and api_key_record.api_key_encrypted:
                try:
                    return decrypt(api_key_record.api_key_encrypted)
                except Exception:
                    continue
    return None


def pcm_to_wav(pcm_audio: bytes, sample_rate: int, num_channels: int = 1) -> bytes:
    """Convert raw PCM 16-bit audio to WAV format."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_audio)
    return buf.getvalue()


async def transcribe_audio(
    wav_bytes: bytes,
    stt_provider_name: str,
    api_key: str,
) -> str:
    """Transcribe WAV audio back to text using the specified STT provider."""
    import aiohttp

    provider = stt_provider_name.strip().lower()

    if provider == "deepgram":
        url = "https://api.deepgram.com/v1/listen?model=nova-3-general&language=en"
        headers = {"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=wav_bytes) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return (
                        data.get("results", {})
                        .get("channels", [{}])[0]
                        .get("alternatives", [{}])[0]
                        .get("transcript", "")
                    ) or "(empty transcription)"
                raise Exception(f"Deepgram HTTP {resp.status}: {await resp.text()}")

    if provider in ("openai", "groq", "sambanova"):
        from openai import AsyncOpenAI
        base_urls = {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "sambanova": "https://api.sambanova.ai/v1",
        }
        models = {
            "openai": "whisper-1",
            "groq": "whisper-large-v3-turbo",
            "sambanova": "whisper-large-v3",
        }
        client = AsyncOpenAI(api_key=api_key, base_url=base_urls.get(provider))
        result = await client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes, "audio/wav"),
            model=models.get(provider, "whisper-1"),
        )
        await client.close()
        return result.text if result.text else "(empty transcription)"

    if provider == "elevenlabs":
        url = "https://api.elevenlabs.io/v1/speech-to-text"
        headers = {"xi-api-key": api_key}
        form = aiohttp.FormData()
        form.add_field("file", wav_bytes, filename="audio.wav", content_type="audio/wav")
        form.add_field("model_id", "scribe_v1")
        form.add_field("language_code", "eng")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("text", "(empty transcription)")
                raise Exception(f"ElevenLabs HTTP {resp.status}: {await resp.text()}")

    raise ValueError(f"Unsupported STT provider for verification: '{stt_provider_name}'. "
                     f"Supported: deepgram, openai, groq, sambanova, elevenlabs")


# ---------------------------------------------------------------------------
# Speech generation
# ---------------------------------------------------------------------------

async def generate_speech(tts_service, provider_name: str) -> tuple[bool, bytes, int]:
    """Try to generate audio frames from the TTS service.

    Returns (success, raw_pcm_audio, sample_rate).
    Fully consumes the run_tts generator to avoid 'async generator ignored
    GeneratorExit' errors caused by breaking out of generators that yield
    inside try/finally blocks.
    """
    # In a real Pipecat pipeline, processors are initialized via setup() and
    # start(). For standalone testing, we replicate that initialization here.
    if not getattr(tts_service, "_clock", None):
        from pipecat.clocks.system_clock import SystemClock
        from pipecat.processors.frame_processor import FrameProcessorSetup
        from pipecat.utils.asyncio.task_manager import TaskManager, TaskManagerParams
        from pipecat.frames.frames import StartFrame

        clock = SystemClock()
        clock.start()
        loop = asyncio.get_event_loop()
        task_manager = TaskManager()
        task_manager.setup(TaskManagerParams(loop=loop))
        setup = FrameProcessorSetup(clock=clock, task_manager=task_manager, observer=None)
        await tts_service.setup(setup)

        # Call start() with a StartFrame to initialize sample_rate, output_format, etc.
        start_frame = StartFrame(
            audio_in_sample_rate=24000,
            audio_out_sample_rate=24000,
            allow_interruptions=False,
            enable_metrics=False,
            enable_usage_metrics=False,
        )
        await tts_service.start(start_frame)

    if hasattr(tts_service, "run_tts"):
        from pipecat.frames.frames import ErrorFrame, TTSAudioRawFrame

        audio_chunks = []
        sample_rate = 16000
        has_error = False
        error_msg = None
        async for _frame in tts_service.run_tts(TEST_TEXT):
            if _frame is None:
                continue
            if isinstance(_frame, ErrorFrame):
                has_error = True
                error_msg = getattr(_frame, "error", None) or str(_frame)
            elif isinstance(_frame, TTSAudioRawFrame):
                audio_chunks.append(_frame.audio)
                sample_rate = _frame.sample_rate

        combined_audio = b"".join(audio_chunks)

        if has_error:
            raise RuntimeError(error_msg or "TTS returned an error frame")
        if len(audio_chunks) > 0:
            return True, combined_audio, sample_rate
        # WebSocket-based service with no errors and no audio frames
        return True, b"", sample_rate

    if hasattr(tts_service, "synthesize"):
        result = await tts_service.synthesize(TEST_TEXT)
        success = result is not None and len(result) > 0
        return success, result if success else b"", 16000

    raise RuntimeError(
        f"TTS service for {provider_name} has no run_tts or synthesize method"
    )


# ---------------------------------------------------------------------------
# Test a single (model, voice) combination
# ---------------------------------------------------------------------------

async def test_model_voice(
    db: Session,
    service_provider_id: int,
    provider_name: str,
    provider_internal_name: str,
    model_record: Model,
    voice_record: Voice,
    stt_provider_name: str | None = None,
    stt_api_key: str | None = None,
) -> dict:
    """Test a single model+voice combination and return the result dict."""
    voice_id = voice_record.voice_id
    language = voice_record.language or DEFAULT_LANGUAGES.get(provider_internal_name, "en")

    result = {
        "provider": provider_name,
        "model_id": model_record.id,
        "model_name": model_record.name,
        "voice_id": voice_id or "(default)",
        "voice_name": voice_record.name or "",
        "language": language,
        "status": "FAILED",
        "time_s": 0.0,
        "error": None,
        "transcription": None,
    }

    start = time.time()
    tts_service = None

    try:
        agent = create_test_agent(
            db, service_provider_id, model_record.id, voice_id, language,
        )

        factory = AgentFactoryService(db=db)
        tts_service = factory.get_tts_for_agent(agent)

        if tts_service is None:
            result["error"] = "get_tts_for_agent() returned None (missing config/credentials?)"
            return result

        success, raw_audio, sample_rate = await generate_speech(tts_service, provider_name)
        if success:
            result["status"] = "WORKING"
            # Transcribe audio back to text for verification
            if stt_provider_name and stt_api_key and len(raw_audio) > 0:
                try:
                    wav_bytes = pcm_to_wav(raw_audio, sample_rate)
                    transcribed = await transcribe_audio(wav_bytes, stt_provider_name, stt_api_key)
                    result["transcription"] = transcribed
                except Exception as e:
                    result["transcription"] = f"[STT error: {type(e).__name__}: {e}]"
        else:
            result["error"] = "No audio frames generated"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    finally:
        result["time_s"] = round(time.time() - start, 2)
        # Properly stop and close the TTS service
        if tts_service is not None:
            # Stop the service (cancels background tasks, closes websockets)
            try:
                from pipecat.frames.frames import EndFrame
                await tts_service.stop(EndFrame())
            except Exception:
                pass
            # Clean up processor resources (cancel internal tasks)
            try:
                await tts_service.cleanup()
            except Exception:
                pass
            # Close websocket if still open (ElevenLabs, Fish, etc.)
            ws = getattr(tts_service, "_websocket", None)
            if ws is not None:
                try:
                    await ws.close()
                except Exception:
                    pass
            # Close aiohttp session passed by the factory (asyncai, deepgram, etc.)
            session = getattr(tts_service, "_session", None)
            if session and hasattr(session, "close") and not session.closed:
                await session.close()
            # Close internal SDK client (e.g. Camb AsyncCambAI uses httpx/aiohttp)
            client = getattr(tts_service, "_client", None)
            if client is not None:
                close_fn = getattr(client, "close", None) or getattr(client, "aclose", None)
                if close_fn and callable(close_fn):
                    try:
                        result_or_coro = close_fn()
                        if asyncio.iscoroutine(result_or_coro) or asyncio.isfuture(result_or_coro):
                            await result_or_coro
                    except Exception:
                        pass
        db.rollback()

    return result


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def parse_provider_ids() -> list[int]:
    """Parse service provider IDs from command-line arguments.

    Supports:
        python script.py 47              # single id
        python script.py 47 51 55        # space-separated
        python script.py 47,51,55        # comma-separated
        python script.py 47 51,55 60     # mixed
        python script.py                 # falls back to DEFAULT_SERVICE_PROVIDER_IDS
    """
    parser = argparse.ArgumentParser(
        description="Test TTS service providers: Provider → Models → Voices.",
    )
    parser.add_argument(
        "provider_ids",
        nargs="*",
        help=(
            "Service provider IDs to test. "
            "Pass as space-separated (47 51 55) or comma-separated (47,51,55). "
            f"Defaults to {DEFAULT_SERVICE_PROVIDER_IDS} if omitted."
        ),
    )
    parser.add_argument(
        "--max-voices",
        type=int,
        default=0,
        help="Max voices to test per model (0 = all). Useful for large providers.",
    )
    parser.add_argument(
        "--verify",
        type=int,
        default=0,
        metavar="STT_PROVIDER_ID",
        help=(
            "STT service provider ID to use for audio verification. "
            "After TTS generates audio, it will be transcribed back to text "
            "using this STT provider so you can verify correctness. "
            "Supported providers: deepgram, openai, groq, sambanova, elevenlabs."
        ),
    )
    args = parser.parse_args()

    if not args.provider_ids:
        return DEFAULT_SERVICE_PROVIDER_IDS, args.max_voices, args.verify

    ids: list[int] = []
    for token in args.provider_ids:
        for part in token.split(","):
            part = part.strip()
            if part:
                try:
                    ids.append(int(part))
                except ValueError:
                    parser.error(f"Invalid provider ID: '{part}' (must be an integer)")
    if not ids:
        return DEFAULT_SERVICE_PROVIDER_IDS, args.max_voices, args.verify
    return ids, args.max_voices, args.verify


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------

def _truncate(text: str, max_len: int) -> str:
    return (text[:max_len - 2] + "..") if len(text) > max_len else text


def print_working_table(results: list[dict]):
    """Print a table of all WORKING combinations."""
    working = [r for r in results if r["status"] == "WORKING"]
    if not working:
        print(f"\n  {YELLOW}No working combinations.{RESET}")
        return

    has_transcriptions = any(r.get("transcription") for r in working)

    print(f"\n{BOLD}{GREEN}  WORKING Combinations ({len(working)}){RESET}")
    header = f"  {'#':<4} {'Provider':<16} {'Model':<22} {'Voice ID':<26} {'Voice Name':<20} {'Lang':<8} {'Time':>6}"
    separator = f"  {'-' * 4} {'-' * 16} {'-' * 22} {'-' * 26} {'-' * 20} {'-' * 8} {'-' * 6}"
    print(header)
    print(separator)

    for i, r in enumerate(working, 1):
        print(
            f"  {i:<4} {_truncate(r['provider'], 16):<16} "
            f"{_truncate(r['model_name'], 22):<22} "
            f"{_truncate(r['voice_id'], 26):<26} "
            f"{_truncate(r['voice_name'], 20):<20} "
            f"{r['language']:<8} {r['time_s']:>5.1f}s"
        )
        if r.get("transcription"):
            print(f"        {CYAN}→ \"{r['transcription']}\"{RESET}")


def print_failed_table(results: list[dict]):
    """Print a table of all FAILED combinations with error reasons."""
    failed = [r for r in results if r["status"] == "FAILED"]
    if not failed:
        print(f"\n  {GREEN}No failed combinations!{RESET}")
        return

    print(f"\n{BOLD}{RED}  FAILED Combinations ({len(failed)}){RESET}")
    print(f"  {'#':<4} {'Provider':<16} {'Model':<22} {'Voice ID':<26} {'Lang':<8} {'Time':>6}  {'Error'}")
    print(f"  {'-' * 4} {'-' * 16} {'-' * 22} {'-' * 26} {'-' * 8} {'-' * 6}  {'-' * 50}")

    for i, r in enumerate(failed, 1):
        error_msg = r["error"] or "Unknown error"
        print(
            f"  {i:<4} {_truncate(r['provider'], 16):<16} "
            f"{_truncate(r['model_name'], 22):<22} "
            f"{_truncate(r['voice_id'], 26):<26} "
            f"{r['language']:<8} {r['time_s']:>5.1f}s  "
            f"{RED}{error_msg}{RESET}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    provider_ids, max_voices, verify_stt_id = parse_provider_ids()

    print(f"\n{BOLD}{CYAN}{'=' * 90}{RESET}")
    print(f"{BOLD}{CYAN}  TTS Model & Voice Test Runner{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 90}{RESET}")
    print(f"\n  Testing provider IDs: {provider_ids}")
    if verify_stt_id:
        print(f"  Audio verification: ON (STT provider id={verify_stt_id})")
    print()

    db = get_db_script()
    results = []

    # Set tenant context
    org = db.query(Organization).first()
    if not org:
        print(f"{RED}ERROR: No organizations found in the database.{RESET}")
        db.close()
        return
    set_tenant_context(org_id=org.id)
    print(f"  Organization: {org.name} (id={org.id})\n")

    # Resolve STT provider for verification
    stt_provider_name = None
    stt_api_key_value = None
    if verify_stt_id:
        stt_provider = get_provider(db, verify_stt_id)
        if not stt_provider:
            print(f"{RED}ERROR: STT provider id={verify_stt_id} not found in DB.{RESET}")
            db.close()
            return
        stt_provider_name = (stt_provider.name or "").strip().lower()
        stt_api_key_value = "gAAAAABpt7S5mTItDizkL2L0bRVi5gialYerVHhAQnXQlCwLgaUM70DW9FfI4QV7jFpBjnvLMA0pUeIr0tOHHZg8rwK9ixfAvr6_vuhqxv66pzkoHWhoKDSd9bYlfIsDJBpT82cwep0vBdpDIUJcaw7RvRERhWkHoMl9ViyMuioA00FCxuOVuXVQCuLtmTbZfNgmKnME2WzC0U0ufVdKyP77xISmLFLFvkjHwQxc-5X88uEl1cP8XOtX-pSltWzfB1oOhDliOqLVh2rk-0C2iuXI_1SXwf_dnaC8pYsM5OS5igU_-L_pt0Q="
        if not stt_api_key_value:
            print(f"{RED}ERROR: No API key found for STT provider '{stt_provider.display_name or stt_provider.name}' (id={verify_stt_id}).{RESET}")
            db.close()
            return
        print(f"  STT provider: {stt_provider.display_name or stt_provider.name} ({stt_provider_name})\n")

    try:
        for sp_id in provider_ids:
            provider = get_provider(db, sp_id)
            if not provider:
                print(f"{YELLOW}[SKIP]{RESET} Provider id={sp_id}: not found in DB\n")
                continue

            provider_name = provider.display_name or provider.name or str(sp_id)
            provider_internal = (provider.name or "").strip().lower()

            # ── Get TTS models ──
            models = get_tts_models(db, sp_id)
            if not models:
                print(f"{YELLOW}[SKIP]{RESET} {provider_name} (id={sp_id}): no active TTS models\n")
                continue

            # ── Get voices ──
            voices = get_voices(db, sp_id)
            if not voices:
                print(f"{YELLOW}[SKIP]{RESET} {provider_name} (id={sp_id}): no active voices\n")
                continue

            test_voices = voices
            if max_voices and len(voices) > max_voices:
                test_voices = voices[:max_voices]

            total_combos = len(models) * len(test_voices)
            print(
                f"{BOLD}Provider: {provider_name} (id={sp_id}){RESET}\n"
                f"  Models: {len(models)}  |  Voices: {len(test_voices)}/{len(voices)}"
                f"{'  (sampled)' if len(test_voices) < len(voices) else ''}"
                f"  |  Combinations: {total_combos}"
            )

            # ── Iterate: model → voice ──
            for model_record in models:
                print(f"\n  {CYAN}Model: {model_record.name} (id={model_record.id}){RESET}")

                for voice_record in test_voices:
                    voice_label = voice_record.voice_id or voice_record.name or "default"
                    print(f"    Voice: {voice_label} ... ", end="", flush=True)

                    result = await test_model_voice(
                        db, sp_id, provider_name, provider_internal,
                        model_record, voice_record,
                        stt_provider_name=stt_provider_name,
                        stt_api_key=stt_api_key_value,
                    )
                    results.append(result)

                    if result["status"] == "WORKING":
                        print(f"{GREEN}WORKING{RESET} ({result['time_s']}s)")
                        if result["transcription"]:
                            print(f"      {CYAN}Transcription: \"{result['transcription']}\"{RESET}")
                    else:
                        print(f"{RED}FAILED{RESET} ({result['time_s']}s)")
                        if result["error"]:
                            print(f"      {RED}Error: {result['error']}{RESET}")

            print()

    finally:
        db.close()

    # ── Summary ──────────────────────────────────────────────────────────
    if not results:
        print(f"\n{YELLOW}No combinations were tested.{RESET}\n")
        return

    working_count = sum(1 for r in results if r["status"] == "WORKING")
    failed_count = sum(1 for r in results if r["status"] == "FAILED")

    print(f"\n{BOLD}{'=' * 90}{RESET}")
    print(f"{BOLD}  Results Summary{RESET}")
    print(f"{'=' * 90}")
    print(
        f"\n  {BOLD}Total: {len(results)}  |  "
        f"{GREEN}Working: {working_count}{RESET}  |  "
        f"{RED}Failed: {failed_count}{RESET}"
    )

    print_working_table(results)
    print_failed_table(results)

    print()


if __name__ == "__main__":
    asyncio.run(main())
