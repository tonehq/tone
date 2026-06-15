"""
Tone STT — Mistral Voxtral-Mini-4B-Realtime via transformers (TRUE streaming, no vLLM).

Uses the native VoxtralRealtime streaming API (transformers >= 5.2.0): audio is fed
chunk-by-chunk into the causal encoder and transcription tokens are emitted as audio
arrives — NOT the Whisper-style buffered re-decode. Reference: HF voxtral_realtime docs.

Exposes the SAME wire protocol as the nemotron STT server so Tone's nvidia_websocket
client works unchanged:
  GET  /health   -> {status, model, cuda}
  WS   /ws/asr   -> client sends 16kHz mono PCM16-LE frames then text "eof";
                    server emits {type: partial|final, text, ms} (+ ttf on first partial)

NOTE: the VoxtralRealtime streaming API is marked experimental by HF; validate the
processor attribute names against the installed transformers version.
"""

import asyncio
import contextvars
import logging
import os
import queue
import threading
import time

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from transformers import (
    TextIteratorStreamer,
    VoxtralRealtimeForConditionalGeneration,
    VoxtralRealtimeProcessor,
)

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

MODEL_NAME = "mistralai/Voxtral-Mini-4B-Realtime-2602"
TARGET_SR = 16000
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
QUANTIZE = "8bit"   # "" = bf16 (needs 16GB GPU); "8bit" ~4.4GB fits 8GB; "4bit" ~2.5GB
COMPUTE_DTYPE = torch.float16 if QUANTIZE in ("8bit", "int8") else torch.bfloat16

app = FastAPI(title="Tone STT — Voxtral Realtime (transformers streaming)")
_model = None
_processor = None
_DONE = object()


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model
    log.info("transformers VoxtralRealtime | torch %s | cuda=%s | model=%s",
             torch.__version__, torch.cuda.is_available(), MODEL_NAME)
    _processor = VoxtralRealtimeProcessor.from_pretrained(MODEL_NAME)
    load_kwargs = {"device_map": DEVICE}
    if QUANTIZE in ("8bit", "int8"):
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    elif QUANTIZE in ("4bit", "int4"):
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
    else:
        load_kwargs["torch_dtype"] = COMPUTE_DTYPE
    _model = VoxtralRealtimeForConditionalGeneration.from_pretrained(MODEL_NAME, **load_kwargs)
    _model.eval()
    log.info("Model ready on %s (quantize=%s, compute_dtype=%s)", DEVICE, QUANTIZE or "none", COMPUTE_DTYPE)
    return _model


def _proc(audio_f32: np.ndarray, first: bool):
    """Run the processor for one audio chunk -> input tensors on device."""
    out = _processor(
        np.ascontiguousarray(audio_f32, dtype=np.float32),
        is_streaming=True,
        is_first_audio_chunk=first,
        return_tensors="pt",
    )
    out.to(_model.device, dtype=COMPUTE_DTYPE)
    return out


def _pcm16_to_float(buf: bytes) -> np.ndarray:
    return np.frombuffer(buf, dtype="<i2").astype(np.float32) / 32768.0


@app.on_event("startup")
def _warmup():
    _load_model()


@app.get("/health")
def health():
    return {
        "status": "ok" if _model is not None else "loading",
        "model": MODEL_NAME,
        "cuda": torch.cuda.is_available(),
    }


@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    """TRUE streaming. Client streams 16kHz mono PCM16-LE frames then text 'eof'.
    Audio is sliced into the model's native chunks and fed to the causal encoder as
    it arrives; transcription tokens are streamed out as {type: partial|final, ...}."""
    await ws.accept()
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/asr open from %s", client)
    _load_model()
    loop = asyncio.get_running_loop()

    feat_q: "queue.Queue" = queue.Queue()      # input_features tensors -> generate thread
    streamer = TextIteratorStreamer(_processor.tokenizer, skip_special_tokens=True,
                                    clean_up_tokenization_spaces=True)

    # native chunk geometry (from the processor)
    hop = _processor.feature_extractor.hop_length
    win = _processor.feature_extractor.win_length
    N_FIRST = _processor.num_samples_first_audio_chunk
    STEP = _processor.num_samples_per_audio_chunk

    state = {"started": False, "mel_idx": 0, "start_idx": 0, "full": "", "t0": time.monotonic(), "first_emit": True}

    def _feat_generator():
        while True:
            item = feat_q.get()
            if item is _DONE:
                return
            yield item

    async def _send_loop():
        it = iter(streamer)
        while True:
            chunk = await loop.run_in_executor(None, lambda: next(it, _DONE))
            if chunk is _DONE:
                break
            state["full"] += chunk
            try:
                await ws.send_json({"type": "partial", "text": state["full"],
                                    "ms": round((time.monotonic() - state["t0"]) * 1000),
                                    "ttf": state["first_emit"]})
                state["first_emit"] = False
            except Exception:  # noqa: BLE001
                return
        log.info("ws/asr %s final: %r", client, state["full"])
        try:
            await ws.send_json({"type": "final", "text": state["full"],
                                "ms": round((time.monotonic() - state["t0"]) * 1000)})
            await ws.close()
        except Exception:  # noqa: BLE001
            pass

    raw = bytearray()
    send_task = None
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                log.info("ws/asr %s disconnected", client)
                break
            data = msg.get("bytes")
            if data is None:
                if msg.get("text") == "eof":
                    feat_q.put(_DONE)
                    break
                continue
            raw.extend(data)
            audio = _pcm16_to_float(bytes(raw))

            if not state["started"]:
                if audio.shape[0] < N_FIRST:
                    continue
                first = await loop.run_in_executor(None, _proc, audio[:N_FIRST], True)
                feat_q.put(first.input_features)
                kwargs = {
                    "input_ids": first.input_ids,
                    "input_features": _feat_generator(),
                    "num_delay_tokens": first.num_delay_tokens,
                    "streamer": streamer,
                }
                threading.Thread(target=_model.generate, kwargs=kwargs, daemon=True).start()
                send_task = asyncio.create_task(_send_loop())
                state["started"] = True
                state["mel_idx"] = _processor.num_mel_frames_first_audio_chunk
                state["start_idx"] = state["mel_idx"] * hop - win // 2
                log.info("ws/asr %s streaming started", client)
            else:
                while state["start_idx"] + STEP <= audio.shape[0]:
                    s = state["start_idx"]
                    feats = await loop.run_in_executor(None, _proc, audio[s:s + STEP], False)
                    feat_q.put(feats.input_features)
                    state["mel_idx"] += _processor.audio_length_per_tok
                    state["start_idx"] = state["mel_idx"] * hop - win // 2
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected (WebSocketDisconnect)", client)
    except Exception as exc:  # noqa: BLE001
        log.exception("ws/asr %s failed", client)
        try:
            await ws.send_json({"type": "error", "detail": str(exc)})
        except Exception:  # noqa: BLE001
            pass
    finally:
        feat_q.put(_DONE)
        if send_task is not None:
            try:
                await asyncio.wait_for(send_task, timeout=30)
            except Exception:  # noqa: BLE001
                pass
