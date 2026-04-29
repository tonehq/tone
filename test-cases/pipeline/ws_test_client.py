#!/usr/bin/env python3
"""WebSocket test client — send audio to /ws/test, save bot response.

Usage:
    # Generate input audio + send to bot + save conversation:
    python test-cases/pipeline/ws_test_client.py --agent-id 20 --text "Hello, how are you?"

    # Use an existing WAV file as input:
    python test-cases/pipeline/ws_test_client.py --agent-id 20 --input my_audio.wav

    # Custom server URL:
    python test-cases/pipeline/ws_test_client.py --agent-id 20 --text "Hi" --url ws://192.168.1.5:8000

Output:
    test-cases/pipeline/recordings/ws_input.wav         <- what you said
    test-cases/pipeline/recordings/ws_bot_response.wav  <- what bot said
    test-cases/pipeline/recordings/ws_conversation.wav  <- both combined (stereo)

Listen:
    afplay test-cases/pipeline/recordings/ws_conversation.wav
    afplay test-cases/pipeline/recordings/ws_bot_response.wav
"""

import argparse
import asyncio
import math
import os
import struct
import sys
import time
import wave

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "recordings")


def create_wav_from_text(path: str, text: str) -> str:
    """Create a WAV file from text using macOS `say` or sine wave fallback."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    import shutil, subprocess
    if shutil.which("say"):
        aiff = path.replace(".wav", ".aiff")
        subprocess.run(["say", "-o", aiff, "-r", "180", text], check=True, capture_output=True)
        subprocess.run(
            ["afconvert", aiff, path, "-d", "LEI16@16000", "-f", "WAVE", "-c", "1", "--mix"],
            check=True, capture_output=True,
        )
        os.remove(aiff)
        print(f"  Generated: {path}")
    else:
        sr = 16000
        n = int(sr * 1.5)
        samples = [int(16000 * math.sin(2 * math.pi * 440 * i / sr)) for i in range(n)]
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{n}h", *samples))
        print(f"  Generated (sine wave fallback): {path}")
    return path


def save_wav(path: str, audio: bytes, sample_rate: int) -> str:
    """Save raw PCM bytes as a WAV file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)
    return path


def build_stereo(user: bytes, bot: bytes, delay_s: float, sr: int) -> bytes:
    """Combine user (left) + bot (right) into stereo."""
    silence = b"\x00" * (int(delay_s * sr) * 2)
    bot_padded = silence + bot
    total = max(len(user), len(bot_padded))
    left = user + b"\x00" * (total - len(user))
    right = bot_padded + b"\x00" * (total - len(bot_padded))
    result = bytearray()
    for i in range(0, total, 2):
        result.extend(left[i : i + 2])
        result.extend(right[i : i + 2])
    return bytes(result)


async def run_test(ws_url: str, input_wav: str):
    """Connect to WebSocket, send audio, receive bot response."""
    from websockets.asyncio.client import connect

    with wave.open(input_wav, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        user_audio = wf.readframes(wf.getnframes())
        in_dur_ms = len(user_audio) / (sr * ch * 2) * 1000

    print(f"\n  Sending: {input_wav} ({in_dur_ms:.0f} ms, {sr}Hz)")
    print(f"  Connecting: {ws_url}")

    bot_audio = bytearray()
    t_start = time.perf_counter()

    async with connect(ws_url, open_timeout=10) as ws:
        print(f"  Connected!")

        # Send audio in 20ms chunks (real-time pace)
        chunk_ms = 20
        chunk_bytes = int(sr * ch * 2 * chunk_ms / 1000)

        for i in range(0, len(user_audio), chunk_bytes):
            chunk = user_audio[i:i + chunk_bytes]
            await ws.send(chunk)
            await asyncio.sleep(chunk_ms / 1000)

        t_audio_sent = time.perf_counter()
        print(f"  Audio sent ({(t_audio_sent - t_start) * 1000:.0f} ms)")

        # Send 1.5s of silence to trigger VAD end-of-speech
        silence = b"\x00" * chunk_bytes
        for _ in range(75):
            await ws.send(silence)
            await asyncio.sleep(chunk_ms / 1000)

        print(f"  Silence sent, waiting for bot...")

        # Receive bot audio
        try:
            while True:
                data = await asyncio.wait_for(ws.recv(), timeout=20.0)
                if isinstance(data, bytes) and len(data) > 0:
                    bot_audio.extend(data)
                    if len(bot_audio) % 10000 < len(data):
                        print(f"    receiving... {len(bot_audio)} bytes", end="\r")
        except (asyncio.TimeoutError, Exception):
            pass

    t_end = time.perf_counter()
    return user_audio, sr, bytes(bot_audio), t_start, t_audio_sent, t_end


def main():
    parser = argparse.ArgumentParser(description="WebSocket pipeline test client")
    parser.add_argument("--agent-id", type=int, default=None, help="Agent ID from DB")
    parser.add_argument("--phone-number", type=str, default=None, help="Phone number mapped to agent (e.g. +1234567890)")
    parser.add_argument("--text", type=str, default=None, help="Text to speak (generates WAV)")
    parser.add_argument("--input", type=str, default=None, help="Path to existing WAV file")
    parser.add_argument("--url", type=str, default="ws://localhost:8000", help="Server WebSocket URL")
    args = parser.parse_args()

    if not args.agent_id and not args.phone_number:
        parser.error("Pass --agent-id or --phone-number")

    os.makedirs(RECORDINGS_DIR, exist_ok=True)

    # Prepare input audio
    if args.input:
        input_wav = args.input
    elif args.text:
        input_wav = os.path.join(RECORDINGS_DIR, "ws_input.wav")
        if os.path.exists(input_wav):
            os.remove(input_wav)
        create_wav_from_text(input_wav, args.text)
    else:
        input_wav = os.path.join(RECORDINGS_DIR, "ws_input.wav")
        if not os.path.exists(input_wav):
            create_wav_from_text(input_wav, "Hello, how are you?")

    # Build WebSocket URL with agent_id or phone_number
    if args.agent_id:
        ws_url = f"{args.url}/ws/test?agent_id={args.agent_id}"
    else:
        from urllib.parse import quote
        ws_url = f"{args.url}/ws/test?phone_number={quote(args.phone_number)}"

    # Run WebSocket test
    user_audio, in_sr, bot_audio, t_start, t_audio_sent, t_end = asyncio.run(
        run_test(ws_url, input_wav)
    )

    total_ms = (t_end - t_start) * 1000
    print(f"\n  ={'=' * 40}")
    print(f"  Total time: {total_ms:.0f} ms")
    print(f"  Bot audio:  {len(bot_audio)} bytes")

    if not bot_audio:
        print("\n  No bot audio received! Check server logs.")
        return

    # Save bot response
    out_sr = 24000  # default TTS output rate
    bot_path = os.path.join(RECORDINGS_DIR, "ws_bot_response.wav")
    save_wav(bot_path, bot_audio, out_sr)
    bot_dur_ms = len(bot_audio) / (out_sr * 2) * 1000
    print(f"\n  Bot response: {bot_path} ({bot_dur_ms:.0f} ms)")

    # Save combined conversation (stereo: user=L, bot=R)
    if in_sr != out_sr:
        try:
            import audioop
            user_audio, _ = audioop.ratecv(user_audio, 2, 1, in_sr, out_sr, None)
        except ImportError:
            pass

    delay_s = max(0, t_audio_sent - t_start)
    stereo = build_stereo(user_audio, bot_audio, delay_s, out_sr)
    conversation_path = os.path.join(RECORDINGS_DIR, "ws_conversation.wav")
    with wave.open(conversation_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(out_sr)
        wf.writeframes(stereo)

    with wave.open(conversation_path, "rb") as wf:
        conv_dur_ms = wf.getnframes() / wf.getframerate() * 1000
    print(f"  Conversation: {conversation_path} ({conv_dur_ms:.0f} ms)")

    print(f"\n  Listen:")
    print(f"    afplay {bot_path}")
    print(f"    afplay {conversation_path}")


if __name__ == "__main__":
    main()
