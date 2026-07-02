"""
Tone TTS — Piper (rhasspy) via piper-tts + onnxruntime, CPU-only.

Piper is a small VITS/ONNX model (15-32M params) designed for real-time CPU
synthesis — no GPU needed (<0.5 GB RAM, ~20-50 ms per sentence). It streams
sentence-by-sentence: synthesize_stream_raw yields one PCM16 chunk per
sentence, so TTFB is the synthesis time of the FIRST sentence only.

Same wire protocol as the Qwen/Chatterbox TTS servers so Tone works unchanged:
  GET  /health -> {status, model, sample_rate, engine}
  POST /tts    -> WAV bytes (batch)
  WS   /ws/tts -> {text} in; {type:start,sample_rate} + PCM16 chunks + {type:end,ms} out
"""
import asyncio
import contextvars
import io
import json
import logging
import os
import threading
import time
import wave

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

_trace_ctx: contextvars.ContextVar = contextvars.ContextVar("trace_id", default="none")


class _TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = _trace_ctx.get()
        return True


_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s trace_id=%(trace_id)s %(message)s"))
_handler.addFilter(_TraceFilter())
logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)
for _name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    _lg = logging.getLogger(_name)
    _lg.handlers = [_handler]
    _lg.propagate = False
log = logging.getLogger("tts")

MODEL_PATH = os.environ.get("PIPER_MODEL", "/cache/en_US-lessac-medium.onnx")
SENTENCE_SILENCE = float(os.environ.get("PIPER_SENTENCE_SILENCE", "0.1"))

app = FastAPI(title="Tone TTS — Piper (CPU, sentence-streaming)")
_voice = None
_sr = 22050


def _load_model():
    global _voice, _sr
    if _voice is not None:
        return _voice
    from piper import PiperVoice

    log.info("loading Piper voice %s ...", MODEL_PATH)
    _voice = PiperVoice.load(MODEL_PATH, config_path=MODEL_PATH + ".json")
    _sr = int(_voice.config.sample_rate)
    log.info("Piper ready (sample_rate=%d, sentence_silence=%.2fs)", _sr, SENTENCE_SILENCE)
    return _voice


async def synthesize_stream(text: str):
    """Yield PCM16 chunks (one per sentence) without blocking the event loop."""
    voice = _load_model()
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()

    def run():
        try:
            for chunk in voice.synthesize_stream_raw(text, sentence_silence=SENTENCE_SILENCE):
                loop.call_soon_threadsafe(q.put_nowait, chunk)
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(q.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    threading.Thread(target=run, daemon=True).start()
    while True:
        item = await q.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item


@app.on_event("startup")
def _warmup():
    _load_model()
    # one synchronous warmup synth so the first real request isn't cold
    t0 = time.monotonic()
    n = sum(len(c) for c in _voice.synthesize_stream_raw("Warm up.", sentence_silence=0.0))
    log.info("warmup: %d bytes in %dms", n, round((time.monotonic() - t0) * 1000))


@app.get("/health")
async def health():
    ok = _voice is not None
    return JSONResponse(
        content={"status": "ok" if ok else "loading", "model": os.path.basename(MODEL_PATH),
                 "engine": "piper-onnx-cpu", "sample_rate": _sr},
        status_code=200 if ok else 503,
    )


class TTSRequest(BaseModel):
    text: str


@app.post("/tts")
async def tts(req: TTSRequest, x_trace_id: str = Header(default="none")):
    _trace_ctx.set(x_trace_id)
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="empty text")
    d0 = time.monotonic()
    parts = [pcm async for pcm in synthesize_stream(req.text)]
    pcm = b"".join(parts)
    log.info("/tts %r -> %.2fs audio (synth %dms)", req.text[:60],
             len(pcm) / 2 / _sr, round((time.monotonic() - d0) * 1000))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_sr)
        w.writeframes(pcm)
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.websocket("/ws/tts")
async def ws_tts(ws: WebSocket):
    await ws.accept()
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/tts open from %s", client)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                log.info("ws/tts %s disconnected", client)
                break
            payload = msg.get("text")
            if payload is None:
                continue
            try:
                req = json.loads(payload)
            except Exception:
                await ws.send_json({"type": "error", "detail": "invalid json"})
                continue
            text = (req.get("text") or "").strip()
            if not text:
                await ws.send_json({"type": "error", "detail": "empty text"})
                continue
            t0 = time.monotonic()
            n_chunks = 0
            first_ms = 0
            try:
                async for pcm in synthesize_stream(text):
                    if n_chunks == 0:
                        first_ms = round((time.monotonic() - t0) * 1000)
                        await ws.send_json({"type": "start", "sample_rate": _sr})
                    n_chunks += 1
                    await ws.send_bytes(pcm)
            except WebSocketDisconnect:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("ws/tts %s synth failed", client)
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            total_ms = round((time.monotonic() - t0) * 1000)
            await ws.send_json({"type": "end", "ms": total_ms})
            log.info("ws/tts %s %r -> %d chunks @ %dHz (first %dms, total %dms)",
                     client, text[:60], n_chunks, _sr, first_ms, total_ms)
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected (WebSocketDisconnect)", client)
    except Exception:
        log.exception("ws/tts %s loop failed", client)
