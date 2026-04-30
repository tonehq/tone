"""
TTS Voice Testing Script
=========================
Tests every active TTS provider's voices with each supported language
using the same hardcoded model as agent_factory_service.get_tts_for_agent.

Usage:
    python dev/test_tts_voices.py
    python dev/test_tts_voices.py --provider cartesia
    python dev/test_tts_voices.py --provider cartesia --limit 5
    python dev/test_tts_voices.py --output results.csv

Output: CSV report with pass/fail per (provider, voice_id, language).
"""

import os
import sys
import csv
import asyncio
import argparse
import time
import traceback
from datetime import datetime

# Ensure project root is on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv()

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Config — hardcoded DB URL + JWT secret (same as shared/config.py)
# ---------------------------------------------------------------------------
DATABASE_URL = "postgresql://neondb_owner:npg_6MIP1wKAkFQh@ep-round-pond-anxl0114-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")

TEST_TEXT = "Hello, this is a voice test."

# ---------------------------------------------------------------------------
# Hardcoded models — exactly matching agent_factory_service.get_tts_for_agent
# ---------------------------------------------------------------------------
HARDCODED_MODELS = {
    "cartesia": "sonic-3",
    "openai": "gpt-4o-mini-tts",
    "elevenlabs": "eleven_v3",
    "deepgram": "aura-2",
    "google": None,  # passed via params
    "groq": "canopylabs/orpheus-v1-english",  # overridden for arabic
    "hathora": "hexgrad-kokoro-82m",
    "minimax": "speech-2.8-turbo",
    "neuphonic": "neu_hq",
    "rime": "mistv2",
    "sarvam": "bulbul:v3",
    "fish": "s1",
    "hume": "2",
    "inworld": "inworld-tts-1.5-max",
    "azure": None,  # passed via params
    "aws_polly": None,  # passed via params
    "playht": None,  # no model param
    "asyncai_http": None,  # no model param
    "camb": None,  # no model param
    "lmnt": None,  # no model param
    "resemble": None,  # no model param
    "nvidia": None,  # passed via params
    "speechmatics": None,  # no model param
    "google_base": None,  # passed via params
}

# ---------------------------------------------------------------------------
# Encryption (same as core/utils/encryption.py)
# ---------------------------------------------------------------------------
def _get_fernet() -> Fernet:
    key = JWT_SECRET_KEY.encode()
    salt = b"tone_salt"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    derived_key = base64.urlsafe_b64encode(kdf.derive(key))
    return Fernet(derived_key)


def decrypt(encrypted_data: str) -> str:
    return _get_fernet().decrypt(encrypted_data.encode()).decode()


# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    return SessionLocal()


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------
def get_active_tts_services(db, provider_filter=None):
    """
    Get active TTS services joined with their provider and API key.
    Returns list of dicts: {service_id, provider_name, display_name, provider_id, api_key}
    """
    from core.models.service import Service
    from core.models.service_provider import ServiceProvider
    from core.models.api_key import ApiKey

    query = (
        db.query(Service, ServiceProvider, ApiKey)
        .join(ServiceProvider, Service.service_provider_id == ServiceProvider.id)
        .outerjoin(ApiKey, Service.api_key_id == ApiKey.id)
        .filter(
            Service.service_type == "tts",
            Service.status == "active",
        )
    )

    if provider_filter:
        query = query.filter(ServiceProvider.name == provider_filter)

    results = []
    for svc, provider, api_key in query.all():
        api_key_value = None
        if api_key and api_key.api_key_encrypted:
            try:
                api_key_value = decrypt(api_key.api_key_encrypted)
            except Exception as e:
                print(f"  [WARN] Failed to decrypt API key for {provider.name}: {e}")

        results.append({
            "service_id": svc.id,
            "provider_name": (provider.name or "").strip().lower(),
            "display_name": provider.display_name,
            "provider_id": provider.id,
            "api_key": api_key_value,
            "meta_data": (svc.config or {}),
        })

    return results


def get_voices_for_provider(db, provider_id, limit=None):
    """Get all active voices for a provider."""
    from core.models.voice import Voice

    query = (
        db.query(Voice)
        .filter(Voice.service_provider_id == provider_id, Voice.is_active == True)
        .order_by(Voice.id)
    )
    if limit:
        query = query.limit(limit)
    return query.all()


# ---------------------------------------------------------------------------
# Voice ID transformations — exactly matching get_tts_for_agent
# ---------------------------------------------------------------------------
def transform_voice_id(provider_name, voice_id):
    """Apply same voice_id transformations as agent_factory_service."""
    if provider_name == "sarvam" and voice_id:
        # Strip "sarvam-" prefix and language suffix
        sarvam_voice = voice_id
        if sarvam_voice.startswith("sarvam-"):
            parts = sarvam_voice.split("-")
            if len(parts) >= 3:
                sarvam_voice = parts[1]
        return sarvam_voice
    return voice_id


def get_model_for_provider(provider_name, language=None):
    """Get the hardcoded model — exactly matching get_tts_for_agent."""
    if provider_name == "groq":
        return "canopylabs/orpheus-arabic-saudi" if language == "ar" else "canopylabs/orpheus-v1-english"
    return HARDCODED_MODELS.get(provider_name)


# ---------------------------------------------------------------------------
# TTS service instantiation — mirrors get_tts_for_agent exactly
# ---------------------------------------------------------------------------
async def test_voice(provider_name, api_key, model, voice_id, language, meta_data):
    """
    Instantiate TTS service exactly like get_tts_for_agent and try to generate audio.
    Returns (success: bool, error_message: str or None)
    """
    import aiohttp

    # Providers that need an aiohttp session (same list as agent_factory_service + elevenlabs for HTTP variant)
    _http_providers = {"asyncai_http", "deepgram", "elevenlabs", "minimax", "neuphonic", "rime", "sarvam", "speechmatics"}
    sessions = []

    def make_session():
        s = aiohttp.ClientSession()
        sessions.append(s)
        return s

    session = make_session() if provider_name in _http_providers else None

    try:
        tts_service = _build_tts_service(provider_name, api_key, model, voice_id, language, meta_data, session)
        if tts_service is None:
            return False, "Failed to build TTS service (unsupported or import error)"

        # Try to generate audio
        audio_bytes = await _generate_audio(tts_service, TEST_TEXT)
        if audio_bytes and len(audio_bytes) > 0:
            return True, None
        else:
            return False, "No audio bytes returned"

    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"
    finally:
        for s in sessions:
            await s.close()


def _build_tts_service(provider_name, api_key, model, voice_id, language, meta_data, session):
    """Build the TTS service instance — mirrors get_tts_for_agent exactly."""
    try:
        if provider_name == "cartesia":
            from pipecat.services.cartesia.tts import CartesiaTTSService
            return CartesiaTTSService(
                api_key=api_key,
                model=model or "sonic-3",
                voice_id=voice_id or "e07c00bc-4134-4eae-9ea4-1a55fb45746b",
                language=language or "en",
            )

        if provider_name == "openai":
            from pipecat.services.openai.tts import OpenAITTSService
            kwargs = {}
            if voice_id is not None:
                kwargs["voice"] = voice_id
            kwargs["language"] = language
            return OpenAITTSService(api_key=api_key, model=model or "gpt-4o-mini-tts", **kwargs)

        if provider_name == "elevenlabs":
            from pipecat.services.elevenlabs.tts import ElevenLabsHttpTTSService
            return ElevenLabsHttpTTSService(
                api_key=api_key,
                model=model or "eleven_v3",
                voice_id=voice_id or "CwhRBWXzGAHq8TQ4Fs17",
                aiohttp_session=session,
            )

        if provider_name == "playht":
            from pipecat.services.playht.tts import PlayHTTTSService
            user_id = meta_data.get("user_id") or ""
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_url"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return PlayHTTTSService(api_key=api_key, user_id=user_id, **kwargs)

        if provider_name == "asyncai_http":
            from pipecat.services.asyncai.tts import AsyncAIHttpTTSService
            return AsyncAIHttpTTSService(
                api_key=api_key,
                aiohttp_session=session,
                voice_id=voice_id or "13616e5f-6fda-4247-b548-8821cb71fb54",
                language=language,
            )

        if provider_name == "aws_polly":
            from pipecat.services.aws.tts import AWSPollyTTSService
            aws_access_key_id = meta_data.get("aws_access_key_id") or ""
            region = meta_data.get("region") or "us-east-1"
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_id"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return AWSPollyTTSService(api_key=api_key, aws_access_key_id=aws_access_key_id, region=region, **kwargs)

        if provider_name == "camb":
            from pipecat.services.camb.tts import CambTTSService
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_id"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return CambTTSService(api_key=api_key, **kwargs)

        if provider_name == "deepgram":
            from pipecat.services.deepgram.tts import DeepgramHttpTTSService
            return DeepgramHttpTTSService(
                api_key=api_key,
                model=model or "aura-2",
                voice=voice_id or "aura-2-helena-en",
                aiohttp_session=session,
            )

        if provider_name == "google":
            from pipecat.services.google.tts import GoogleTTSService
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_id"] = voice_id
            return GoogleTTSService(credentials=api_key, **kwargs)

        if provider_name == "groq":
            from pipecat.services.groq.tts import GroqTTSService
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_id"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return GroqTTSService(api_key=api_key, model_name=model or "canopylabs/orpheus-v1-english", **kwargs)

        if provider_name == "hathora":
            from pipecat.services.hathora.tts import HathoraTTSService
            return HathoraTTSService(
                api_key=api_key,
                model=model or "hexgrad-kokoro-82m",
                voice_id=voice_id,
                language=language,
            )

        if provider_name == "minimax":
            from pipecat.services.minimax.tts import MiniMaxHttpTTSService
            group_id = meta_data.get("group_id") or ""
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_id"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return MiniMaxHttpTTSService(
                api_key=api_key, group_id=group_id, model=model or "speech-2.8-turbo",
                aiohttp_session=session, **kwargs,
            )

        if provider_name == "neuphonic":
            from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
            return NeuphonicHttpTTSService(
                api_key=api_key,
                model=model or "neu_hq",
                aiohttp_session=session,
                voice_id=voice_id or "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6",
                language=language,
            )

        if provider_name == "nvidia":
            from pipecat.services.nvidia.tts import NvidiaTTSService
            server = meta_data.get("server") or "grpc.nvcf.nvidia.com:443"
            kwargs = {}
            if voice_id is not None:
                kwargs["voice_id"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return NvidiaTTSService(api_key=api_key, server=server, **kwargs)

        if provider_name == "rime":
            from pipecat.services.rime.tts import RimeHttpTTSService
            return RimeHttpTTSService(
                api_key=api_key,
                model=model or "mistv2",
                aiohttp_session=session,
                voice_id=voice_id or "albion",
            )

        if provider_name == "sarvam":
            from pipecat.services.sarvam.tts import SarvamHttpTTSService
            return SarvamHttpTTSService(
                api_key=api_key,
                model=model or "bulbul:v3",
                aiohttp_session=session,
                voice_id=voice_id,
                language=language,
            )

        if provider_name == "speechmatics":
            from pipecat.services.speechmatics.tts import SpeechmaticsTTSService
            return SpeechmaticsTTSService(
                api_key=api_key,
                aiohttp_session=session,
                voice_id=voice_id,
                language=language,
            )

        if provider_name == "azure":
            from pipecat.services.azure.tts import AzureTTSService
            region = meta_data.get("region") or "eastus"
            kwargs = {}
            if voice_id is not None:
                kwargs["voice"] = voice_id
            if language is not None:
                kwargs["language"] = language
            return AzureTTSService(api_key=api_key, region=region, **kwargs)

        if provider_name == "fish":
            from pipecat.services.fish.tts import FishAudioTTSService
            return FishAudioTTSService(
                api_key=api_key,
                model_id=model or "s1",
                reference_id=voice_id or "0eb2bd3576714dbcad7cd4c6b2b6e12f",
                language=language,
            )

        if provider_name == "hume":
            from pipecat.services.hume.tts import HumeTTSService
            return HumeTTSService(
                api_key=api_key,
                version=model or "2",
                voice_id=voice_id or "d8ab67c6-953d-4bd8-9370-8fa53a0f1453",
                language=language,
            )

        if provider_name == "inworld":
            from pipecat.services.inworld.tts import InworldTTSService
            return InworldTTSService(
                api_key=api_key,
                model=model or "inworld-tts-1.5-max",
                voice_id=voice_id,
                language=language,
            )

        if provider_name == "lmnt":
            from pipecat.services.lmnt.tts import LmntTTSService
            kwargs = {}
            kwargs["voice_id"] = voice_id or "ava"
            if language is not None:
                kwargs["language"] = language
            return LmntTTSService(api_key=api_key, **kwargs)

        if provider_name == "resemble":
            from pipecat.services.resembleai.tts import ResembleAITTSService
            kwargs = {}
            kwargs["voice_id"] = voice_id
            kwargs["language"] = language
            return ResembleAITTSService(api_key=api_key, **kwargs)

        return None

    except ImportError as e:
        print(f"  [WARN] Import failed for {provider_name}: {e}")
        return None


async def _initialize_service(tts_service):
    """Initialize the TTS service by calling start() with a StartFrame.

    Pipecat services set up internal state (clients, queues, tasks) in start().
    Without this, run_tts fails with missing attributes like _contexts_queue.
    """
    from pipecat.frames.frames import StartFrame

    try:
        start_frame = StartFrame(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            allow_interruptions=False,
            enable_metrics=False,
            enable_tracing=False,
            enable_usage_metrics=False,
        )
        await tts_service.start(start_frame)
    except Exception:
        # Some services may not fully support standalone start.
        # Manually set the minimum required attributes as fallback.
        if not hasattr(tts_service, "_sample_rate") or tts_service._sample_rate is None:
            tts_service._sample_rate = 24000


async def _cleanup_service(tts_service):
    """Clean up the TTS service after testing."""
    from pipecat.frames.frames import EndFrame

    try:
        await tts_service.stop(EndFrame())
    except Exception:
        pass


async def _generate_audio(tts_service, text):
    """
    Run the TTS service to generate audio frames.
    Collects all output frames and returns concatenated audio bytes.
    """
    from pipecat.frames.frames import TTSSpeakFrame, TTSAudioRawFrame, Frame, ErrorFrame

    # Initialize the service (sets up _contexts_queue, _client, etc.)
    await _initialize_service(tts_service)

    audio_chunks = []
    error_msg = None

    # Use run_tts to generate audio
    try:
        async for frame in tts_service.run_tts(text):
            if isinstance(frame, TTSAudioRawFrame):
                audio_chunks.append(frame.audio)
            elif isinstance(frame, ErrorFrame):
                error_msg = str(frame.error) if hasattr(frame, "error") else str(frame)
                break
    except Exception as e:
        await _cleanup_service(tts_service)
        raise e

    await _cleanup_service(tts_service)

    if error_msg:
        raise Exception(error_msg)

    return b"".join(audio_chunks) if audio_chunks else None


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------
async def _test_one_voice(semaphore, provider_name, api_key, voice, lang, meta_data):
    """Test a single voice+language combo with concurrency control."""
    async with semaphore:
        transformed_voice_id = transform_voice_id(provider_name, voice.voice_id)
        model = get_model_for_provider(provider_name, lang)

        start_time = time.time()
        try:
            success, error = await asyncio.wait_for(
                test_voice(provider_name, api_key, model, transformed_voice_id, lang, meta_data),
                timeout=30,
            )
        except asyncio.TimeoutError:
            success, error = False, "Timeout (30s)"

        elapsed = round(time.time() - start_time, 2)

        status = "PASS" if success else "FAIL"
        status_msg = f"PASS ({elapsed}s)" if success else f"FAIL ({elapsed}s) — {error}"
        print(f"  {voice.name} | voice_id={voice.voice_id} | lang={lang} ... {status_msg}")

        return {
            "provider": provider_name,
            "display_name": "",  # filled by caller
            "model": model,
            "voice_id": voice.voice_id,
            "voice_name": voice.name,
            "language": lang,
            "status": status,
            "error": error or "",
            "time_seconds": elapsed,
        }


async def run_tests(provider_filter=None, limit=None, output_file=None, concurrency=10):
    db = get_db()

    print("=" * 70)
    print("TTS Voice Test Runner")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Concurrency: {concurrency} parallel calls per provider")
    print("=" * 70)

    services = get_active_tts_services(db, provider_filter)
    if not services:
        print("\nNo active TTS services found.")
        return

    print(f"\nFound {len(services)} active TTS service(s):\n")
    for svc in services:
        print(f"  - {svc['display_name']} ({svc['provider_name']}) | API key: {'YES' if svc['api_key'] else 'NO'}")

    results = []
    total_pass = 0
    total_fail = 0
    total_skip = 0

    for svc in services:
        provider_name = svc["provider_name"]
        api_key = svc["api_key"]

        if not api_key:
            print(f"\n[SKIP] {svc['display_name']} — no API key")
            total_skip += 1
            continue

        voices = get_voices_for_provider(db, svc["provider_id"], limit)
        if not voices:
            print(f"\n[SKIP] {svc['display_name']} — no active voices")
            total_skip += 1
            continue

        # Count total test cases for this provider
        test_count = sum(
            len(v.language_list) if v.language_list else 1
            for v in voices
        )

        print(f"\n{'─' * 70}")
        print(f"Testing: {svc['display_name']} ({provider_name})")
        print(f"  Voices: {len(voices)} | Test cases: {test_count} | Concurrency: {concurrency}")
        print(f"  Hardcoded model: {HARDCODED_MODELS.get(provider_name, 'N/A')}")
        print(f"{'─' * 70}")

        # Build all tasks for this provider
        semaphore = asyncio.Semaphore(concurrency)
        tasks = []
        for voice in voices:
            languages = voice.language_list if voice.language_list else [voice.language]
            for lang in languages:
                tasks.append(_test_one_voice(semaphore, provider_name, api_key, voice, lang, svc["meta_data"]))

        # Run all tasks in parallel (bounded by semaphore)
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        provider_pass = 0
        provider_fail = 0
        for r in provider_results:
            if isinstance(r, Exception):
                print(f"  [ERROR] Unexpected: {r}")
                provider_fail += 1
                total_fail += 1
                results.append({
                    "provider": provider_name, "display_name": svc["display_name"],
                    "model": "", "voice_id": "", "voice_name": "",
                    "language": "", "status": "FAIL",
                    "error": f"Unexpected: {r}", "time_seconds": 0,
                })
            else:
                r["display_name"] = svc["display_name"]
                results.append(r)
                if r["status"] == "PASS":
                    provider_pass += 1
                    total_pass += 1
                else:
                    provider_fail += 1
                    total_fail += 1

        print(f"\n  Result: {provider_pass} passed, {provider_fail} failed")

    db.close()

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total: {total_pass + total_fail} tests")
    print(f"  Pass:  {total_pass}")
    print(f"  Fail:  {total_fail}")
    print(f"  Skip:  {total_skip} provider(s)")
    print(f"{'=' * 70}")

    # Write CSV
    output = output_file or f"dev/tts_voice_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "provider", "display_name", "model", "voice_id", "voice_name",
            "language", "status", "error", "time_seconds",
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults saved to: {output}")

    # Print failed voices summary
    failed = [r for r in results if r["status"] == "FAIL"]
    if failed:
        print(f"\n{'─' * 70}")
        print(f"FAILED VOICES ({len(failed)}):")
        print(f"{'─' * 70}")
        for r in failed:
            print(f"  {r['provider']} | {r['voice_id']} | {r['language']} | {r['error']}")


def main():
    parser = argparse.ArgumentParser(description="Test TTS voices against real provider APIs")
    parser.add_argument("--provider", type=str, help="Test only this provider (e.g., cartesia)")
    parser.add_argument("--limit", type=int, help="Max voices per provider")
    parser.add_argument("--output", type=str, help="Output CSV file path")
    parser.add_argument("--concurrency", type=int, default=10, help="Max parallel calls per provider (default: 10)")
    args = parser.parse_args()

    asyncio.run(run_tests(
        provider_filter=args.provider,
        limit=args.limit,
        output_file=args.output,
        concurrency=args.concurrency,
    ))


if __name__ == "__main__":
    main()
