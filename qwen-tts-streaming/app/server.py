import asyncio
import contextvars
import io
import json
import logging
import os
import time

import httpx
import numpy as np
import soundfile as sf
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

MODEL_NAME = os.environ.get("TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
DEFAULT_SPEAKER = os.environ.get("TTS_SPEAKER", "Ryan")
DEFAULT_LANGUAGE = os.environ.get("TTS_LANGUAGE", "English")
ENGINE_URL = os.environ.get("TTS_ENGINE_URL", "http://127.0.0.1:8091")
SAMPLE_RATE = 24000

SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

app = FastAPI(title="Tone TTS — Qwen3-TTS 0.6B CustomVoice (vllm-omni proxy)")
_client: httpx.AsyncClient | None = None


async def _warmup_engine():
    for _ in range(360):
        try:
            r = await _client.get("/health", timeout=3.0)
            if r.status_code == 200:
                break
        except Exception:
            pass
        await asyncio.sleep(5)
    t0 = time.monotonic()
    for batch in (1, 2, 4):
        async def _one():
            try:
                async for _ in synthesize_stream("Hello, warming up.", DEFAULT_SPEAKER, DEFAULT_LANGUAGE):
                    pass
            except Exception:
                log.exception("warmup synth failed")
        await asyncio.gather(*(_one() for _ in range(batch)))
    log.info("engine warmup done in %dms", round((time.monotonic() - t0) * 1000))


@app.on_event("startup")
async def _startup():
    global _client
    _client = httpx.AsyncClient(base_url=ENGINE_URL, timeout=httpx.Timeout(300.0, connect=5.0))
    asyncio.create_task(_warmup_engine())


@app.on_event("shutdown")
async def _shutdown():
    if _client:
        await _client.aclose()


async def synthesize_stream(text: str, speaker: str, language: str):
    payload = {
        "model": MODEL_NAME,
        "input": text,
        "voice": speaker.lower(),
        "language": language,
        "response_format": "pcm",
        "stream": True,
    }
    remainder = b""
    async with _client.stream("POST", "/v1/audio/speech", json=payload) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise RuntimeError(f"engine {resp.status_code}: {body[:200].decode(errors='replace')}")
        async for raw in resp.aiter_bytes():
            data = remainder + raw
            cut = len(data) - (len(data) % 2)
            if cut:
                yield data[:cut]
            remainder = data[cut:]
    if remainder:
        yield remainder + b"\x00"


@app.get("/health")
async def health():
    try:
        r = await _client.get("/health", timeout=5.0)
        engine_ok = r.status_code == 200
    except Exception:
        engine_ok = False
    body = {
        "status": "ok" if engine_ok else "loading",
        "model": MODEL_NAME,
        "engine": "vllm-omni",
        "engine_ok": engine_ok,
        "speakers": SPEAKERS,
    }
    return JSONResponse(content=body, status_code=200 if engine_ok else 503)


class TTSRequest(BaseModel):
    text: str
    speaker: str | None = None
    language: str | None = None


@app.post("/tts")
async def tts(req: TTSRequest, x_trace_id: str = Header(default="none")):
    _trace_ctx.set(x_trace_id)
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="empty text")
    speaker = req.speaker or DEFAULT_SPEAKER
    language = req.language or DEFAULT_LANGUAGE
    d0 = time.monotonic()
    parts = []
    async for pcm in synthesize_stream(req.text, speaker, language):
        parts.append(pcm)
    wav = np.frombuffer(b"".join(parts), dtype="<i2").astype(np.float32) / 32767.0
    log.info("/tts %r speaker=%s -> %.2fs audio (synth %dms)", req.text[:60], speaker,
             len(wav) / SAMPLE_RATE, round((time.monotonic() - d0) * 1000))
    buf = io.BytesIO()
    sf.write(buf, wav, SAMPLE_RATE, format="WAV", subtype="PCM_16")
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
            speaker = req.get("speaker") or DEFAULT_SPEAKER
            language = req.get("language") or DEFAULT_LANGUAGE
            t0 = time.monotonic()
            n_chunks = 0
            first_ms = 0
            try:
                async for pcm in synthesize_stream(text, speaker, language):
                    if n_chunks == 0:
                        first_ms = round((time.monotonic() - t0) * 1000)
                        await ws.send_json({"type": "start", "sample_rate": SAMPLE_RATE})
                    n_chunks += 1
                    await ws.send_bytes(pcm)
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                log.exception("ws/tts %s synth failed", client)
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            total_ms = round((time.monotonic() - t0) * 1000)
            await ws.send_json({"type": "end", "ms": total_ms})
            log.info("ws/tts %s %r speaker=%s -> %d chunks @ %dHz (first %dms, total %dms)",
                     client, text[:60], speaker, n_chunks, SAMPLE_RATE, first_ms, total_ms)
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected (WebSocketDisconnect)", client)
    except Exception:
        log.exception("ws/tts %s loop failed", client)
        try:
            await ws.send_json({"type": "error", "detail": "internal error"})
        except Exception:
            pass
