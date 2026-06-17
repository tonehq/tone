import contextvars
import io
import logging
import os
import tempfile
import time

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

import nemo.collections.asr as nemo_asr

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

MODEL_NAME = os.environ.get("STT_MODEL", "nvidia/parakeet-tdt-0.6b-v2")
TARGET_SR = 16000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="Tone STT — NVIDIA Parakeet")
_model = None


def _disable_cuda_graph_decoder(m):
    try:
        cfg = m.cfg.decoding
        if hasattr(cfg, "greedy") and hasattr(cfg.greedy, "use_cuda_graph_decoder"):
            cfg.greedy.use_cuda_graph_decoder = False
        m.change_decoding_strategy(cfg)
        log.info("cuda-graph decoder disabled")
    except Exception as exc:  # noqa: BLE001
        log.warning("could not disable cuda-graph decoder: %s", exc)


def _load_model():
    global _model
    if _model is not None:
        return _model
    log.info("NeMo Parakeet | torch %s | cuda=%s | model=%s", torch.__version__, torch.cuda.is_available(), MODEL_NAME)
    m = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME, map_location="cpu")
    if torch.cuda.is_available():
        m = m.to("cuda")
    m.eval()
    _disable_cuda_graph_decoder(m)
    _model = m
    log.info("Parakeet ready on %s", DEVICE)
    return _model


def _transcribe_wav(wav_bytes: bytes) -> str:
    audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    audio = np.ascontiguousarray(audio, dtype=np.float32)
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, audio, TARGET_SR)
        with torch.no_grad():
            out = _model.transcribe([f.name], verbose=False)
    h = out[0] if out else ""
    text = h.text if hasattr(h, "text") else h
    return (text or "").strip()


@app.on_event("startup")
def _warmup():
    _load_model()


@app.get("/health")
def health():
    return {"status": "ok" if _model is not None else "loading", "model": MODEL_NAME, "cuda": torch.cuda.is_available()}


@app.get("/selftest")
async def selftest():
    import urllib.request

    import librosa

    _load_model()
    raw = urllib.request.urlopen(
        "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/mlk.flac", timeout=30).read()
    audio, sr = sf.read(io.BytesIO(raw), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), TARGET_SR, format="WAV")
    d0 = time.monotonic()
    text = await run_in_threadpool(_transcribe_wav, buf.getvalue())
    return {"transcript": text, "len": len(text), "ms": round((time.monotonic() - d0) * 1000)}


@app.post("/asr")
async def asr(request: Request):
    _trace_ctx.set(request.query_params.get("trace_id", "none"))
    _load_model()
    wav = await request.body()
    if not wav:
        return {"text": "", "ms": 0, "model": MODEL_NAME}
    d0 = time.monotonic()
    try:
        text = await run_in_threadpool(_transcribe_wav, wav)
    except Exception:  # noqa: BLE001
        log.exception("/asr transcription failed")
        return {"text": "", "ms": round((time.monotonic() - d0) * 1000), "model": MODEL_NAME}
    ms = round((time.monotonic() - d0) * 1000)
    log.info("/asr -> %r (%dms)", text, ms)
    return {"text": text, "ms": ms, "model": MODEL_NAME}
