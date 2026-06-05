#!/usr/bin/env python3
"""
Stream a wav to the /ws/asr endpoint in real-time chunks; print partials + timing.

Run (see README.md for venv setup):
  python test_ws.py ws://localhost:8000/ws/asr sample.wav
  python test_ws.py ws://localhost:8000/ws/asr sample.wav --chunk-ms 100
"""
import argparse
import asyncio
import time

import soundfile as sf
import websockets


async def run(url: str, wav: str, chunk_ms: int):
    data, sr = sf.read(wav, dtype="int16")
    if data.ndim > 1:
        data = data[:, 0]
    if sr != 16000:
        raise SystemExit(f"need a 16 kHz mono wav, got {sr} Hz — resample it first")
    pcm = data.tobytes()
    chunk = int(0.001 * chunk_ms * sr) * 2  # bytes per chunk (int16 = 2 bytes/sample)

    async with websockets.connect(url, max_size=None) as ws:
        start = time.monotonic()

        async def sender():
            for i in range(0, len(pcm), chunk):
                await ws.send(pcm[i:i + chunk])
                await asyncio.sleep(chunk_ms / 1000)  # pace at real-time
            await ws.send("eof")

        async def receiver():
            first = None
            try:
                async for raw in ws:
                    t = (time.monotonic() - start) * 1000
                    if first is None:
                        first = t
                        print(f"--- TTF: first response at {t:.0f} ms ---")
                    print(f"[{t:7.0f} ms] {raw}")
            except websockets.exceptions.ConnectionClosed:
                pass

        await asyncio.gather(sender(), receiver())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url", help="e.g. ws://localhost:8000/ws/asr")
    p.add_argument("wav", help="16 kHz mono wav file")
    p.add_argument("--chunk-ms", type=int, default=100, help="audio chunk size in ms")
    args = p.parse_args()
    asyncio.run(run(args.url, args.wav, args.chunk_ms))


if __name__ == "__main__":
    main()
