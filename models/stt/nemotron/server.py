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

import asyncio
import contextvars
import logging
import os
import tempfile
import time

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

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

MODEL_NAME = os.environ.get("STT_MODEL", "nvidia/nemotron-speech-streaming-en-0.6b")
TARGET_SR = 16000
MAX_BUFFER_SEC = int(os.environ.get("STT_MAX_BUFFER_SEC", "30"))
STT_DECODE_MODE = os.environ.get("STT_DECODE_MODE", "streaming").lower()

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
    if STT_DECODE_MODE == "streaming":
        _setup_streaming(m)
        _set_streaming_decoding(m)
    else:
        _disable_cuda_graph_decoder(m)
    _model = m
    log.info("Model ready on %s (decode_mode=%s)", "cuda" if torch.cuda.is_available() else "cpu", STT_DECODE_MODE)
    return _model


def _set_streaming_decoding(m):
    try:
        from omegaconf import open_dict

        cfg = m.cfg.decoding
        with open_dict(cfg):
            if cfg.get("greedy") is None:
                cfg.greedy = {}
            cfg.greedy.use_cuda_graph_decoder = False
            cfg.greedy.loop_labels = True
        m.change_decoding_strategy(cfg)
        log.info("streaming decoding set: loop_labels=True, cuda_graph=False")
    except Exception as exc:  # noqa: BLE001
        log.warning("streaming decoding config failed: %s", exc)


def _setup_streaming(m):
    try:
        m.encoder.setup_streaming_params()
        cfg = getattr(m.encoder, "streaming_cfg", None)
        log.info("streaming setup ok | att_context_size=%s | streaming_cfg=%s",
                 getattr(m.encoder, "att_context_size", None), cfg)
    except Exception as exc:  # noqa: BLE001
        log.warning("streaming setup failed (model may not be cache-aware): %s", exc)


class _StreamSession:
    def __init__(self, model):
        self.m = model
        self.device = next(model.parameters()).device
        (self.cache_ch, self.cache_t, self.cache_ch_len) = model.encoder.get_initial_cache_state(batch_size=1)
        self.prev_hyp = None
        self.pred_out = None
        self.text = ""

    def feed(self, audio_f32, last=False):
        sig = torch.from_numpy(np.ascontiguousarray(audio_f32, dtype=np.float32)).to(self.device).unsqueeze(0)
        ln = torch.tensor([sig.shape[1]], device=self.device, dtype=torch.long)
        with torch.no_grad():
            feat, flen = self.m.preprocessor(input_signal=sig, length=ln)
            out = self.m.conformer_stream_step(
                processed_signal=feat,
                processed_signal_length=flen,
                cache_last_channel=self.cache_ch,
                cache_last_time=self.cache_t,
                cache_last_channel_len=self.cache_ch_len,
                keep_all_outputs=last,
                previous_hypotheses=self.prev_hyp,
                previous_pred_out=self.pred_out,
                drop_extra_pre_encoded=None,
                return_transcription=True,
            )
        self.pred_out, transcribed, self.cache_ch, self.cache_t, self.cache_ch_len, self.prev_hyp = out
        t = transcribed[0] if transcribed else ""
        self.text = (t.text if hasattr(t, "text") else t) or self.text
        return self.text


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


async def _ws_stream_loop(ws, model, client):
    loop = asyncio.get_running_loop()
    session = _StreamSession(model)
    chunk = bytearray()
    decodes = 0
    first = True
    STEP_MS = int(os.environ.get("STT_STEP_MS", "320"))
    STEP = max(1, int(TARGET_SR * 2 * STEP_MS / 1000))
    SILENCE_TICKS = int(os.environ.get("STT_SILENCE_TICKS", "2"))
    last_text = ""
    stable = 0
    t0 = time.monotonic()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                log.info("ws/asr %s disconnected (stream, %d decodes)", client, decodes)
                break
            data = msg.get("bytes")
            if data is None:
                if msg.get("text") == "eof":
                    audio = _pcm16_to_float(bytes(chunk))
                    text = await loop.run_in_executor(None, session.feed, audio, True) if audio.size else session.text
                    text = text or last_text
                    log.info("ws/asr %s final(eof): %r", client, text)
                    await ws.send_json({"type": "final", "text": text,
                                        "ms": round((time.monotonic() - t0) * 1000)})
                    await ws.close()
                    return
                continue
            chunk.extend(data)
            if len(chunk) >= STEP:
                audio = _pcm16_to_float(bytes(chunk))
                chunk = bytearray()
                d0 = time.monotonic()
                text = await loop.run_in_executor(None, session.feed, audio, False)
                decodes += 1
                dms = round((time.monotonic() - d0) * 1000)
                if text and text != last_text:
                    last_text = text
                    stable = 0
                    log.info("ws/asr %s partial #%d: %r (decode %dms, stream)", client, decodes, text, dms)
                    await ws.send_json({"type": "partial", "text": text,
                                        "ms": round((time.monotonic() - t0) * 1000), "ttf": first})
                    first = False
                elif last_text:
                    stable += 1
                    if stable >= SILENCE_TICKS:
                        # Emit a `final` at end-of-turn (interim partials never reach the LLM).
                        log.info("ws/asr %s end-of-turn final: %r", client, last_text)
                        await ws.send_json({"type": "final", "text": last_text,
                                            "ms": round((time.monotonic() - t0) * 1000)})
                        session = _StreamSession(model)
                        last_text = ""
                        stable = 0
                        first = True
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected (stream, WebSocketDisconnect)", client)
    except Exception as exc:  # noqa: BLE001
        log.exception("ws/asr %s stream transcription failed", client)
        try:
            await ws.send_json({"type": "error", "detail": str(exc)})
        except Exception:  # noqa: BLE001
            pass


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
async def asr(file: UploadFile = File(...), x_trace_id: str = Header(default="none")):
    _trace_ctx.set(x_trace_id)
    model = _load_model()
    raw = await file.read()
    log.info("/asr request: %s (%d bytes)", file.filename, len(raw))
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
        loop = asyncio.get_running_loop()
        d0 = time.monotonic()
        text = await loop.run_in_executor(None, _infer, model, data)
        log.info("/asr result: %r (decode %dms)", text, round((time.monotonic() - d0) * 1000))
        return {"text": text, "model": MODEL_NAME}
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
    _trace_ctx.set(ws.query_params.get("trace_id", "none"))
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "?"
    log.info("ws/asr open from %s (mode=%s)", client, STT_DECODE_MODE)
    model = _load_model()
    if STT_DECODE_MODE == "streaming":
        await _ws_stream_loop(ws, model, client)
        return
    loop = asyncio.get_running_loop()
    buf = bytearray()
    received = 0
    last_decode_at = 0
    decodes = 0
    DECODE_EVERY = TARGET_SR * 2
    MAX_BUFFER_BYTES = TARGET_SR * 2 * MAX_BUFFER_SEC

    t0 = time.monotonic()
    first = True
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                log.info("ws/asr %s disconnected (%d bytes, %d decodes)", client, received, decodes)
                break
            data = msg.get("bytes")
            if data is None:
                if msg.get("text") == "eof":
                    log.info("ws/asr %s eof (%d bytes, %.1fs buffered)", client, received,
                             len(buf) / (TARGET_SR * 2))
                    audio = _pcm16_to_float(bytes(buf))
                    d0 = time.monotonic()
                    text = await loop.run_in_executor(None, _infer, model, audio) if audio.size else ""
                    log.info("ws/asr %s final: %r (decode %dms)", client, text,
                             round((time.monotonic() - d0) * 1000))
                    await ws.send_json({"type": "final", "text": text,
                                        "ms": round((time.monotonic() - t0) * 1000)})
                    await ws.close()
                    return
                continue
            buf.extend(data)
            received += len(data)
            if len(buf) > MAX_BUFFER_BYTES:
                trimmed = len(buf) - MAX_BUFFER_BYTES
                del buf[:trimmed]
                log.debug("ws/asr %s trimmed %d bytes (cap %ds)", client, trimmed, MAX_BUFFER_SEC)
            if received - last_decode_at >= DECODE_EVERY:
                last_decode_at = received
                audio = _pcm16_to_float(bytes(buf))
                d0 = time.monotonic()
                text = await loop.run_in_executor(None, _infer, model, audio)
                decodes += 1
                log.info("ws/asr %s partial #%d: %r (decode %dms, %.1fs buffered)", client,
                         decodes, text, round((time.monotonic() - d0) * 1000),
                         len(buf) / (TARGET_SR * 2))
                await ws.send_json({"type": "partial", "text": text,
                                    "ms": round((time.monotonic() - t0) * 1000),
                                    "ttf": first})
                first = False
    except WebSocketDisconnect:
        log.info("ws/asr %s disconnected (WebSocketDisconnect)", client)
    except Exception as exc:  # noqa: BLE001
        log.exception("ws/asr %s transcription failed", client)
        try:
            await ws.send_json({"type": "error", "detail": str(exc)})
        except Exception:  # noqa: BLE001
            pass
