"""
Tone STT — Mistral Voxtral-Mini-4B-Realtime via transformers (offline, VAD-segmented).

Research finding: the high-level chunk-streaming path (generate with an input_features
generator) does NOT work reliably at transformers 5.12 / mistral_common 1.11.3 — it needs
exact left/right padding (the model prompt is BOS + 32 left-pad + 6 delay = 39 tokens) and
true token-streaming requires low-level forward_one decoding. The correct working path is
OFFLINE transcription (is_streaming=False) of the full audio, which the processor pads
internally. For a live call we segment by server-side energy VAD and transcribe per
utterance, emitting a `final` per turn.

Same wire protocol as the nemotron server so Tone's nvidia_websocket client works unchanged:
  GET  /health    -> {status, model, cuda}
  GET  /selftest  -> offline-transcribe a known clip (sanity check)
  WS   /ws/asr    -> 16kHz mono PCM16 frames; server emits {type: final, text, ms} per utterance
"""

import asyncio
import contextvars
import logging
import time

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from transformers import VoxtralRealtimeForConditionalGeneration, VoxtralRealtimeProcessor

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
QUANTIZE = "none"
COMPUTE_DTYPE = torch.bfloat16
MAX_NEW_TOKENS = 256

# energy-VAD segmentation
SPEECH_RMS = 0.012
SILENCE_HANG_MS = 600
MIN_SPEECH_MS = 300

app = FastAPI(title="Tone STT — Voxtral (offline, VAD-segmented)")
_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model
    log.info("transformers VoxtralRealtime (offline) | torch %s | cuda=%s | model=%s | quant=%s",
             torch.__version__, torch.cuda.is_available(), MODEL_NAME, QUANTIZE)
    _processor = VoxtralRealtimeProcessor.from_pretrained(MODEL_NAME)
    load_kwargs = {}
    if QUANTIZE in ("8bit", "int8"):
        from transformers import BitsAndBytesConfig
        load_kwargs["device_map"] = DEVICE
        load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    elif QUANTIZE in ("4bit", "int4"):
        from transformers import BitsAndBytesConfig
        load_kwargs["device_map"] = DEVICE
        load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
    else:
        # BF16 doesn't fit 8GB — let accelerate offload the overflow to CPU RAM so we can
        # test whether BF16 transcribes (isolating quant vs. the generate call).
        load_kwargs["device_map"] = "auto"
        load_kwargs["torch_dtype"] = COMPUTE_DTYPE
        load_kwargs["low_cpu_mem_usage"] = True
    _model = VoxtralRealtimeForConditionalGeneration.from_pretrained(MODEL_NAME, **load_kwargs)
    _model.eval()
    log.info("Model ready on %s (quant=%s, compute_dtype=%s)", DEVICE, QUANTIZE, COMPUTE_DTYPE)
    return _model


def _transcribe_offline(audio_f32: np.ndarray) -> str:
    """Full-clip offline transcription (is_streaming=False -> processor pads internally)."""
    inputs = _processor(
        np.ascontiguousarray(audio_f32, dtype=np.float32),
        is_streaming=False,
        is_first_audio_chunk=True,
        return_tensors="pt",
    )
    inputs.to(_model.device, dtype=COMPUTE_DTYPE)
    with torch.no_grad():
        gen = _model.generate(
            input_ids=inputs.input_ids,
            input_features=inputs.input_features,
            num_delay_tokens=inputs.num_delay_tokens,
            max_new_tokens=MAX_NEW_TOKENS,
        )
    text = _processor.batch_decode(gen[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return (text[0] if text else "").strip()


def _pcm16_to_float(buf: bytes) -> np.ndarray:
    return np.frombuffer(buf, dtype="<i2").astype(np.float32) / 32768.0


@app.on_event("startup")
def _warmup():
    _load_model()


@app.get("/health")
def health():
    return {"status": "ok" if _model is not None else "loading", "model": MODEL_NAME, "cuda": torch.cuda.is_available()}


@app.get("/selftest")
def selftest():
    """Offline-transcribe a known clean clip (MLK) to verify the model produces text."""
    import io
    import urllib.request

    import soundfile as sf

    _load_model()
    raw = urllib.request.urlopen(
        "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/mlk.flac", timeout=30).read()
    audio, sr = sf.read(io.BytesIO(raw), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    d0 = time.monotonic()
    text = _transcribe_offline(audio)
    return {"transcript": text, "len": len(text), "ms": round((time.monotonic() - d0) * 1000)}


@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    """Client streams 16kHz mono PCM16 frames. Server detects utterance boundaries via
    energy VAD and emits {type: final, text, ms} per utterance (offline transcription)."""
    await ws.accept()
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/asr open from %s", client)
    _load_model()
    loop = asyncio.get_running_loop()

    seg = bytearray()
    in_speech = False
    sil_ms = 0.0
    speech_ms = 0.0
    t0 = time.monotonic()

    async def _flush(reason):
        nonlocal seg, in_speech, sil_ms, speech_ms
        if speech_ms < MIN_SPEECH_MS or not seg:
            seg = bytearray(); in_speech = False; sil_ms = 0.0; speech_ms = 0.0
            return
        audio = _pcm16_to_float(bytes(seg))
        seg = bytearray(); in_speech = False; sil_ms = 0.0; speech_ms = 0.0
        d0 = time.monotonic()
        try:
            text = await loop.run_in_executor(None, _transcribe_offline, audio)
        except Exception as exc:  # noqa: BLE001
            log.exception("ws/asr %s transcription failed", client)
            return
        log.info("ws/asr %s final (%s, %.1fs audio): %r (%dms)", client, reason,
                 len(audio) / TARGET_SR, text, round((time.monotonic() - d0) * 1000))
        if text:
            try:
                await ws.send_json({"type": "final", "text": text, "ms": round((time.monotonic() - t0) * 1000)})
            except Exception:  # noqa: BLE001
                pass

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                await _flush("disconnect")
                break
            data = msg.get("bytes")
            if data is None:
                if msg.get("text") == "eof":
                    await _flush("eof")
                    break
                continue
            seg.extend(data)
            frame = _pcm16_to_float(data)
            if frame.size == 0:
                continue
            dur_ms = frame.size / TARGET_SR * 1000.0
            rms = float(np.sqrt(np.mean(frame ** 2)))
            if rms >= SPEECH_RMS:
                in_speech = True
                sil_ms = 0.0
                speech_ms += dur_ms
            elif in_speech:
                sil_ms += dur_ms
                if sil_ms >= SILENCE_HANG_MS:
                    await _flush("silence")
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected", client)
    except Exception as exc:  # noqa: BLE001
        log.exception("ws/asr %s failed", client)
