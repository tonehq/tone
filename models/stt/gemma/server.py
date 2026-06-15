"""
Tone STT — Google Gemma 4 E2B-it (native ASR) via transformers, offline + VAD-segmented.

Gemma 4 E2B-it is multimodal with native speech recognition, open (ungated, no HF token),
and runs in BF16 within ~3-4 GB of GPU via MatFormer/PLE offload — so it fits the 8 GB box
WITHOUT quantization (unlike Voxtral, whose 8-bit quant produced blank output). The model
transcribes a <=30s audio segment from a chat-template prompt; we segment a live call by
server-side energy VAD and transcribe per utterance, emitting a `final` per turn.

Same wire protocol as the nemotron server so Tone's nvidia_websocket client works unchanged:
  GET  /health    -> {status, model, cuda}
  GET  /selftest  -> transcribe a known clip (sanity check)
  WS   /ws/asr    -> 16kHz mono PCM16 frames; server emits {type: final, text, ms} per utterance
"""

import asyncio
import contextvars
import logging
import tempfile
import time

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from transformers import AutoModelForMultimodalLM, AutoProcessor

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

MODEL_NAME = "google/gemma-4-E2B-it"
TARGET_SR = 16000
MAX_NEW_TOKENS = 256
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
# On the 16GB GPU ($344 plan), BF16 (~10GB) fits FULLY on-GPU with no CPU offload and no
# quant -> fast AND correct. (On the old 8GB box: bf16 needed offload=slow, 8bit OOM'd,
# 4bit was fast but garbled — all moot with 16GB.)
QUANTIZE = "none"
PROMPT = ("You are a speech-to-text transcriber for an English-language phone call. "
          "Transcribe the audio verbatim into English text only. Do NOT translate and do NOT "
          "output any other language or script. If the audio is silent, noise, or unintelligible, "
          "output nothing at all. Output only the transcription, no extra words, no newlines.")

# energy-VAD segmentation
SPEECH_RMS = 0.012
SILENCE_HANG_MS = 600
MIN_SPEECH_MS = 300
MAX_UTT_S = 28  # Gemma caps audio at 30s — flush before that
# pipecat sends VAD-gated audio: utterances arrive as bursts with no audio in
# between (not silence frames). The primary end-of-utterance signal is a GAP —
# no audio frame for this long while a segment is buffered.
SILENCE_GAP_S = 0.6

app = FastAPI(title="Tone STT — Gemma 4 E2B (offline, VAD-segmented)")
_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model
    log.info("transformers Gemma ASR | torch %s | cuda=%s | model=%s",
             torch.__version__, torch.cuda.is_available(), MODEL_NAME)
    _processor = AutoProcessor.from_pretrained(MODEL_NAME)
    if QUANTIZE in ("8bit", "int8"):
        from transformers import BitsAndBytesConfig
        bnb = BitsAndBytesConfig(load_in_8bit=True)
        _model = AutoModelForMultimodalLM.from_pretrained(MODEL_NAME, quantization_config=bnb, device_map=DEVICE)
    elif QUANTIZE in ("4bit", "int4"):
        from transformers import BitsAndBytesConfig
        bnb = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
        )
        _model = AutoModelForMultimodalLM.from_pretrained(MODEL_NAME, quantization_config=bnb, device_map=DEVICE)
    else:
        # device_map=DEVICE (not "auto") forces the WHOLE model onto the GPU — on 16GB it
        # fits, so nothing offloads to CPU and inference stays fast.
        _model = AutoModelForMultimodalLM.from_pretrained(MODEL_NAME, dtype=torch.bfloat16, device_map=DEVICE)
    _model.eval()
    log.info("Model ready (quant=%s)", QUANTIZE)
    return _model


def _transcribe(audio_f32: np.ndarray) -> str:
    """Transcribe a <=30s 16kHz mono float32 segment via the chat-template audio path."""
    import soundfile as sf

    audio_f32 = np.ascontiguousarray(audio_f32, dtype=np.float32)
    # Telephony audio is often quiet -> low SNR -> hallucination. Boost toward a
    # consistent RMS level (capped so near-silence isn't amplified into noise).
    rms = float(np.sqrt(np.mean(audio_f32 ** 2))) if audio_f32.size else 0.0
    if rms > 1e-4:
        audio_f32 = np.clip(audio_f32 * min(0.1 / rms, 8.0), -1.0, 1.0)

    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, audio_f32, TARGET_SR)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "audio", "audio": f.name},
            ],
        }]
        inputs = _processor.apply_chat_template(
            messages, tokenize=True, return_dict=True, return_tensors="pt", add_generation_prompt=True,
        ).to(_model.device)
        input_len = inputs["input_ids"].shape[-1]
        with torch.no_grad():
            out = _model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
        text = _processor.decode(out[0][input_len:], skip_special_tokens=True)
    try:
        parsed = _processor.parse_response(text)
        if isinstance(parsed, str):
            text = parsed
    except Exception:  # noqa: BLE001
        pass
    return text.strip()


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
    """Transcribe a known clean clip (MLK) to verify the model produces text."""
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
                # gap in incoming audio after speech => end of utterance
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
            if len(seg) >= MAX_UTT_S * TARGET_SR * 2:  # hard cap (Gemma 30s limit)
                await _flush("maxlen")
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected", client)
    except Exception:  # noqa: BLE001
        log.exception("ws/asr %s failed", client)
