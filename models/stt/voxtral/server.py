"""
Tone STT bridge — Voxtral-Mini-4B-Realtime via vLLM's /v1/realtime streaming API.

Voxtral Realtime is a NATIVE STREAMING ASR model (13 languages, <500ms). The official
serving path is vLLM's /v1/realtime WebSocket API (NOT the transformers streaming API,
which is broken). This process runs the bridge: Tone connects to /ws/asr (nemotron
protocol, so NvidiaWebSocketService works unchanged); the bridge opens a vLLM
/v1/realtime session, forwards PCM as base64 input_audio_buffer.append chunks, and
relays transcription.delta -> {partial} / transcription.done -> {final} back to Tone.

vLLM runs in the same pod on 127.0.0.1:8091 (see deployment).
  GET /health   -> {status, model, engine_ok}
  WS  /ws/asr   -> 16kHz mono PCM16 frames in; {type:partial|final,text,ms} out
"""
import asyncio
import base64
import contextvars
import json
import logging
import os
import time

import websockets
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
log = logging.getLogger("stt")

MODEL_NAME = os.environ.get("STT_MODEL", "mistralai/Voxtral-Mini-4B-Realtime-2602")
VLLM_HTTP = os.environ.get("VLLM_HTTP_URL", "http://127.0.0.1:8091")
VLLM_RT = os.environ.get("VLLM_REALTIME_URL", "ws://127.0.0.1:8091/v1/realtime")
APPEND_BYTES = 4096  # vLLM realtime expects PCM16 16kHz base64 in ~4096-byte chunks

app = FastAPI(title="Tone STT — Voxtral Realtime (vLLM /v1/realtime bridge)")


@app.get("/health")
async def health():
    import urllib.request
    ok = False
    try:
        with urllib.request.urlopen(f"{VLLM_HTTP}/health", timeout=3) as r:
            ok = r.status == 200
    except Exception:
        ok = False
    return JSONResponse({"status": "ok" if ok else "loading", "model": MODEL_NAME, "engine_ok": ok},
                        status_code=200 if ok else 503)


@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    await ws.accept()
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/asr open from %s", client)
    t0 = time.monotonic()

    try:
        up = await websockets.connect(VLLM_RT, max_size=None, open_timeout=15)
    except Exception:
        log.exception("ws/asr %s could not connect to vLLM realtime", client)
        await ws.close()
        return

    relay = None
    try:
        # handshake: wait for session.created, then send session.update
        async def _await_created():
            async for raw in up:
                m = json.loads(raw)
                if m.get("type") == "session.created":
                    return
        await asyncio.wait_for(_await_created(), timeout=15)
        await up.send(json.dumps({"type": "session.update", "model": MODEL_NAME}))
        # initial commit = "start the transcription turn" signal (vLLM's example client sends
        # this BEFORE any audio). Without it the engine buffers audio but emits no deltas.
        await up.send(json.dumps({"type": "input_audio_buffer.commit"}))
        log.info("ws/asr %s vLLM realtime session open", client)

        # upstream -> Tone: relay transcripts
        async def _relay_transcripts():
            try:
                async for raw in up:
                    m = json.loads(raw)
                    t = m.get("type")
                    ms = round((time.monotonic() - t0) * 1000)
                    if t == "transcription.delta":
                        txt = m.get("delta", "")
                        if txt:
                            await ws.send_json({"type": "partial", "text": txt, "ms": ms})
                    elif t == "transcription.done":
                        txt = m.get("text", "")
                        log.info("ws/asr %s final: %r (%dms)", client, txt, ms)
                        await ws.send_json({"type": "final", "text": txt, "ms": ms})
                    elif t == "error":
                        log.error("ws/asr %s vLLM error: %s", client, m)
            except Exception:
                pass

        relay = asyncio.create_task(_relay_transcripts())

        # Tone -> vLLM: forward PCM as base64 append chunks
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data is None:
                if msg.get("text") == "eof":
                    await up.send(json.dumps({"type": "input_audio_buffer.commit", "final": True}))
                continue
            for i in range(0, len(data), APPEND_BYTES):
                chunk = data[i:i + APPEND_BYTES]
                await up.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(chunk).decode("ascii"),
                }))
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected", client)
    except Exception:
        log.exception("ws/asr %s bridge failed", client)
    finally:
        if relay is not None:
            relay.cancel()
        await up.close()
        log.info("ws/asr %s closed", client)
