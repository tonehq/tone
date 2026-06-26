import asyncio
import contextvars
import logging
import os
import time

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

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

MODEL_NAME = os.environ.get("STT_MODEL", "ibm-granite/granite-speech-3.3-2b")
TARGET_SR = 16000
MAX_NEW_TOKENS = 200
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
SYSTEM_PROMPT = ("Knowledge Cutoff Date: April 2024.\nYou are Granite, developed by IBM. "
                 "You are a helpful AI assistant.")
USER_PROMPT = "<|audio|>can you transcribe the speech into a written format?"

SPEECH_RMS = 0.012
SILENCE_HANG_MS = 600
MIN_SPEECH_MS = 300
MAX_UTT_S = 28
SILENCE_GAP_S = 0.6

app = FastAPI(title="Tone STT — IBM Granite Speech 3.3")
_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model
    log.info("transformers Granite Speech ASR | torch %s | cuda=%s | model=%s",
             torch.__version__, torch.cuda.is_available(), MODEL_NAME)
    _processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
    _model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_NAME, dtype=torch.bfloat16, device_map=DEVICE, trust_remote_code=True,
    )
    _model.eval()
    log.info("Granite Speech ready on %s", DEVICE)
    return _model


def _transcribe(audio_f32: np.ndarray) -> str:
    audio_f32 = np.ascontiguousarray(audio_f32, dtype=np.float32)
    rms = float(np.sqrt(np.mean(audio_f32 ** 2))) if audio_f32.size else 0.0
    if rms > 1e-4:
        audio_f32 = np.clip(audio_f32 * min(0.1 / rms, 8.0), -1.0, 1.0)

    wav = torch.from_numpy(audio_f32).unsqueeze(0)
    chat = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]
    text = _processor.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    inputs = _processor(text, wav, device=DEVICE, return_tensors="pt").to(DEVICE)
    input_len = inputs["input_ids"].shape[-1]
    with torch.no_grad():
        out = _model.generate(
            **inputs, max_new_tokens=MAX_NEW_TOKENS, num_beams=1, do_sample=False,
            pad_token_id=_processor.tokenizer.pad_token_id,
        )
    new_tokens = out[0, input_len:]
    return _processor.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


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
    import io
    import urllib.request

    import librosa
    import soundfile as sf

    _load_model()
    raw = urllib.request.urlopen(
        "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/mlk.flac", timeout=30).read()
    audio, sr = sf.read(io.BytesIO(raw), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    d0 = time.monotonic()
    text = _transcribe(audio)
    return {"transcript": text, "len": len(text), "ms": round((time.monotonic() - d0) * 1000)}


@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
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
            text = await loop.run_in_executor(None, _transcribe, audio)
        except Exception:  # noqa: BLE001
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
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=SILENCE_GAP_S)
            except asyncio.TimeoutError:
                await _flush("gap")
                continue
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
            if len(seg) >= MAX_UTT_S * TARGET_SR * 2:
                await _flush("maxlen")
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected", client)
    except Exception:  # noqa: BLE001
        log.exception("ws/asr %s failed", client)
