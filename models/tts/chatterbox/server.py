"""
Tone TTS — Resemble AI Chatterbox via the chatterbox-streaming package (generate_stream).

STREAMING: emits audio chunks AS they are generated (first chunk after ~chunk_size speech
tokens, not the whole sentence) — this is the low-latency path (the plain generate() was
full-utterance ~1.8s). Same /ws/tts protocol as the Qwen server so Tone works unchanged.

  GET /health  -> {status, model, sample_rate, cuda}
  WS  /ws/tts  -> {text, ...} in; {type:start,sample_rate} + PCM16 chunks + {type:end,ms} out
"""
import asyncio
import contextvars
import json
import logging
import time

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

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

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEFAULT_EXAGGERATION = 0.5
DEFAULT_CFG = 0.5
CHUNK_SIZE = 25  # speech tokens per streamed chunk — smaller = lower TTFB (default fork value is 50)

app = FastAPI(title="Tone TTS — Chatterbox (streaming)")
_model = None
_sr = 24000


def _load_model():
    global _model, _sr
    if _model is not None:
        return _model
    log.info("loading Chatterbox (streaming) | torch %s | cuda=%s | device=%s",
             torch.__version__, torch.cuda.is_available(), DEVICE)
    from chatterbox.tts import ChatterboxTTS
    _model = ChatterboxTTS.from_pretrained(device=DEVICE)
    _sr = int(_model.sr)
    log.info("Chatterbox ready (sample_rate=%d, chunk_size=%d)", _sr, CHUNK_SIZE)
    return _model


def _chunk_to_pcm(audio_chunk) -> bytes:
    arr = audio_chunk.squeeze().detach().cpu().numpy().astype(np.float32)
    return (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def _stream_into(text: str, loop, q: asyncio.Queue):
    """Run generate_stream in a worker thread; push PCM chunks to the asyncio queue."""
    try:
        for audio_chunk, _metrics in _model.generate_stream(
            text, chunk_size=CHUNK_SIZE, exaggeration=DEFAULT_EXAGGERATION, cfg_weight=DEFAULT_CFG,
        ):
            loop.call_soon_threadsafe(q.put_nowait, _chunk_to_pcm(audio_chunk))
    except Exception as exc:  # noqa: BLE001
        loop.call_soon_threadsafe(q.put_nowait, ("__err__", str(exc)))
    finally:
        loop.call_soon_threadsafe(q.put_nowait, None)


@app.on_event("startup")
def _warmup():
    _load_model()
    try:
        for _ in _model.generate_stream("Hello, warming up.", chunk_size=CHUNK_SIZE,
                                        exaggeration=DEFAULT_EXAGGERATION, cfg_weight=DEFAULT_CFG):
            pass
        log.info("warmup stream done")
    except Exception:  # noqa: BLE001
        log.exception("warmup failed")


@app.get("/health")
def health():
    return JSONResponse(
        {"status": "ok" if _model is not None else "loading", "model": "chatterbox-streaming",
         "sample_rate": _sr, "cuda": torch.cuda.is_available()},
        status_code=200 if _model is not None else 503,
    )


@app.websocket("/ws/tts")
async def ws_tts(ws: WebSocket):
    await ws.accept()
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/tts open from %s", client)
    _load_model()
    loop = asyncio.get_running_loop()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            payload = msg.get("text")
            if payload is None:
                continue
            try:
                req = json.loads(payload)
            except Exception:  # noqa: BLE001
                await ws.send_json({"type": "error", "detail": "invalid json"})
                continue
            text = (req.get("text") or "").strip()
            if not text:
                await ws.send_json({"type": "error", "detail": "empty text"})
                continue

            t0 = time.monotonic()
            first_ms = 0
            n = 0
            q: asyncio.Queue = asyncio.Queue()
            fut = loop.run_in_executor(None, _stream_into, text, loop, q)
            try:
                while True:
                    item = await q.get()
                    if item is None:
                        break
                    if isinstance(item, tuple) and item and item[0] == "__err__":
                        log.error("ws/tts %s synth failed: %s", client, item[1])
                        await ws.send_json({"type": "error", "detail": item[1]})
                        break
                    if n == 0:
                        first_ms = round((time.monotonic() - t0) * 1000)
                        await ws.send_json({"type": "start", "sample_rate": _sr})
                    n += 1
                    await ws.send_bytes(item)
            except WebSocketDisconnect:
                raise
            finally:
                await fut
            total_ms = round((time.monotonic() - t0) * 1000)
            await ws.send_json({"type": "end", "ms": total_ms})
            log.info("ws/tts %s %r -> %d chunk(s) @ %dHz (first %dms, total %dms)",
                     client, text[:60], n, _sr, first_ms, total_ms)
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected", client)
    except Exception:  # noqa: BLE001
        log.exception("ws/tts %s loop failed", client)
