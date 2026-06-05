"""
Tone STT — nvidia/nemotron-speech-streaming-en-0.6b via NeMo + FastAPI.

Public model (NVIDIA Open Model License), pulled from HuggingFace — no NGC key.

IMPORTANT — vGPU workaround:
  This runs on an NVIDIA A16 *vGPU* slice. `model.transcribe()` uses NeMo's
  Lhotse dataloader with pin_memory=True; pinned-memory allocation
  (cudaHostRegister) is unsupported on the vGPU and corrupts the CUDA context,
  making the next GPU op fail with "CUDA driver error: operation not supported".
  We therefore bypass transcribe() entirely and run preprocessor -> encoder ->
  RNNT decode by hand on a CUDA tensor (verified working on this exact vGPU).
  We also disable the CUDA-graph decoder (the vGPU rejects graph capture).

Endpoints: GET /health, POST /asr (batch). Streaming /ws/asr is the next step.
"""

import logging
import os
import tempfile

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

import nemo.collections.asr as nemo_asr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stt")

MODEL_NAME = os.environ.get("STT_MODEL", "nvidia/nemotron-speech-streaming-en-0.6b")
TARGET_SR = 16000

app = FastAPI(title="Tone STT — Nemotron Streaming 0.6B")
_model = None


def _disable_cuda_graph_decoder(m):
    # The vGPU's CUDA 12.4 driver can't do CUDA-graph capture; force the plain
    # decode path so the greedy RNNT decoder doesn't try graphs.
    try:
        from omegaconf import open_dict

        cfg = m.cfg.decoding
        with open_dict(cfg):
            if cfg.get("greedy") is None:
                cfg.greedy = {}
            cfg.greedy.use_cuda_graph_decoder = False
            cfg.greedy.loop_labels = False
        m.change_decoding_strategy(cfg)
        log.info("CUDA-graph decoder disabled (vGPU workaround)")
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not disable cuda-graph decoder: %s", exc)


def _load_model():
    global _model
    if _model is not None:
        return _model
    log.info("NeMo %s | torch %s | cuda=%s | cap=%s",
             getattr(__import__("nemo"), "__version__", "?"), torch.__version__,
             torch.cuda.is_available(),
             torch.cuda.get_device_capability() if torch.cuda.is_available() else "n/a")
    log.info("Loading %s on CPU ...", MODEL_NAME)
    m = nemo_asr.models.ASRModel.from_pretrained(model_name=MODEL_NAME, map_location="cpu")
    if torch.cuda.is_available():
        log.info("Moving model to CUDA ...")
        m = m.to("cuda")
    m.eval()
    _disable_cuda_graph_decoder(m)
    _model = m
    log.info("Model ready on %s", "cuda" if torch.cuda.is_available() else "cpu")
    return _model


def _decode_text(hyps):
    # rnnt_decoder_predictions_tensor may return a list, or a (best, all) tuple,
    # of Hypothesis objects (or plain strings on older NeMo).
    if isinstance(hyps, tuple):
        hyps = hyps[0]
    h = hyps[0] if isinstance(hyps, (list, tuple)) else hyps
    return h.text if hasattr(h, "text") else h


def _infer(model, audio):
    """audio: 1-D float32 numpy @ 16 kHz -> transcript str. Manual path, no dataloader."""
    device = next(model.parameters()).device
    audio = np.ascontiguousarray(audio, dtype=np.float32)
    sig = torch.from_numpy(audio).to(device=device).unsqueeze(0)
    ln = torch.tensor([sig.shape[1]], device=device, dtype=torch.long)
    with torch.no_grad():
        feat, flen = model.preprocessor(input_signal=sig, length=ln)
        enc, enc_len = model.encoder(audio_signal=feat, length=flen)
        hyps = model.decoding.rnnt_decoder_predictions_tensor(
            enc, enc_len, return_hypotheses=False
        )
    return _decode_text(hyps)


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


@app.post("/asr")
async def asr(file: UploadFile = File(...)):
    model = _load_model()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(raw)
        path = tmp.name
    try:
        data, sr = sf.read(path, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != TARGET_SR:
            import torchaudio

            t = torch.from_numpy(np.ascontiguousarray(data)).unsqueeze(0)
            t = torchaudio.functional.resample(t, sr, TARGET_SR)
            data = t.squeeze(0).numpy()
        return {"text": _infer(model, data), "model": MODEL_NAME}
    except Exception as exc:  # noqa: BLE001
        log.exception("transcription failed")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        os.unlink(path)


def _pcm16_to_float(buf: bytes) -> np.ndarray:
    return np.frombuffer(buf, dtype="<i2").astype(np.float32) / 32768.0


@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    """
    v1 buffered streaming. Client sends raw 16 kHz mono PCM16-LE binary frames,
    then the text "eof" to finish. Server emits {type: partial|final, text, ms}.
    Re-decodes the whole buffer each tick (fine for short utterances) — true
    cache-aware incremental decoding is the next iteration.
    """
    await ws.accept()
    model = _load_model()
    buf = bytearray()
    last_len = 0
    DECODE_EVERY = TARGET_SR * 2  # ~0.5 s of new audio (int16 -> 2 bytes/sample)
    import time

    t0 = time.monotonic()
    first = True
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data is None:
                if msg.get("text") == "eof":
                    audio = _pcm16_to_float(bytes(buf))
                    text = _infer(model, audio) if audio.size else ""
                    await ws.send_json({"type": "final", "text": text,
                                        "ms": round((time.monotonic() - t0) * 1000)})
                    await ws.close()
                    return
                continue
            buf.extend(data)
            if len(buf) - last_len >= DECODE_EVERY:
                last_len = len(buf)
                audio = _pcm16_to_float(bytes(buf))
                text = _infer(model, audio)
                await ws.send_json({"type": "partial", "text": text,
                                    "ms": round((time.monotonic() - t0) * 1000),
                                    "ttf": first})
                first = False
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        log.exception("ws transcription failed")
        try:
            await ws.send_json({"type": "error", "detail": str(exc)})
        except Exception:  # noqa: BLE001
            pass
