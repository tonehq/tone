import asyncio, io, json, time, urllib.request
import numpy as np
import soundfile as sf
import websockets

URL = "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/mlk.flac"
WS = "ws://localhost:8000/ws/asr"
CHUNK_MS = 100            # send 100ms of audio per frame
REALTIME = True           # pace sends to real-time (simulate a live call)

print("downloading sample...")
raw = urllib.request.urlopen(URL, timeout=30).read()
audio, sr = sf.read(io.BytesIO(raw), dtype="float32")
if audio.ndim > 1:
    audio = audio.mean(axis=1)
if sr != 16000:
    import librosa
    audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    sr = 16000
pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
dur = len(audio) / sr
print(f"clip: {dur:.1f}s, {len(pcm)} bytes PCM16 @16k")

CHUNK = int(16000 * 2 * CHUNK_MS / 1000)   # bytes per frame


async def run():
    async with websockets.connect(WS, max_size=None) as ws:
        t0 = time.monotonic()
        first = {"t": None}

        async def sender():
            for i in range(0, len(pcm), CHUNK):
                await ws.send(pcm[i:i + CHUNK])
                if REALTIME:
                    await asyncio.sleep(CHUNK_MS / 1000)
            await ws.send("eof")
            print(f"[{(time.monotonic()-t0)*1000:.0f}ms] sent eof (audio was {dur:.1f}s)")

        async def receiver():
            async for msg in ws:
                m = json.loads(msg)
                el = (time.monotonic() - t0) * 1000
                if m["type"] == "partial" and first["t"] is None:
                    first["t"] = el
                    print(f">>> FIRST PARTIAL @ {el:.0f}ms")
                print(f"[{el:.0f}ms] {m['type']}: {m.get('text','')!r}")
                if m["type"] in ("final", "error"):
                    break

        await asyncio.gather(sender(), receiver())
        if first["t"] is not None:
            print(f"\nfirst-partial latency: {first['t']:.0f}ms   (clip {dur:.1f}s)")


asyncio.run(run())
