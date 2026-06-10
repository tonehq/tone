"""
Tone TTS — Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice via qwen-tts + FastAPI.

Open-weights (Apache-2.0), pulled from HuggingFace. Runs as a SIDECAR container
in the existing STT pod, sharing the same A16-8Q vGPU (NVIDIA_VISIBLE_DEVICES=all,
no nvidia.com/gpu request — the STT container owns the integer GPU allocation).

Notes:
  - Python 3.12+ required by qwen-tts, so this container uses an Ubuntu 24.04 CUDA
    base image (NOT the pytorch/pytorch:2.6 image STT uses, which ships 3.11).
  - We load with attn_implementation="sdpa" (PyTorch built-in) to avoid building
    flash-attn (needs nvcc/devel image). Set QWEN_ATTN=flash_attention_2 to opt in.
  - CustomVoice = 9 preset speakers, no reference audio needed.

Endpoints: GET /health, POST /tts (debug WAV), WS /ws/tts (streaming PCM16-LE).
Streaming here is sentence-level: synthesize each request fully, then stream the
PCM out in chunks. Token-level streaming is the next iteration.
"""

import asyncio
import contextvars
import io
import logging
import os
import time

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from qwen_tts import Qwen3TTSModel

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
ATTN_IMPL = os.environ.get("QWEN_ATTN", "sdpa")
DEFAULT_SPEAKER = os.environ.get("TTS_SPEAKER", "Ryan")
DEFAULT_LANGUAGE = os.environ.get("TTS_LANGUAGE", "English")
# Stream PCM out in ~200ms slices (re-resolved per-request against the real SR).
CHUNK_MS = int(os.environ.get("TTS_CHUNK_MS", "200"))

# CustomVoice preset speakers (Qwen3-TTS-0.6B-CustomVoice).
SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

app = FastAPI(title="Tone TTS — Qwen3-TTS 0.6B CustomVoice")
_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    log.info("torch %s | cuda=%s | cap=%s", torch.__version__, torch.cuda.is_available(),
             torch.cuda.get_device_capability() if torch.cuda.is_available() else "n/a")
    log.info("Loading %s (attn=%s) ...", MODEL_NAME, ATTN_IMPL)
    device_map = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    _model = Qwen3TTSModel.from_pretrained(
        MODEL_NAME,
        device_map=device_map,
        dtype=dtype,
        attn_implementation=ATTN_IMPL,
    )
    log.info("Model ready on %s", device_map)
    return _model


def _synth(text: str, speaker: str, language: str):
    """Blocking synthesis -> (float32 mono numpy, sample_rate)."""
    model = _load_model()
    with torch.no_grad():
        wavs, sr = model.generate_custom_voice(text=text, language=language, speaker=speaker)
    wav = np.asarray(wavs[0], dtype=np.float32)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    return wav, int(sr)


def _float_to_pcm16(wav: np.ndarray) -> bytes:
    clipped = np.clip(wav, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


@app.on_event("startup")
def _warmup():
    _load_model()


@app.get("/health")
def health():
    return {
        "status": "ok" if _model is not None else "loading",
        "model": MODEL_NAME,
        "cuda": torch.cuda.is_available(),
        "speakers": SPEAKERS,
    }


class TTSRequest(BaseModel):
    text: str
    speaker: str | None = None
    language: str | None = None


@app.post("/tts")
async def tts(req: TTSRequest, x_trace_id: str = Header(default="none")):
    """Debug endpoint: returns a full WAV (not streamed)."""
    _trace_ctx.set(x_trace_id)
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="empty text")
    speaker = req.speaker or DEFAULT_SPEAKER
    language = req.language or DEFAULT_LANGUAGE
    loop = asyncio.get_running_loop()
    d0 = time.monotonic()
    wav, sr = await loop.run_in_executor(None, _synth, req.text, speaker, language)
    log.info("/tts %r speaker=%s -> %.2fs audio (synth %dms)", req.text[:60], speaker,
             len(wav) / sr, round((time.monotonic() - d0) * 1000))
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.websocket("/ws/tts")
async def ws_tts(ws: WebSocket):
    """
    Streaming TTS. Per request the client sends a JSON message:
        {"text": "...", "speaker": "Ryan", "language": "English"}
    The server replies with:
        {"type": "start", "sample_rate": N}   (JSON)
        <binary PCM16-LE frames>               (CHUNK_MS each)
        {"type": "end", "ms": <total>}         (JSON)
    The socket stays open for multiple requests (one TTS turn each).
    """
    await ws.accept()
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/tts open from %s", client)
    loop = asyncio.get_running_loop()
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
                import json
                req = json.loads(payload)
            except Exception:  # noqa: BLE001
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
                wav, sr = await loop.run_in_executor(None, _synth, text, speaker, language)
            except Exception as exc:  # noqa: BLE001
                log.exception("ws/tts %s synth failed", client)
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            await ws.send_json({"type": "start", "sample_rate": sr})
            pcm = _float_to_pcm16(wav)
            step = max(1, int(sr * CHUNK_MS / 1000)) * 2  # bytes per chunk (PCM16 = 2 bytes/sample)
            for i in range(0, len(pcm), step):
                await ws.send_bytes(pcm[i:i + step])
            await ws.send_json({"type": "end", "ms": round((time.monotonic() - t0) * 1000)})
            log.info("ws/tts %s %r speaker=%s -> %.2fs audio (%dms)", client, text[:60], speaker,
                     len(wav) / sr, round((time.monotonic() - t0) * 1000))
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected (WebSocketDisconnect)", client)
    except Exception:  # noqa: BLE001
        log.exception("ws/tts %s loop failed", client)
        try:
            await ws.send_json({"type": "error", "detail": "internal error"})
        except Exception:  # noqa: BLE001
            pass
