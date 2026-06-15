"""
Tone TTS — Resemble AI Chatterbox via the chatterbox-tts package.

Chatterbox (~500M) fits an 8GB GPU. This server loads ChatterboxTTS and exposes the same
/ws/tts protocol as the Qwen server (nemotron-style), so Tone's QwenWebSocketTTSService-style
client works. Text is split into sentences and synthesized one at a time, streaming each
sentence's PCM so the bot starts speaking after the FIRST sentence (lower TTFB than
generating the whole utterance first).

  GET /health  -> {status, model, sample_rate, cuda}
  WS  /ws/tts  -> {text, ...} in; {type:start,sample_rate} + PCM16 chunks + {type:end,ms} out
"""
import asyncio
import contextvars
import json
import logging
import re
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

app = FastAPI(title="Tone TTS — Chatterbox")
_model = None
_sr = 24000


def _load_model():
    global _model, _sr
    if _model is not None:
        return _model
    log.info("loading Chatterbox | torch %s | cuda=%s | device=%s", torch.__version__, torch.cuda.is_available(), DEVICE)
    from chatterbox.tts import ChatterboxTTS
    _model = ChatterboxTTS.from_pretrained(device=DEVICE)
    _sr = int(_model.sr)
    log.info("Chatterbox ready (sample_rate=%d)", _sr)
    return _model


def _synth_pcm(text: str) -> bytes:
    with torch.no_grad():
        wav = _model.generate(text, exaggeration=DEFAULT_EXAGGERATION, cfg_weight=DEFAULT_CFG)
    arr = wav.squeeze().detach().cpu().numpy().astype(np.float32)
    return (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def _sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()] or [text.strip()]


@app.on_event("startup")
def _warmup():
    _load_model()
    try:
        _synth_pcm("Hello, warming up.")
        log.info("warmup synth done")
    except Exception:  # noqa: BLE001
        log.exception("warmup failed")


@app.get("/health")
def health():
    return JSONResponse(
        {"status": "ok" if _model is not None else "loading", "model": "chatterbox",
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
            try:
                for sent in _sentences(text):
                    pcm = await loop.run_in_executor(None, _synth_pcm, sent)
                    if n == 0:
                        first_ms = round((time.monotonic() - t0) * 1000)
                        await ws.send_json({"type": "start", "sample_rate": _sr})
                    n += 1
                    await ws.send_bytes(pcm)
            except WebSocketDisconnect:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("ws/tts %s synth failed", client)
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            total_ms = round((time.monotonic() - t0) * 1000)
            await ws.send_json({"type": "end", "ms": total_ms})
            log.info("ws/tts %s %r -> %d sentence(s) @ %dHz (first %dms, total %dms)",
                     client, text[:60], n, _sr, first_ms, total_ms)
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected", client)
    except Exception:  # noqa: BLE001
        log.exception("ws/tts %s loop failed", client)
