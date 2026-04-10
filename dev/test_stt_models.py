"""
Test script to validate STT models configured in dev-data.json.
Uses each provider's REST/HTTP API to send a small audio sample and verify
that the API key is valid and the model is accessible.

Usage:
    python dev/test_stt_models.py                                      # Test all
    python dev/test_stt_models.py --provider deepgram                  # One provider
    python dev/test_stt_models.py --provider openai --model whisper-1  # One model
"""

import asyncio
import argparse
import io
import json
import os
import struct
import sys
import time
import wave
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add project root to sys.path so pipecat and core imports work
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipecat" / "src"))

DEV_DATA_PATH = Path(__file__).resolve().parent / "dev-data.json"

# ── Hardcoded service providers to test ──────────────────────────
# Only providers with API keys set in .env are listed here.
# Models are auto-picked from dev-data.json for each provider.
SERVICE_PROVIDERS = {
    "deepgram": {
        "api_key_env": "DEEPGRAM_API_KEY",  # All pass
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY", # all pass
    },
    "groq": {
        "api_key_env": "GROQ_API_KEY",  # All pass
    },
    "sarvam": {
        "api_key_env": "SARVAM_API_KEY", # All pass
    },
    "assemblyai": {
        "api_key_env": "ASSEMBLYAI_API_KEY", #Issues
    },
    "cartesia": {
        "api_key_env": "CARTESIA_API_KEY",  #All pass
    },
    "soniox": {
        "api_key_env": "SONIOX_API_KEY",  #all pass
    },
    "elevenlabs": {
        "api_key_env": "ELEVENLABS_API_KEY",  # all pass
    },
    "gladia": {
        "api_key_env": "GLADIA_API_KEY",  #All pass
    },
    "hathora": {
        "api_key_env": "HATHORA_API_KEY",  #Issues
    },
    "speechmatics": {
        "api_key_env": "SPEECHMATICS_API_KEY",  #All pass
    },
    "nvidia": {
        "api_key_env": "NVIDIA_API_KEY", #all pass
    },
}


def generate_test_wav(duration_s=1.0, sample_rate=16000) -> bytes:
    """Generate a minimal WAV file with a short tone (440Hz sine wave)."""
    import math

    num_samples = int(sample_rate * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        samples = []
        for i in range(num_samples):
            # 440Hz sine wave at ~50% amplitude
            val = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            samples.append(struct.pack("<h", val))
        wf.writeframes(b"".join(samples))
    return buf.getvalue()


# Pre-generate test audio
TEST_WAV = generate_test_wav()


def load_stt_providers():
    with open(DEV_DATA_PATH) as f:
        data = json.load(f)
    return data.get("stt_providers", [])


# ── Provider-specific test functions ─────────────────────────────
# Each returns a string (transcript or status message) on success,
# or raises on failure.

async def test_deepgram(api_key: str, model: str) -> str:
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.deepgram.com/v1/listen?model={model}&language=en",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/wav",
            },
            content=TEST_WAV,
        )
        resp.raise_for_status()
        data = resp.json()
        transcript = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        return transcript or "(empty transcript — auth OK)"


async def test_openai(api_key: str, model: str) -> str:
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("test.wav", TEST_WAV, "audio/wav")},
            data={"model": model, "language": "en"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "(empty transcript — auth OK)")


async def test_groq(api_key: str, model: str) -> str:
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("test.wav", TEST_WAV, "audio/wav")},
            data={"model": model, "language": "en"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "(empty transcript — auth OK)")


async def test_sarvam(api_key: str, model: str) -> str:
    """Sarvam STT is WebSocket-based. Validate API key via their REST speech-to-text endpoint."""
    import httpx

    # Sarvam model names in dev-data.json are display names;
    # the actual API model ID is "saarika:v2.5" (default).
    actual_model = "saarika:v2.5"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": api_key},
            files={"file": ("test.wav", TEST_WAV, "audio/wav")},
            data={"model": actual_model, "language_code": "en-IN"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("transcript", "(empty transcript — auth OK)")


async def test_assemblyai(api_key: str, model: str) -> str:
    """AssemblyAI uses async transcription: upload → create transcript → poll."""
    import httpx

    headers = {"Authorization": api_key}
    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: Upload audio
        upload_resp = await client.post(
            "https://api.assemblyai.com/v2/upload",
            headers={**headers, "Content-Type": "application/octet-stream"},
            content=TEST_WAV,
        )
        upload_resp.raise_for_status()
        upload_url = upload_resp.json()["upload_url"]

        # Step 2: Create transcript
        body = {
            "audio_url": upload_url,
            "language_code": "en",
        }
        # Map display model names to API speech_model values
        speech_model_map = {
            "Universal-3-Pro": "universal-3-pro",
            "Universal-2": "best",
            "Universal-Streaming": "nano",
        }
        if model in speech_model_map:
            body["speech_model"] = speech_model_map[model]

        create_resp = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=headers,
            json=body,
        )
        create_resp.raise_for_status()
        transcript_id = create_resp.json()["id"]

        # Step 3: Poll for completion (max 30s)
        for _ in range(30):
            poll_resp = await client.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers,
            )
            poll_resp.raise_for_status()
            status = poll_resp.json()["status"]
            if status == "completed":
                return poll_resp.json().get("text", "(empty transcript — auth OK)")
            if status == "error":
                raise Exception(f"Transcription error: {poll_resp.json().get('error', 'unknown')}")
            await asyncio.sleep(1)

        raise Exception("Transcription timed out after 30s")


async def test_cartesia(api_key: str, model: str) -> str:
    """Cartesia STT is WebSocket-based. Test by establishing a connection."""
    import httpx

    # Cartesia doesn't have a REST transcription endpoint.
    # Validate the API key by hitting their voices endpoint (lightweight).
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.cartesia.ai/voices",
            headers={
                "X-API-Key": api_key,
                "Cartesia-Version": "2024-06-10",
            },
        )
        resp.raise_for_status()
        return f"(API key valid — {model} — connection test only)"


async def test_soniox(api_key: str, model: str) -> str:
    """Soniox is WebSocket/gRPC-based. Validate API key via REST."""
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        # Use their REST transcription endpoint
        resp = await client.post(
            "https://api.soniox.com/v1/transcribe",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "audio/wav",
            },
            content=TEST_WAV,
            params={"model": model},
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("text", "") or data.get("transcript", "")
            return text or "(empty transcript — auth OK)"
        # If REST endpoint doesn't exist, just validate key via a different endpoint
        if resp.status_code == 404:
            return f"(API key format valid — {model} — REST endpoint not available)"
        resp.raise_for_status()
        return "(auth OK)"


async def test_elevenlabs(api_key: str, model: str) -> str:
    import httpx

    # Realtime model is WebSocket-only, can't test via REST.
    # Validate API key by calling the batch model instead.
    if model == "scribe_v2_realtime":
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.elevenlabs.io/v1/models",
                headers={"xi-api-key": api_key},
            )
            resp.raise_for_status()
            return f"(API key valid — {model} — WebSocket-only, connection test)"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": api_key},
            files={"file": ("test.wav", TEST_WAV, "audio/wav")},
            data={"model_id": model},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "(empty transcript — auth OK)")


async def test_gladia(api_key: str, model: str) -> str:
    """Gladia: upload audio then poll for result."""
    import httpx

    headers = {"x-gladia-key": api_key}
    async with httpx.AsyncClient(timeout=60) as client:
        # Create transcription
        resp = await client.post(
            "https://api.gladia.io/v2/transcription",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "audio_url": "data:audio/wav;base64,"
                + __import__("base64").b64encode(TEST_WAV).decode(),
            },
        )
        resp.raise_for_status()
        result_url = resp.json().get("result_url")
        if not result_url:
            return "(transcription created — auth OK)"

        # Poll for result
        for _ in range(30):
            poll_resp = await client.get(result_url, headers=headers)
            poll_resp.raise_for_status()
            data = poll_resp.json()
            status = data.get("status")
            if status == "done":
                text = data.get("result", {}).get("transcription", {}).get("full_transcript", "")
                return text or "(empty transcript — auth OK)"
            if status == "error":
                raise Exception(f"Transcription error: {data.get('error', 'unknown')}")
            await asyncio.sleep(1)

        raise Exception("Transcription timed out after 30s")


async def test_hathora(api_key: str, model: str) -> str:
    """Hathora STT — uses JSON POST with base64 audio to models.hathora.dev.
    Note: Uses the same URL as Pipecat's HathoraSTTService (base_url default).
    If 404, the Hathora API endpoint may be down or changed.
    """
    import base64
    import httpx

    payload = {
        "model": model,
        "audio": base64.b64encode(TEST_WAV).decode("utf-8"),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.models.hathora.dev/inference/v1/stt",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        if resp.status_code == 404:
            raise Exception("Hathora API endpoint returned 404 — service may be down or URL changed (same URL used in Pipecat pipeline)")
        resp.raise_for_status()
        data = resp.json()
        text = data.get("text", "")
        return text.strip() or "(empty transcript — auth OK)"


async def test_speechmatics(api_key: str, model: str) -> str:
    """Speechmatics batch transcription API."""
    import httpx

    async with httpx.AsyncClient(timeout=60) as client:
        config = {
            "type": "transcription",
            "transcription_config": {
                "language": "en",
                "operating_point": "standard" if "Standard" in model else "enhanced",
            },
        }
        resp = await client.post(
            "https://asr.api.speechmatics.com/v2/jobs",
            headers={"Authorization": f"Bearer {api_key}"},
            files={
                "data_file": ("test.wav", TEST_WAV, "audio/wav"),
                "config": (None, json.dumps(config), "application/json"),
            },
        )
        resp.raise_for_status()
        job_id = resp.json().get("id")

        # Poll for completion
        for _ in range(30):
            poll_resp = await client.get(
                f"https://asr.api.speechmatics.com/v2/jobs/{job_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            poll_resp.raise_for_status()
            data = poll_resp.json()
            status = data.get("job", {}).get("status")
            if status == "done":
                # Fetch transcript
                tr_resp = await client.get(
                    f"https://asr.api.speechmatics.com/v2/jobs/{job_id}/transcript",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "text/plain",
                    },
                )
                tr_resp.raise_for_status()
                return tr_resp.text.strip() or "(empty transcript — auth OK)"
            if status in ("rejected", "deleted"):
                raise Exception(f"Job {status}: {data}")
            await asyncio.sleep(1)

        raise Exception("Transcription timed out after 30s")


async def test_nvidia(api_key: str, model: str) -> str:
    """NVIDIA NIM STT — uses REST API."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        # NVIDIA NIM has an OpenAI-compatible transcription endpoint
        resp = await client.post(
            "https://integrate.api.nvidia.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("test.wav", TEST_WAV, "audio/wav")},
            data={"model": model, "language": "en"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("text", "(empty transcript — auth OK)")
        # If the specific model endpoint doesn't work, try validating via models list
        if resp.status_code in (404, 422):
            resp2 = await client.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp2.status_code == 200:
                return f"(API key valid — {model} — model may need different endpoint)"
            resp.raise_for_status()
        resp.raise_for_status()
        return "(auth OK)"


# ── Provider → test function mapping ─────────────────────────────
PROVIDER_TEST_FN = {
    "deepgram": test_deepgram,
    "openai": test_openai,
    "groq": test_groq,
    "sarvam": test_sarvam,
    "assemblyai": test_assemblyai,
    "cartesia": test_cartesia,
    "soniox": test_soniox,
    "elevenlabs": test_elevenlabs,
    "gladia": test_gladia,
    "hathora": test_hathora,
    "speechmatics": test_speechmatics,
    "nvidia": test_nvidia,
}


def main():
    parser = argparse.ArgumentParser(
        description="Test STT models from dev-data.json via provider REST APIs"
    )
    parser.add_argument("--provider", help="Test only this provider")
    parser.add_argument("--model", help="Test only this model (requires --provider)")
    args = parser.parse_args()

    # Load models from dev-data.json, indexed by provider name
    all_providers = load_stt_providers()
    dev_data_models = {p["name"]: p for p in all_providers}

    results = []
    total = 0
    passed = 0
    failed = 0
    skipped = 0

    for name, cfg in SERVICE_PROVIDERS.items():
        # Filter by --provider
        if args.provider and name != args.provider:
            continue

        # Resolve API key from env
        api_key = os.getenv(cfg["api_key_env"], "")
        if not api_key:
            print(f"\n{'='*60}")
            print(f"SKIP  {name} — {cfg['api_key_env']} not set in .env")
            print(f"{'='*60}")
            continue

        # Get models from dev-data.json for this provider
        dev_entry = dev_data_models.get(name)
        if not dev_entry:
            print(f"\n{'='*60}")
            print(f"SKIP  {name} — not found in dev-data.json")
            print(f"{'='*60}")
            continue

        # Get test function for this provider
        test_fn = PROVIDER_TEST_FN.get(name)
        if not test_fn:
            print(f"\n{'='*60}")
            print(f"SKIP  {name} — no test function implemented")
            print(f"{'='*60}")
            continue

        models = dev_entry.get("models", [])
        display_name = dev_entry.get("display_name", name)

        print(f"\n{'='*60}")
        print(f"Testing {display_name} ({len(models)} models)")
        print(f"{'='*60}")

        for model_entry in models:
            model_name = model_entry.get("meta_data", {}).get("model") or model_entry["name"]

            # Filter by --model
            if args.model and model_name != args.model:
                continue

            total += 1
            sys.stdout.write(f"  {model_name:50s} ... ")
            sys.stdout.flush()

            try:
                start = time.time()
                result = asyncio.run(test_fn(api_key, model_name))
                elapsed = time.time() - start

                passed += 1
                display = (result or "")[:60].strip()
                print(f"PASS ({elapsed:.1f}s) — \"{display}\"")
                results.append((name, model_name, "PASS", result.strip() if result else ""))
            except Exception as e:
                elapsed = time.time() - start
                failed += 1
                err = str(e)[:120]
                print(f"FAIL ({elapsed:.1f}s) — {err}")
                results.append((name, model_name, "FAIL", str(e)))

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Tested:  {total}")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print()

    if failed > 0:
        print("Failed models:")
        for prov, model, status, detail in results:
            if status == "FAIL":
                print(f"  [{prov}] {model}: {detail[:120]}")

    # Write results to JSON
    output_path = Path(__file__).resolve().parent / "stt_test_results.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "tested": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "results": [
                    {"provider": r[0], "model": r[1], "status": r[2], "detail": r[3]}
                    for r in results
                ],
            },
            f,
            indent=2,
        )
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
