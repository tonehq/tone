"""
Test script to simulate a Twilio incoming call via WebSocket.

Connects to the local /ws endpoint and sends Twilio-format messages
to trigger the incoming call flow.

Usage:
    python test_incoming_call.py

    # Send a WAV file as speech input (triggers the bot to respond):
    python test_incoming_call.py --audio-file hello.wav

    # Send silence audio frames to keep connection alive:
    python test_incoming_call.py --send-audio

    # With custom server URL:
    python test_incoming_call.py --url ws://localhost:7860/ws
"""

import argparse
import asyncio
import audioop
import base64
import json
import os
import uuid
import wave

from dotenv import load_dotenv
import websockets

load_dotenv()


TO_NUMBER = "+19894742667"

# Twilio sends mulaw 8kHz mono audio - 20ms chunks (160 bytes each)
MULAW_SILENCE_FRAME = base64.b64encode(b"\xff" * 160).decode("ascii")
CHUNK_SIZE = 160  # 20ms at 8kHz mulaw
CHUNK_DURATION = 0.02  # 20ms


def build_connected_message():
    """First message Twilio sends after WebSocket connection."""
    return json.dumps({
        "event": "connected",
        "protocol": "Call",
        "version": "1.0.0",
    })


def build_start_message(stream_sid: str, call_sid: str, account_sid: str):
    """Second message Twilio sends - the 'start' event with call metadata."""
    return json.dumps({
        "event": "start",
        "sequenceNumber": "1",
        "start": {
            "streamSid": stream_sid,
            "accountSid": account_sid,
            "callSid": call_sid,
            "tracks": ["inbound"],
            "customParameters": {
                "to": TO_NUMBER,
            },
            "mediaFormat": {
                "encoding": "audio/x-mulaw",
                "sampleRate": 8000,
                "channels": 1,
            },
        },
        "streamSid": stream_sid,
    })


def build_media_message(stream_sid: str, sequence: int, chunk: int, timestamp: int, payload: str):
    """A media event containing audio data."""
    return json.dumps({
        "event": "media",
        "sequenceNumber": str(sequence),
        "media": {
            "track": "inbound",
            "chunk": str(chunk),
            "timestamp": str(timestamp),
            "payload": payload,
        },
        "streamSid": stream_sid,
    })


def load_wav_as_mulaw_chunks(wav_path: str) -> list[str]:
    """Load a WAV file and convert it to mulaw 8kHz mono chunks (base64-encoded).

    Supports WAV files of any sample rate, channels, or bit depth.
    """
    with wave.open(wav_path, "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        raw_data = wf.readframes(wf.getnframes())

    # Convert to mono if stereo
    if channels == 2:
        raw_data = audioop.tomono(raw_data, sample_width, 1, 1)

    # Convert to 16-bit if needed (audioop.lin2ulaw needs specific widths)
    if sample_width != 2:
        raw_data = audioop.lin2lin(raw_data, sample_width, 2)
        sample_width = 2

    # Resample to 8kHz if needed
    if sample_rate != 8000:
        raw_data, _ = audioop.ratecv(raw_data, sample_width, 1, sample_rate, 8000, None)

    # Convert PCM 16-bit to mulaw
    mulaw_data = audioop.lin2ulaw(raw_data, sample_width)

    # Split into 160-byte chunks (20ms at 8kHz)
    chunks = []
    for i in range(0, len(mulaw_data), CHUNK_SIZE):
        chunk = mulaw_data[i : i + CHUNK_SIZE]
        # Pad last chunk with silence if needed
        if len(chunk) < CHUNK_SIZE:
            chunk += b"\xff" * (CHUNK_SIZE - len(chunk))
        chunks.append(base64.b64encode(chunk).decode("ascii"))

    return chunks


async def receive_loop(ws):
    """Listen for server responses and print them."""
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                event = data.get("event", data.get("type", "unknown"))
                label = data.get("label", "")
                prefix = f"{label}:" if label else ""
                print(f"[RECV] {prefix}{event} | {str(message)[:180]}")
            except json.JSONDecodeError:
                print(f"[RECV] raw: {str(message)[:180]}")
    except websockets.exceptions.ConnectionClosed:
        print("[INFO] Connection closed by server")


async def simulate_incoming_call(ws_url: str, send_audio: bool = False, audio_file: str = None):
    """Connect to the /ws endpoint and simulate a Twilio incoming call."""
    stream_sid = f"MZ{uuid.uuid4().hex}"
    call_sid = f"CA{uuid.uuid4().hex}"
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", f"AC{uuid.uuid4().hex}")

    print(f"Connecting to {ws_url} ...")
    print(f"  Stream SID : {stream_sid}")
    print(f"  Call SID   : {call_sid}")
    print(f"  To Number  : {TO_NUMBER}")
    if audio_file:
        print(f"  Audio File : {audio_file}")
    print()

    async with websockets.connect(ws_url) as ws:
        # 1) Send "connected" event (first message)
        connected_msg = build_connected_message()
        await ws.send(connected_msg)
        print(f"[SENT] connected")

        # 2) Send "start" event (second message - triggers detection)
        start_msg = build_start_message(stream_sid, call_sid, account_sid)
        await ws.send(start_msg)
        print(f"[SENT] start (streamSid={stream_sid[:20]}...)")
        print()

        if audio_file:
            # Load WAV and send as mulaw chunks, then follow with silence
            print(f"Loading audio from {audio_file}...")
            chunks = load_wav_as_mulaw_chunks(audio_file)
            print(f"Loaded {len(chunks)} chunks ({len(chunks) * 20}ms of audio)")
            print("Sending audio...")

            async def send_file_then_silence():
                seq = 2
                chunk_num = 1
                timestamp = 0

                try:
                    # Send the WAV audio
                    for payload in chunks:
                        media_msg = build_media_message(stream_sid, seq, chunk_num, timestamp, payload)
                        await ws.send(media_msg)
                        seq += 1
                        chunk_num += 1
                        timestamp += 20
                        await asyncio.sleep(CHUNK_DURATION)

                    print(f"[SENT] {len(chunks)} audio chunks from file")
                    print("Sending silence (waiting for bot response, Ctrl+C to stop)...")

                    # Continue with silence to keep connection alive
                    while True:
                        media_msg = build_media_message(stream_sid, seq, chunk_num, timestamp, MULAW_SILENCE_FRAME)
                        await ws.send(media_msg)
                        seq += 1
                        chunk_num += 1
                        timestamp += 20
                        await asyncio.sleep(CHUNK_DURATION)
                except websockets.exceptions.ConnectionClosed:
                    print("[INFO] Connection closed by server")

            await asyncio.gather(send_file_then_silence(), receive_loop(ws))

        elif send_audio:
            # Send silence audio frames every 20ms to keep the call alive
            print("Sending silence audio frames (Ctrl+C to stop)...")

            async def send_silence_loop():
                seq = 2
                chunk_num = 1
                timestamp = 0
                try:
                    while True:
                        media_msg = build_media_message(stream_sid, seq, chunk_num, timestamp, MULAW_SILENCE_FRAME)
                        await ws.send(media_msg)
                        seq += 1
                        chunk_num += 1
                        timestamp += 20
                        await asyncio.sleep(CHUNK_DURATION)
                except websockets.exceptions.ConnectionClosed:
                    print("[INFO] Connection closed by server")

            await asyncio.gather(send_silence_loop(), receive_loop(ws))
        else:
            # Just listen for responses
            print("Waiting for server responses...")
            await receive_loop(ws)


def main():
    parser = argparse.ArgumentParser(description="Simulate a Twilio incoming call via WebSocket")
    parser.add_argument(
        "--url",
        default="ws://localhost:7860/ws",
        help="WebSocket URL to connect to (default: ws://localhost:7860/ws)",
    )
    parser.add_argument(
        "--send-audio",
        action="store_true",
        help="Send silence audio frames to keep the call alive",
    )
    parser.add_argument(
        "--audio-file",
        type=str,
        help="Path to a WAV file to send as speech input (any sample rate/channels supported)",
    )
    args = parser.parse_args()

    if args.audio_file and not os.path.isfile(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        return

    try:
        asyncio.run(simulate_incoming_call(args.url, args.send_audio, args.audio_file))
    except KeyboardInterrupt:
        print("\nStopped.")
    except ConnectionRefusedError:
        print(f"\nCould not connect to {args.url}. Is the server running?")


if __name__ == "__main__":
    main()
