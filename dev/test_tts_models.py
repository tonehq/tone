"""
TTS Model Evaluation Script — Tests Google Cloud TTS following Pipecat's approach.

Uses google.cloud.texttospeech_v1 with Application Default Credentials (ADC),
matching exactly how Pipecat's GoogleHttpTTSService and GoogleTTSService work.

Supports both HTTP (synthesize) and streaming (streaming_synthesize) modes.

Auth: Uses ADC — run `gcloud auth application-default login` first.

Currently tests: Google Cloud TTS (Chirp 3 HD, Neural2)
To add a new provider: see "Adding a new provider" section below.

Usage:
    python dev/test_tts_models.py                                          # Test all providers
    python dev/test_tts_models.py --provider google                        # One provider
    python dev/test_tts_models.py --provider google --model en-US-Chirp3-HD-Charon
    python dev/test_tts_models.py --provider google --voice en-US-Chirp3-HD-Kore
    python dev/test_tts_models.py --text "Custom text to synthesize"
    python dev/test_tts_models.py --list-voices google                     # List available voices
    python dev/test_tts_models.py --formats                                # Print audio format docs
    python dev/test_tts_models.py --streaming                              # Use streaming mode
    python dev/test_tts_models.py --analyze-streaming                      # Show WS chunking analysis
    python dev/test_tts_models.py --runs 3                                 # Average over 3 runs
"""

import argparse
import asyncio
import io
import json
import math
import os
import struct
import sys
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Coroutine, Optional

from dotenv import load_dotenv

# Suppress gRPC fork warnings (same as Pipecat)
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "false"

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Output directory for audio files
AUDIO_OUTPUT_DIR = Path(__file__).resolve().parent / "tts_audio_output"

# Default test texts — varied lengths for evaluation
TEST_TEXTS = {
    "short": "Hello, how are you today?",
    "medium": (
        "The quick brown fox jumps over the lazy dog. "
        "This is a test of text-to-speech synthesis quality and latency."
    ),
    "long": (
        "Welcome to our voice agent platform. I'm here to help you with any questions "
        "you might have about our services. We offer a wide range of solutions including "
        "customer support automation, appointment scheduling, and interactive voice response "
        "systems. Our platform supports multiple languages and can be customized to match "
        "your brand's voice and tone. How can I assist you today?"
    ),
}


# ── Data structures ─────────────────────────────────────────────


@dataclass
class TTSMetrics:
    """Metrics collected during TTS synthesis."""

    provider: str
    model: str
    voice: str
    text_length: int
    ttfb_ms: float = 0.0  # Time to First Byte
    ttfs_ms: float = 0.0  # Time to First Sound (first non-silent audio)
    total_time_ms: float = 0.0  # Total synthesis time
    audio_duration_ms: float = 0.0  # Duration of generated audio
    total_bytes: int = 0
    chunk_count: int = 0
    sample_rate: int = 0
    channels: int = 1
    encoding: str = ""
    realtime_factor: float = 0.0  # audio_duration / total_time (>1 means faster than realtime)
    error: Optional[str] = None


@dataclass
class AudioChunk:
    """A chunk of audio data with timing info."""

    data: bytes
    timestamp_ms: float  # Time since synthesis start
    chunk_index: int


@dataclass
class TTSResult:
    """Complete result from a TTS synthesis."""

    metrics: TTSMetrics
    chunks: list = field(default_factory=list)
    raw_audio: bytes = b""
    sample_rate: int = 24000
    channels: int = 1


# Type alias for provider test functions
# Signature: (model, voice, text) -> TTSResult
TTSTestFn = Callable[[str, str, str], Coroutine[None, None, TTSResult]]


# ── Audio format utilities ──────────────────────────────────────


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Convert raw PCM (LINEAR16) to WAV format."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def calculate_audio_duration_ms(pcm_data: bytes, sample_rate: int, channels: int = 1, sample_width: int = 2) -> float:
    """Calculate audio duration in ms from PCM data."""
    if not pcm_data:
        return 0.0
    num_samples = len(pcm_data) / (sample_width * channels)
    return (num_samples / sample_rate) * 1000


def detect_first_sound_offset_ms(
    pcm_data: bytes, sample_rate: int, threshold: int = 500, sample_width: int = 2
) -> float:
    """Detect when the first audible sound occurs in PCM data (skip leading silence)."""
    if not pcm_data or len(pcm_data) < sample_width:
        return 0.0

    num_samples = len(pcm_data) // sample_width
    fmt = f"<{num_samples}h"  # little-endian signed 16-bit
    try:
        samples = struct.unpack(fmt, pcm_data[: num_samples * sample_width])
    except struct.error:
        return 0.0

    for i, sample in enumerate(samples):
        if abs(sample) > threshold:
            return (i / sample_rate) * 1000
    return 0.0


def compute_derived_metrics(metrics: TTSMetrics, raw_audio: bytes, sample_rate: int):
    """Fill in audio_duration_ms, ttfs_ms, and realtime_factor from raw PCM data."""
    if not raw_audio:
        return
    metrics.audio_duration_ms = calculate_audio_duration_ms(raw_audio, sample_rate)
    first_sound_offset = detect_first_sound_offset_ms(raw_audio, sample_rate)
    metrics.ttfs_ms = metrics.ttfb_ms + first_sound_offset
    if metrics.total_time_ms > 0:
        metrics.realtime_factor = metrics.audio_duration_ms / metrics.total_time_ms


def analyze_audio_for_streaming(pcm_data: bytes, sample_rate: int, chunk_duration_ms: int = 20) -> dict:
    """Analyze how audio can be chunked for WebSocket streaming."""
    sample_width = 2  # 16-bit PCM
    bytes_per_ms = (sample_rate * sample_width) / 1000
    chunk_size_bytes = int(bytes_per_ms * chunk_duration_ms)
    total_chunks = math.ceil(len(pcm_data) / chunk_size_bytes) if pcm_data else 0
    audio_duration_ms = calculate_audio_duration_ms(pcm_data, sample_rate)

    return {
        "total_audio_bytes": len(pcm_data),
        "audio_duration_ms": round(audio_duration_ms, 1),
        "sample_rate": sample_rate,
        "encoding": "LINEAR16 (signed 16-bit PCM, little-endian)",
        "chunk_duration_ms": chunk_duration_ms,
        "chunk_size_bytes": chunk_size_bytes,
        "total_chunks": total_chunks,
        "bytes_per_second": sample_rate * sample_width,
        "recommended_ws_settings": {
            "chunk_duration_ms": 20,
            "chunk_size_bytes": chunk_size_bytes,
            "buffer_ahead_chunks": 3,
            "format": "raw PCM LINEAR16",
            "note": "Client must know sample_rate and channels to decode. "
            "Send a metadata message first with {sample_rate, channels, encoding}.",
        },
    }


# ── Audio format documentation ──────────────────────────────────


AUDIO_FORMAT_DOCS = {
    "LINEAR16_PCM": {
        "description": "Raw uncompressed PCM audio, 16-bit signed integers, little-endian",
        "codec": "None (uncompressed)",
        "mime_type": "audio/L16",
        "sample_widths": "2 bytes (16-bit)",
        "typical_sample_rates": [8000, 16000, 24000, 44100, 48000],
        "bitrate_at_24khz": "384 kbps (mono)",
        "streaming_suitability": "EXCELLENT — lowest latency, no encode/decode overhead",
        "ws_considerations": "Largest bandwidth; client must reassemble. Best for LAN/local.",
        "used_by": ["Google TTS (streaming)", "Gemini TTS", "OpenAI TTS", "Deepgram TTS"],
    },
    "WAV": {
        "description": "RIFF WAV container wrapping LINEAR16 PCM with a 44-byte header",
        "codec": "PCM (uncompressed) inside WAV container",
        "mime_type": "audio/wav",
        "sample_widths": "2 bytes (16-bit) typically",
        "typical_sample_rates": [8000, 16000, 24000, 44100, 48000],
        "bitrate_at_24khz": "384 kbps + 44 bytes header",
        "streaming_suitability": "GOOD — simple header, then raw PCM follows",
        "ws_considerations": "Send header once, then stream PCM chunks. Easy client-side decoding.",
        "used_by": ["Google HTTP TTS", "AWS Polly"],
    },
    "MP3": {
        "description": "Lossy compressed audio using MPEG Layer 3",
        "codec": "MP3 (MPEG-1 Audio Layer III)",
        "mime_type": "audio/mpeg",
        "typical_bitrates": ["64 kbps", "128 kbps", "192 kbps"],
        "streaming_suitability": "MODERATE — smaller bandwidth but encode/decode latency",
        "ws_considerations": "Frames are self-contained; can stream frame-by-frame. "
        "Client needs MP3 decoder. ~26ms per frame at 128kbps.",
        "used_by": ["ElevenLabs", "OpenAI TTS (non-streaming)"],
    },
    "OPUS": {
        "description": "Modern lossy codec optimized for speech and low-latency streaming",
        "codec": "Opus (RFC 6716)",
        "mime_type": "audio/opus",
        "typical_bitrates": ["16-64 kbps (speech)", "64-128 kbps (music)"],
        "frame_sizes": ["2.5ms", "5ms", "10ms", "20ms", "40ms", "60ms"],
        "streaming_suitability": "EXCELLENT — designed for real-time streaming, very low latency",
        "ws_considerations": "Smallest bandwidth for speech. Native WebRTC codec. "
        "Ideal for WAN/mobile. OGG container not needed for raw streaming.",
        "used_by": ["WebRTC (native)", "Cartesia (via OGG container)"],
    },
    "MULAW": {
        "description": "G.711 μ-law companding, standard telephony codec",
        "codec": "G.711 μ-law (ITU-T G.711)",
        "mime_type": "audio/basic",
        "sample_rate": 8000,
        "bitrate": "64 kbps",
        "streaming_suitability": "GOOD — designed for telephony, very low latency",
        "ws_considerations": "Fixed 8kHz/8-bit. Used by Twilio and PSTN gateways.",
        "used_by": ["Twilio transport", "PSTN gateways"],
    },
}


# ══════════════════════════════════════════════════════════════════
# PROVIDER REGISTRY
#
# Uses google.cloud.texttospeech_v1 — the same SDK Pipecat uses.
# Auth: Application Default Credentials (gcloud auth application-default login)
#
# To add a new provider:
#   1. Add an entry to SERVICE_PROVIDERS with models, default_voice, voices,
#      sample_rate, encoding.
#   2. Write an async test function with signature:
#        async def test_<name>(model, voice, text) -> TTSResult
#   3. Register it in PROVIDER_TEST_FN.
# ══════════════════════════════════════════════════════════════════

SERVICE_PROVIDERS = {
    "google": {
        "models": [
            # Chirp 3 HD voices (streaming supported)
            "en-US-Chirp3-HD-Charon",
            "en-US-Chirp3-HD-Kore",
            "en-US-Chirp3-HD-Puck",
            "en-US-Chirp3-HD-Zephyr",
            # Neural2 voices (HTTP only)
            "en-US-Neural2-A",
            "en-US-Neural2-C",
        ],
        "default_voice": "en-US-Chirp3-HD-Charon",
        "voices": [
            "en-US-Chirp3-HD-Achernar", "en-US-Chirp3-HD-Achird",
            "en-US-Chirp3-HD-Algenib", "en-US-Chirp3-HD-Algieba",
            "en-US-Chirp3-HD-Aoede", "en-US-Chirp3-HD-Autonoe",
            "en-US-Chirp3-HD-Charon", "en-US-Chirp3-HD-Enceladus",
            "en-US-Chirp3-HD-Fenrir", "en-US-Chirp3-HD-Kore",
            "en-US-Chirp3-HD-Leda", "en-US-Chirp3-HD-Orus",
            "en-US-Chirp3-HD-Puck", "en-US-Chirp3-HD-Zephyr",
            "en-US-Neural2-A", "en-US-Neural2-C",
            "en-US-Neural2-D", "en-US-Neural2-E",
            "en-US-Neural2-F", "en-US-Neural2-G",
            "en-US-Neural2-I", "en-US-Neural2-J",
        ],
        "sample_rate": 24000,
        "encoding": "LINEAR16 PCM",
    },
    "gemini": {
        "models": [
            "gemini-2.5-flash-tts",
            "gemini-2.5-pro-tts",
            "gemini-3.1-flash-tts-preview",
        ],
        "default_voice": "Kore",
        "voices": [
            "Achernar", "Achird", "Algenib", "Algieba", "Alnilam",
            "Aoede", "Autonoe", "Callirhoe", "Charon", "Despina",
            "Enceladus", "Erinome", "Fenrir", "Gacrux", "Iapetus",
            "Kore", "Laomedeia", "Leda", "Orus", "Puck",
            "Pulcherrima", "Rasalgethi", "Sadachbia", "Sadaltager",
            "Schedar", "Sulafar", "Umbriel", "Vindemiatrix", "Zephyr",
            "Zubenelgenubi",
        ],
        "sample_rate": 24000,
        "encoding": "LINEAR16 PCM",
    },
}


# ── Google Cloud TTS — HTTP mode (Pipecat's GoogleHttpTTSService approach) ──


def _create_google_client():
    """Create Google TTS client using service account JSON — same auth flow as Pipecat."""
    from google.auth import default
    from google.auth.exceptions import GoogleAuthError
    from google.cloud import texttospeech_v1
    from google.oauth2 import service_account

    creds = None

    # 1. Check for inline service account JSON (GOOGLE_SERVICE_ACCOUNT_JSON) — matches Pipecat's credentials= param
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if credentials_json:
        import json as _json
        creds = service_account.Credentials.from_service_account_info(_json.loads(credentials_json))
    # 2. Check for credentials file path
    elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if os.path.exists(credentials_path):
            creds = service_account.Credentials.from_service_account_file(credentials_path)
    # 3. Fall back to ADC
    if not creds:
        try:
            creds, project_id = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        except GoogleAuthError as e:
            raise ValueError(
                f"No valid Google credentials found.\n"
                f"Set GOOGLE_SERVICE_ACCOUNT_JSON in .env or run: gcloud auth application-default login\n"
                f"Error: {e}"
            )

    if not creds:
        raise ValueError(
            "No valid Google credentials. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"
        )

    return texttospeech_v1.TextToSpeechAsyncClient(credentials=creds)


async def test_google_http(voice_id: str, _voice_unused: str, text: str) -> TTSResult:
    """Test Google Cloud TTS via HTTP API — matches Pipecat's GoogleHttpTTSService.

    Uses texttospeech_v1.synthesize_speech with LINEAR16 encoding.
    Strips the 44-byte WAV header from the response (same as Pipecat).
    """
    from google.cloud import texttospeech_v1

    sample_rate = 24000
    metrics = TTSMetrics(
        provider="google", model=f"{voice_id} (http)", voice=voice_id, text_length=len(text),
        sample_rate=sample_rate, channels=1, encoding="LINEAR16 PCM",
    )

    try:
        client = _create_google_client()

        # Chirp and Journey voices don't support SSML — use plain text (same as Pipecat)
        is_chirp = "chirp" in voice_id.lower()
        is_journey = "journey" in voice_id.lower()

        if is_chirp or is_journey:
            synthesis_input = texttospeech_v1.SynthesisInput(text=text)
        else:
            ssml = f"<speak><voice name='{voice_id}' language='en-US'>{text}</voice></speak>"
            synthesis_input = texttospeech_v1.SynthesisInput(ssml=ssml)

        # Extract language code from voice_id (e.g., "en-US" from "en-US-Chirp3-HD-Charon")
        parts = voice_id.split("-")
        language_code = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "en-US"

        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=language_code, name=voice_id
        )

        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
        )

        request = texttospeech_v1.SynthesizeSpeechRequest(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        start_time = time.monotonic()
        response = await client.synthesize_speech(request=request)
        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Skip the first 44 bytes to remove the WAV header (same as Pipecat)
        audio_content = response.audio_content[44:]

        metrics.ttfb_ms = elapsed_ms
        metrics.total_time_ms = elapsed_ms
        metrics.total_bytes = len(audio_content)
        metrics.chunk_count = 1

        compute_derived_metrics(metrics, audio_content, sample_rate)

        chunks = [AudioChunk(data=audio_content, timestamp_ms=elapsed_ms, chunk_index=0)]
        return TTSResult(metrics=metrics, chunks=chunks, raw_audio=audio_content, sample_rate=sample_rate)

    except Exception as e:
        metrics.error = str(e)
        metrics.total_time_ms = 0
        return TTSResult(metrics=metrics)


# ── Google Cloud TTS — Streaming mode (Pipecat's GoogleTTSService approach) ──


async def test_google_streaming(voice_id: str, _voice_unused: str, text: str) -> TTSResult:
    """Test Google Cloud TTS via streaming API — matches Pipecat's GoogleTTSService.

    Uses texttospeech_v1.streaming_synthesize with the same request_generator
    pattern as Pipecat's _stream_tts method.

    Note: Streaming only works with Chirp 3 HD and Journey voices.
    """
    from google.cloud import texttospeech_v1

    sample_rate = 24000
    mode_label = "streaming"
    metrics = TTSMetrics(
        provider="google", model=f"{voice_id} ({mode_label})", voice=voice_id, text_length=len(text),
        sample_rate=sample_rate, channels=1, encoding="LINEAR16 PCM",
    )

    # Streaming only works with Chirp 3 HD and Journey voices
    is_chirp = "chirp" in voice_id.lower()
    is_journey = "journey" in voice_id.lower()
    if not is_chirp and not is_journey:
        metrics.error = f"Streaming not supported for {voice_id} — only Chirp 3 HD and Journey voices"
        return TTSResult(metrics=metrics)

    try:
        client = _create_google_client()

        # Extract language code from voice_id
        parts = voice_id.split("-")
        language_code = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "en-US"

        # Build streaming config — same as Pipecat's GoogleTTSService
        voice_params = texttospeech_v1.VoiceSelectionParams(
            language_code=language_code, name=voice_id
        )
        streaming_config = texttospeech_v1.StreamingSynthesizeConfig(
            voice=voice_params,
            streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
                audio_encoding=texttospeech_v1.AudioEncoding.PCM,
                sample_rate_hertz=sample_rate,
            ),
        )

        config_request = texttospeech_v1.StreamingSynthesizeRequest(
            streaming_config=streaming_config
        )

        # Request generator — same pattern as Pipecat's _stream_tts
        async def request_generator():
            yield config_request
            yield texttospeech_v1.StreamingSynthesizeRequest(
                input=texttospeech_v1.StreamingSynthesisInput(text=text)
            )

        start_time = time.monotonic()
        first_byte_received = False
        chunks = []
        all_audio = bytearray()
        chunk_idx = 0

        streaming_responses = await client.streaming_synthesize(request_generator())

        async for response in streaming_responses:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            audio_bytes = response.audio_content

            if not audio_bytes:
                continue

            if not first_byte_received:
                first_byte_received = True
                metrics.ttfb_ms = elapsed_ms

            all_audio.extend(audio_bytes)
            chunks.append(AudioChunk(data=audio_bytes, timestamp_ms=elapsed_ms, chunk_index=chunk_idx))
            chunk_idx += 1

        metrics.total_time_ms = (time.monotonic() - start_time) * 1000
        metrics.total_bytes = len(all_audio)
        metrics.chunk_count = chunk_idx

        if all_audio:
            compute_derived_metrics(metrics, bytes(all_audio), sample_rate)
        else:
            metrics.error = "No audio data received in stream"

    except Exception as e:
        metrics.error = str(e)
        metrics.total_time_ms = (time.monotonic() - start_time) * 1000

    return TTSResult(metrics=metrics, chunks=chunks, raw_audio=bytes(all_audio), sample_rate=sample_rate)


# ── Gemini TTS — streaming (Pipecat's GeminiTTSService approach) ──


async def test_gemini_tts(model: str, voice: str, text: str) -> TTSResult:
    """Test Gemini TTS via streaming API — matches Pipecat's GeminiTTSService.

    Uses texttospeech_v1.streaming_synthesize with model_name in VoiceSelectionParams.
    Same SDK (google.cloud.texttospeech_v1) and same ADC auth as Google Cloud TTS.

    Key difference from GoogleTTSService: passes model_name (e.g., "gemini-2.5-flash-tts")
    and uses short voice names (e.g., "Kore" instead of "en-US-Chirp3-HD-Kore").
    """
    from google.cloud import texttospeech_v1

    sample_rate = 24000
    metrics = TTSMetrics(
        provider="gemini", model=f"{model} ({voice})", voice=voice, text_length=len(text),
        sample_rate=sample_rate, channels=1, encoding="LINEAR16 PCM",
    )

    chunks = []
    all_audio = bytearray()
    start_time = time.monotonic()

    try:
        client = _create_google_client()

        # Build voice selection with model_name — same as Pipecat's GeminiTTSService
        voice_params = texttospeech_v1.VoiceSelectionParams(
            language_code="en-US",
            name=voice,
            model_name=model,
        )

        # Streaming config with PCM encoding — same as Pipecat
        streaming_config = texttospeech_v1.StreamingSynthesizeConfig(
            voice=voice_params,
            streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
                audio_encoding=texttospeech_v1.AudioEncoding.PCM,
                sample_rate_hertz=sample_rate,
            ),
        )

        config_request = texttospeech_v1.StreamingSynthesizeRequest(
            streaming_config=streaming_config
        )

        # Request generator — same pattern as Pipecat's _stream_tts
        async def request_generator():
            yield config_request
            yield texttospeech_v1.StreamingSynthesizeRequest(
                input=texttospeech_v1.StreamingSynthesisInput(text=text)
            )

        first_byte_received = False
        chunk_idx = 0

        streaming_responses = await client.streaming_synthesize(request_generator())

        async for response in streaming_responses:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            audio_bytes = response.audio_content

            if not audio_bytes:
                continue

            if not first_byte_received:
                first_byte_received = True
                metrics.ttfb_ms = elapsed_ms

            all_audio.extend(audio_bytes)
            chunks.append(AudioChunk(data=audio_bytes, timestamp_ms=elapsed_ms, chunk_index=chunk_idx))
            chunk_idx += 1

        metrics.total_time_ms = (time.monotonic() - start_time) * 1000
        metrics.total_bytes = len(all_audio)
        metrics.chunk_count = chunk_idx

        if all_audio:
            compute_derived_metrics(metrics, bytes(all_audio), sample_rate)
        else:
            metrics.error = "No audio data received in stream"

    except Exception as e:
        metrics.error = str(e)
        metrics.total_time_ms = (time.monotonic() - start_time) * 1000

    return TTSResult(metrics=metrics, chunks=chunks, raw_audio=bytes(all_audio), sample_rate=sample_rate)


# ── Provider → test function mapping ────────────────────────────
PROVIDER_TEST_FN: dict[str, TTSTestFn] = {
    "google": test_google_http,
    "google_streaming": test_google_streaming,
    "gemini": test_gemini_tts,
}


# ── Output helpers ──────────────────────────────────────────────


def save_audio_files(result: TTSResult, output_dir: Path, prefix: str):
    """Save audio in multiple formats for validation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if not result.raw_audio:
        return {}

    saved = {}

    pcm_path = output_dir / f"{prefix}.pcm"
    pcm_path.write_bytes(result.raw_audio)
    saved["pcm"] = str(pcm_path)

    wav_data = pcm_to_wav(result.raw_audio, result.sample_rate, result.channels)
    wav_path = output_dir / f"{prefix}.wav"
    wav_path.write_bytes(wav_data)
    saved["wav"] = str(wav_path)

    return saved


def print_metrics(metrics: TTSMetrics):
    """Print metrics in a readable format."""
    status = "FAIL" if metrics.error else "PASS"
    print(f"\n  [{status}] {metrics.provider}/{metrics.model} — voice: {metrics.voice}")

    if metrics.error:
        print(f"    Error: {metrics.error[:120]}")
        return

    print(f"    Text length:     {metrics.text_length} chars")
    print(f"    TTFB:            {metrics.ttfb_ms:.0f} ms")
    print(f"    TTFS:            {metrics.ttfs_ms:.0f} ms")
    print(f"    Total time:      {metrics.total_time_ms:.0f} ms")
    print(f"    Audio duration:  {metrics.audio_duration_ms:.0f} ms")
    print(f"    Realtime factor: {metrics.realtime_factor:.2f}x")
    print(f"    Audio size:      {metrics.total_bytes:,} bytes")
    print(f"    Chunks:          {metrics.chunk_count}")
    print(f"    Sample rate:     {metrics.sample_rate} Hz")
    print(f"    Encoding:        {metrics.encoding}")


def print_streaming_analysis(result: TTSResult):
    """Print WebSocket streaming analysis."""
    if not result.raw_audio:
        return
    analysis = analyze_audio_for_streaming(result.raw_audio, result.sample_rate)
    print(f"\n  WebSocket Streaming Analysis:")
    print(f"    Audio bytes:     {analysis['total_audio_bytes']:,}")
    print(f"    Audio duration:  {analysis['audio_duration_ms']:.0f} ms")
    print(f"    Chunk size:      {analysis['chunk_size_bytes']} bytes ({analysis['chunk_duration_ms']}ms)")
    print(f"    Total chunks:    {analysis['total_chunks']}")
    print(f"    Bytes/sec:       {analysis['bytes_per_second']:,}")
    print(f"    Recommended:     {analysis['recommended_ws_settings']['format']}")


def print_format_docs():
    """Print audio format documentation."""
    print("\n" + "=" * 70)
    print("AUDIO FORMAT REFERENCE")
    print("=" * 70)
    for fmt_name, info in AUDIO_FORMAT_DOCS.items():
        print(f"\n--- {fmt_name} ---")
        for key, val in info.items():
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            print(f"  {key:25s}: {val}")

    print("\n" + "=" * 70)
    print("RECOMMENDATION FOR LOW-LATENCY STREAMING:")
    print("=" * 70)
    print("  1. LINEAR16 PCM (raw) — Lowest latency, simplest decode, highest bandwidth")
    print("     Best for: Server-to-server, LAN, WebSocket with good bandwidth")
    print("  2. Opus — Best compression for speech, very low latency, smallest bandwidth")
    print("     Best for: WebRTC, mobile clients, WAN connections")
    print("  3. WAV — PCM with header, easy client decoding, same bandwidth as raw PCM")
    print("     Best for: Simple clients that need format metadata in-band")
    print("  4. MP3 — Wide compatibility but higher encode/decode latency")
    print("     Best for: Pre-generated audio, non-realtime playback")


# ── Main ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="TTS Model Evaluation — test Google Cloud TTS (Pipecat approach)"
    )
    parser.add_argument("--provider", help="Test only this provider (e.g., google)")
    parser.add_argument("--model", help="Test only this voice/model (e.g., en-US-Chirp3-HD-Charon)")
    parser.add_argument("--voice", help="Alias for --model (voice ID to test)")
    parser.add_argument("--text", help="Custom text to synthesize")
    parser.add_argument(
        "--text-length", choices=["short", "medium", "long"], default="medium",
        help="Predefined text length (default: medium)",
    )
    parser.add_argument("--list-voices", metavar="PROVIDER", help="List available voices for a provider")
    parser.add_argument("--formats", action="store_true", help="Print audio format documentation")
    parser.add_argument("--save-audio", action="store_true", default=True, help="Save audio output files")
    parser.add_argument("--no-save-audio", action="store_false", dest="save_audio")
    parser.add_argument("--streaming", action="store_true", help="Use streaming mode (Chirp 3 HD / Journey only)")
    parser.add_argument("--analyze-streaming", action="store_true", help="Print WebSocket streaming analysis")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per model for averaging (default: 1)")
    args = parser.parse_args()

    if args.formats:
        print_format_docs()
        return

    if args.list_voices:
        provider = args.list_voices.lower()
        if provider not in SERVICE_PROVIDERS:
            print(f"Unknown provider: {provider}")
            print(f"Available: {', '.join(SERVICE_PROVIDERS.keys())}")
            return
        cfg = SERVICE_PROVIDERS[provider]
        print(f"\nVoices for {provider} (google.cloud.texttospeech_v1):")
        for v in cfg["voices"]:
            marker = " (default)" if v == cfg["default_voice"] else ""
            if provider == "gemini":
                print(f"  - {v}{marker}")
            else:
                streaming = " [streaming]" if "chirp" in v.lower() or "journey" in v.lower() else " [http only]"
                print(f"  - {v}{marker}{streaming}")
        if provider == "gemini":
            print(f"\nModels: {', '.join(cfg['models'])}")
        return

    # --voice is an alias for --model in Google Cloud TTS (voice_id = model)
    model_override = args.model or args.voice
    text = args.text or TEST_TEXTS[args.text_length]
    all_results = []

    print("=" * 70)
    print("TTS MODEL EVALUATION (Pipecat google.cloud.texttospeech_v1 approach)")
    print("=" * 70)
    print(f"Text ({len(text)} chars): \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
    print(f"Auth: Application Default Credentials (gcloud auth application-default login)")
    print(f"Mode: {'Streaming (streaming_synthesize)' if args.streaming else 'HTTP (synthesize_speech)'}")

    for provider_name, cfg in SERVICE_PROVIDERS.items():
        if args.provider and provider_name != args.provider:
            continue

        # Gemini: iterate over models with a voice name
        # Google: iterate over voice IDs (voice_id is the model)
        is_gemini = provider_name == "gemini"

        if is_gemini:
            models = [model_override] if model_override else cfg["models"]
            voice = args.voice or cfg["default_voice"]
            test_items = [(m, voice) for m in models]
            print(f"\n{'─'*70}")
            print(f"Provider: {provider_name} | Voice: {voice} | Models: {len(models)}")
            print(f"{'─'*70}")
        else:
            voice_ids = [model_override] if model_override else cfg["models"]
            test_items = [(vid, vid) for vid in voice_ids]
            print(f"\n{'─'*70}")
            print(f"Provider: {provider_name} | Voices to test: {len(voice_ids)}")
            print(f"{'─'*70}")

        for model_id, voice_id in test_items:
            for run in range(args.runs):
                run_label = f" (run {run + 1}/{args.runs})" if args.runs > 1 else ""

                # Pick streaming variant if available and requested
                if args.streaming:
                    test_fn = PROVIDER_TEST_FN.get(f"{provider_name}_streaming")
                    if not test_fn:
                        test_fn = PROVIDER_TEST_FN.get(provider_name)
                else:
                    test_fn = PROVIDER_TEST_FN.get(provider_name)

                if not test_fn:
                    print(f"  SKIP {model_id} — no test function registered")
                    continue

                label = f"{model_id}/{voice_id}" if is_gemini else voice_id
                sys.stdout.write(f"  Testing {label}{run_label} ...")
                sys.stdout.flush()

                result = asyncio.run(test_fn(model_id, voice_id, text))
                print_metrics(result.metrics)

                if args.analyze_streaming and not result.metrics.error:
                    print_streaming_analysis(result)

                if args.save_audio and result.raw_audio:
                    prefix = f"{provider_name}_{model_id}_{voice_id}".replace("/", "_").replace(" ", "_")
                    if args.runs > 1:
                        prefix += f"_run{run + 1}"
                    saved = save_audio_files(result, AUDIO_OUTPUT_DIR, prefix)
                    if saved:
                        print(f"    Audio saved: {', '.join(saved.keys())}")
                        for fmt, path in saved.items():
                            print(f"      {fmt}: {path}")

                if result.chunks and len(result.chunks) > 1:
                    intervals = [
                        result.chunks[i].timestamp_ms - result.chunks[i - 1].timestamp_ms
                        for i in range(1, len(result.chunks))
                    ]
                    avg_interval = sum(intervals) / len(intervals)
                    print(f"    Chunk intervals: avg={avg_interval:.0f}ms, "
                          f"min={min(intervals):.0f}ms, max={max(intervals):.0f}ms")

                all_results.append(result)

    # ── Summary ─────────────────────────────────────────────────
    if not all_results:
        print("\nNo tests were run. Check credentials (gcloud auth application-default login)")
        return

    passed = [r for r in all_results if not r.metrics.error]
    failed = [r for r in all_results if r.metrics.error]

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Total tests: {len(all_results)}")
    print(f"  Passed:      {len(passed)}")
    print(f"  Failed:      {len(failed)}")

    if passed:
        print(f"\n  {'Provider':<15} {'Model':<40} {'TTFB':>8} {'TTFS':>8} {'Total':>8} {'RT Factor':>10}")
        print(f"  {'─'*15} {'─'*40} {'─'*8} {'─'*8} {'─'*8} {'─'*10}")
        for r in passed:
            m = r.metrics
            print(
                f"  {m.provider:<15} {m.model:<40} {m.ttfb_ms:>7.0f}ms {m.ttfs_ms:>7.0f}ms "
                f"{m.total_time_ms:>7.0f}ms {m.realtime_factor:>9.2f}x"
            )

    if failed:
        print("\n  Failed:")
        for r in failed:
            m = r.metrics
            print(f"    [{m.provider}] {m.model}: {m.error[:100]}")

    # Save results JSON
    output_path = Path(__file__).resolve().parent / "tts_test_results.json"
    results_data = {
        "test_text": text,
        "test_text_length": len(text),
        "total": len(all_results),
        "passed": len(passed),
        "failed": len(failed),
        "auth_method": "Application Default Credentials (google.cloud.texttospeech_v1)",
        "results": [
            {
                **{k: v for k, v in asdict(r.metrics).items()},
                "streaming_analysis": analyze_audio_for_streaming(r.raw_audio, r.sample_rate)
                if r.raw_audio else None,
            }
            for r in all_results
        ],
        "audio_format_reference": AUDIO_FORMAT_DOCS,
    }
    with open(output_path, "w") as f:
        json.dump(results_data, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
