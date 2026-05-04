"""
Simple script to test Google STT (Speech-to-Text) using Gemini models.

Google doesn't have dedicated STT models via the Gemini API.
Instead, Gemini's multimodal models handle audio transcription.

Usage:
    # Test all models with a WAV file
    python dev/test_google_stt.py --audio dev/tts_audio_output/gemini_gemini-2.5-flash-preview-tts_Kore.wav

    # Test a specific model
    python dev/test_google_stt.py --audio dev/tts_audio_output/gemini_gemini-2.5-flash-preview-tts_Kore.wav --model gemini-2.5-flash

    # Generate a test audio file first (requires TTS script), then test
    python dev/test_google_stt.py --generate
"""

import argparse
import json
import os
import sys
import time

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Installing google-genai...")
    os.system(f"{sys.executable} -m pip install google-genai")
    from google import genai
    from google.genai import types

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

CREDENTIALS_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if not CREDENTIALS_JSON:
    print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not found in .env")
    print("  This should be the full service account JSON string.")
    sys.exit(1)

# Authenticate using service account credentials — same as Pipecat's GoogleSTTService
from google.oauth2 import service_account as sa
creds = sa.Credentials.from_service_account_info(json.loads(CREDENTIALS_JSON))
client = genai.Client(credentials=creds)

# Models that support audio input for transcription
STT_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

TRANSCRIPTION_PROMPT = "Transcribe this audio exactly as spoken. Return only the transcription text, nothing else."

# Known reference text from the TTS test
REFERENCE_TEXT = "The quick brown fox jumps over the lazy dog. This is a test of text-to-speech synthesis quality and naturalness."


def generate_test_audio(output_path: str) -> str:
    """Generate a test WAV file using Gemini TTS."""
    print("Generating test audio using gemini-2.5-flash-preview-tts...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=REFERENCE_TEXT,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                    )
                ),
            ),
        )
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # Write as WAV
        import struct
        import wave

        pcm_path = output_path.replace(".wav", ".pcm")
        with open(pcm_path, "wb") as f:
            f.write(audio_data)

        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_data)

        print(f"  Audio saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"  ERROR generating audio: {e}")
        sys.exit(1)


def word_accuracy(reference: str, transcription: str) -> float:
    """Simple word-level accuracy between reference and transcription."""
    ref_words = set(reference.lower().split())
    trans_words = set(transcription.lower().split())
    if not ref_words:
        return 0.0
    matching = ref_words.intersection(trans_words)
    return len(matching) / len(ref_words) * 100


def test_stt(audio_path: str, models: list[str], reference: str | None = None):
    """Test STT across multiple models."""
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    mime_type = "audio/wav" if audio_path.endswith(".wav") else "audio/pcm"
    audio_size_kb = len(audio_data) / 1024

    print(f"Audio file: {audio_path}")
    print(f"Audio size: {audio_size_kb:.1f} KB")
    if reference:
        print(f"Reference:  \"{reference[:80]}...\"" if len(reference) > 80 else f"Reference:  \"{reference}\"")
    print(f"\nTesting {len(models)} models...\n")
    print("=" * 70)

    results = []

    for model_name in models:
        print(f"\nModel: {model_name}")
        print("-" * 50)
        try:
            start = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                    TRANSCRIPTION_PROMPT,
                ],
            )
            elapsed = time.time() - start

            transcription = response.text.strip()
            print(f"  Transcription: {transcription[:100]}{'...' if len(transcription) > 100 else ''}")
            print(f"  Latency:       {elapsed:.2f}s")

            result = {
                "model": model_name,
                "status": "OK",
                "transcription": transcription,
                "latency_s": round(elapsed, 2),
            }

            if reference:
                accuracy = word_accuracy(reference, transcription)
                print(f"  Word accuracy: {accuracy:.1f}%")
                result["word_accuracy"] = round(accuracy, 1)

            results.append(result)
        except Exception as e:
            error_msg = str(e)[:200]
            print(f"  ERROR: {error_msg}")
            results.append({"model": model_name, "status": "FAILED", "error": error_msg})

    # Summary
    print("\n" + "=" * 70)
    print("\nSummary:")
    print(f"  {'Model':<35s} {'Status':<8s} {'Latency':<10s} {'Accuracy':<10s}")
    print(f"  {'─' * 35} {'─' * 8} {'─' * 10} {'─' * 10}")

    passed = 0
    for r in results:
        if r["status"] == "OK":
            passed += 1
            accuracy_str = f"{r.get('word_accuracy', 'N/A')}%" if "word_accuracy" in r else "N/A"
            print(f"  {r['model']:<35s} {'PASS':<8s} {r['latency_s']}s{'':<5s} {accuracy_str}")
        else:
            print(f"  {r['model']:<35s} {'FAIL':<8s} {'—':<10s} {'—'}")

    print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {len(results) - passed}")

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "google_stt_test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Test Google STT using Gemini multimodal models")
    parser.add_argument("--audio", type=str, help="Path to WAV/PCM audio file to transcribe")
    parser.add_argument("--model", type=str, help="Test a specific model only")
    parser.add_argument("--generate", action="store_true", help="Generate test audio using Gemini TTS first")
    parser.add_argument("--reference", type=str, default=None, help="Reference text for accuracy comparison")
    args = parser.parse_args()

    # Determine audio file
    audio_path = args.audio
    output_dir = os.path.join(os.path.dirname(__file__), "tts_audio_output")

    if args.generate or not audio_path:
        # Check for existing TTS output first
        existing_wavs = [
            os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".wav")
        ] if os.path.isdir(output_dir) else []

        if existing_wavs and not args.generate:
            audio_path = existing_wavs[0]
            print(f"Using existing audio: {audio_path}\n")
        elif args.generate:
            os.makedirs(output_dir, exist_ok=True)
            audio_path = os.path.join(output_dir, "stt_test_audio.wav")
            audio_path = generate_test_audio(audio_path)
            print()
        else:
            print("ERROR: No audio file provided and no existing WAV files found.")
            print("  Use --audio <path> to provide a WAV file, or --generate to create one.")
            sys.exit(1)

    if not os.path.exists(audio_path):
        print(f"ERROR: Audio file not found: {audio_path}")
        sys.exit(1)

    # Determine reference text
    reference = args.reference or REFERENCE_TEXT

    # Determine models
    models = [args.model] if args.model else STT_MODELS

    print("=" * 70)
    print("GOOGLE STT (Speech-to-Text) TEST")
    print("=" * 70)

    test_stt(audio_path, models, reference)


if __name__ == "__main__":
    main()
