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
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy.orm import Session

from core.database.session import get_db_script
from core.models.voice import Voice
from core.models.service_provider import ServiceProvider
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.models import Model
from core.services.agent_factory_service import AgentFactoryService
from core.context import set_tenant_context
from core.models.organization import Organization

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
# Speech generation
# ---------------------------------------------------------------------------

async def generate_speech(tts_service, provider_name: str) -> bool:
    """Try to generate at least one audio frame from the TTS service."""
    if hasattr(tts_service, "run_tts"):
        frame_count = 0
        async for frame in tts_service.run_tts(TEST_TEXT):
            frame_count += 1
            if frame_count >= 1:
                return True
        return frame_count > 0

    if hasattr(tts_service, "synthesize"):
        result = await tts_service.synthesize(TEST_TEXT)
        return result is not None and len(result) > 0

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
    }

    start = time.time()

    try:
        agent = create_test_agent(
            db, service_provider_id, model_record.id, voice_id, language,
        )

        factory = AgentFactoryService(db=db)
        tts_service = factory.get_tts_for_agent(agent)

        if tts_service is None:
            result["error"] = "get_tts_for_agent() returned None (missing config/credentials?)"
            return result

        success = await generate_speech(tts_service, provider_name)
        if success:
            result["status"] = "WORKING"
        else:
            result["error"] = "No audio frames generated"

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    finally:
        result["time_s"] = round(time.time() - start, 2)
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
    args = parser.parse_args()

    if not args.provider_ids:
        return DEFAULT_SERVICE_PROVIDER_IDS

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
        return DEFAULT_SERVICE_PROVIDER_IDS
    return ids


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

    print(f"\n{BOLD}{GREEN}  WORKING Combinations ({len(working)}){RESET}")
    print(f"  {'#':<4} {'Provider':<16} {'Model':<22} {'Voice ID':<26} {'Voice Name':<20} {'Lang':<8} {'Time':>6}")
    print(f"  {'-' * 4} {'-' * 16} {'-' * 22} {'-' * 26} {'-' * 20} {'-' * 8} {'-' * 6}")

    for i, r in enumerate(working, 1):
        print(
            f"  {i:<4} {_truncate(r['provider'], 16):<16} "
            f"{_truncate(r['model_name'], 22):<22} "
            f"{_truncate(r['voice_id'], 26):<26} "
            f"{_truncate(r['voice_name'], 20):<20} "
            f"{r['language']:<8} {r['time_s']:>5.1f}s"
        )


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
    provider_ids = parse_provider_ids()

    print(f"\n{BOLD}{CYAN}{'=' * 90}{RESET}")
    print(f"{BOLD}{CYAN}  TTS Model & Voice Test Runner{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 90}{RESET}")
    print(f"\n  Testing provider IDs: {provider_ids}\n")

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

            total_combos = len(models) * len(voices)
            print(
                f"{BOLD}Provider: {provider_name} (id={sp_id}){RESET}\n"
                f"  Models: {len(models)}  |  Voices: {len(voices)}  |  "
                f"Combinations: {total_combos}"
            )

            # ── Iterate: model → voice ──
            for model_record in models:
                print(f"\n  {CYAN}Model: {model_record.name} (id={model_record.id}){RESET}")

                for voice_record in voices:
                    voice_label = voice_record.voice_id or voice_record.name or "default"
                    print(f"    Voice: {voice_label} ... ", end="", flush=True)

                    result = await test_model_voice(
                        db, sp_id, provider_name, provider_internal,
                        model_record, voice_record,
                    )
                    results.append(result)

                    if result["status"] == "WORKING":
                        print(f"{GREEN}WORKING{RESET} ({result['time_s']}s)")
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
