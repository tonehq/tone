import asyncio
import contextvars
import io
import json
import logging
import os
import time

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from faster_qwen3_tts import FasterQwen3TTS

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
CHUNK_FRAMES = int(os.environ.get("TTS_CHUNK_FRAMES", "8"))

SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

app = FastAPI(title="Tone TTS — Qwen3-TTS 0.6B CustomVoice (faster-qwen3-tts)")
_model = None
_synth_lock = asyncio.Lock()


def _load_model():
    global _model
    if _model is not None:
        return _model
    log.info("torch %s | cuda=%s | cap=%s", torch.__version__, torch.cuda.is_available(),
             torch.cuda.get_device_capability() if torch.cuda.is_available() else "n/a")
    log.info("Loading %s via faster-qwen3-tts ...", MODEL_NAME)
    _model = FasterQwen3TTS.from_pretrained(MODEL_NAME)
    log.info("Model ready")
    return _model


def _float_to_pcm16(wav: np.ndarray) -> bytes:
    clipped = np.clip(wav, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def _chunk_to_pcm16(chunk) -> bytes:
    wav = np.asarray(chunk, dtype=np.float32).reshape(-1)
    return _float_to_pcm16(wav)


@app.on_event("startup")
def _warmup():
    model = _load_model()
    try:
        t0 = time.monotonic()
        for _ in model.generate_custom_voice_streaming(
            text="Hello.", speaker=DEFAULT_SPEAKER, language=DEFAULT_LANGUAGE, chunk_size=CHUNK_FRAMES
        ):
            pass
        log.info("warmup synth done in %dms", round((time.monotonic() - t0) * 1000))
    except Exception:
        log.exception("warmup synth failed (continuing)")


@app.get("/health")
def health():
    return {
        "status": "ok" if _model is not None else "loading",
        "model": MODEL_NAME,
        "engine": "faster-qwen3-tts",
        "cuda": torch.cuda.is_available(),
        "speakers": SPEAKERS,
    }


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
    model = _load_model()
    d0 = time.monotonic()
    async with _synth_lock:
        wavs, sr = await asyncio.get_running_loop().run_in_executor(
            None, lambda: model.generate_custom_voice(text=req.text, speaker=speaker, language=language)
        )
    wav = np.asarray(wavs[0] if isinstance(wavs, (list, tuple)) else wavs, dtype=np.float32).reshape(-1)
    log.info("/tts %r speaker=%s -> %.2fs audio (synth %dms)", req.text[:60], speaker,
             len(wav) / sr, round((time.monotonic() - d0) * 1000))
    buf = io.BytesIO()
    sf.write(buf, wav, int(sr), format="WAV", subtype="PCM_16")
    return Response(content=buf.getvalue(), media_type="audio/wav")


async def _stream_to_ws(ws: WebSocket, text: str, speaker: str, language: str):
    model = _load_model()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()
    t0 = time.monotonic()

    def produce():
        try:
            for audio_chunk, sr, _ in model.generate_custom_voice_streaming(
                text=text, speaker=speaker, language=language, chunk_size=CHUNK_FRAMES
            ):
                loop.call_soon_threadsafe(queue.put_nowait, (int(sr), _chunk_to_pcm16(audio_chunk)))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _DONE)

    producer = loop.run_in_executor(None, produce)
    started = False
    sample_rate = 0
    n_chunks = 0
    first_chunk_ms = 0
    try:
        while True:
            item = await queue.get()
            if item is _DONE:
                break
            if isinstance(item, Exception):
                raise item
            sr, pcm = item
            if not started:
                sample_rate = sr
                first_chunk_ms = round((time.monotonic() - t0) * 1000)
                await ws.send_json({"type": "start", "sample_rate": sample_rate})
                started = True
            n_chunks += 1
            await ws.send_bytes(pcm)
    finally:
        await producer
    return sample_rate, n_chunks, first_chunk_ms


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
            try:
                async with _synth_lock:
                    sr, n_chunks, first_ms = await _stream_to_ws(ws, text, speaker, language)
            except Exception as exc:
                log.exception("ws/tts %s synth failed", client)
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            total_ms = round((time.monotonic() - t0) * 1000)
            await ws.send_json({"type": "end", "ms": total_ms})
            log.info("ws/tts %s %r speaker=%s -> %d chunks @ %dHz (first %dms, total %dms)",
                     client, text[:60], speaker, n_chunks, sr, first_ms, total_ms)
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected (WebSocketDisconnect)", client)
    except Exception:
        log.exception("ws/tts %s loop failed", client)
        try:
            await ws.send_json({"type": "error", "detail": "internal error"})
        except Exception:
            pass
