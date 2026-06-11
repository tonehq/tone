import asyncio
import contextvars
import io
import json
import logging
import os
import time
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from nano_qwen3tts_vllm.interface import Qwen3TTSInterface
from nano_qwen3tts_vllm.utils.speech_tokenizer_cudagraph import SpeechTokenizerCUDAGraph

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
TOKENIZER_NAME = os.environ.get("TTS_TOKENIZER", "Qwen/Qwen3-TTS-Tokenizer-12Hz")
DEFAULT_SPEAKER = os.environ.get("TTS_SPEAKER", "Ryan")
DEFAULT_LANGUAGE = os.environ.get("TTS_LANGUAGE", "English")
GPU_MEM_UTIL = float(os.environ.get("TTS_GPU_MEM_UTIL", "0.85"))
WARMUP_MAX_BATCH = int(os.environ.get("TTS_WARMUP_MAX_BATCH", "8"))

TARGET_SAMPLE_RATE = 24000
FIRST_CHUNK_SIZE = int(os.environ.get("TTS_FIRST_CHUNK_SIZE", "2"))
FIRST_CHUNK_COUNT = int(os.environ.get("TTS_FIRST_CHUNK_COUNT", "8"))
STREAMING_CHUNK_SIZE = int(os.environ.get("TTS_CHUNK_FRAMES", "4"))
_FIRST_CODES_THRESHOLD = FIRST_CHUNK_COUNT * FIRST_CHUNK_SIZE

SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]

_interface: Qwen3TTSInterface | None = None
_tokenizer: SpeechTokenizerCUDAGraph | None = None
_decode_queue: asyncio.Queue | None = None
_decode_worker_task: asyncio.Task | None = None


def _load_interface() -> Qwen3TTSInterface:
    global _interface
    if _interface is None:
        log.info("torch %s | cuda=%s | cap=%s", torch.__version__, torch.cuda.is_available(),
                 torch.cuda.get_device_capability() if torch.cuda.is_available() else "n/a")
        log.info("Loading %s via nano-qwen3tts-vllm ...", MODEL_NAME)
        _interface = Qwen3TTSInterface.from_pretrained(
            MODEL_NAME, enforce_eager=False, gpu_memory_utilization=GPU_MEM_UTIL,
        )
        log.info("Engine ready")
    return _interface


def _load_tokenizer() -> SpeechTokenizerCUDAGraph:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = SpeechTokenizerCUDAGraph(TOKENIZER_NAME, device="cuda:0" if torch.cuda.is_available() else "cpu")
    return _tokenizer


def _float_to_pcm16(wav: np.ndarray) -> bytes:
    clipped = np.clip(wav, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def _resample_to_24k(wav: np.ndarray, orig_sr: int) -> np.ndarray:
    if orig_sr == TARGET_SAMPLE_RATE:
        return wav
    n_orig = len(wav)
    n_new = int(round(n_orig * TARGET_SAMPLE_RATE / orig_sr))
    x_new = np.linspace(0.0, n_orig - 1, n_new)
    return np.interp(x_new, np.arange(n_orig), wav).astype(np.float32)


def _decode_trim_sync(audio_codes: list, left_context_frames: int) -> bytes:
    tokenizer = _load_tokenizer()
    with torch.inference_mode():
        wav_list, sr = tokenizer.decode([{"audio_codes": audio_codes}])
    wav = np.asarray(wav_list[0], dtype=np.float32)
    if left_context_frames > 0:
        spf = int(tokenizer.tokenizer.model.decoder.total_upsample)
        skip = left_context_frames * spf
        wav = wav[skip:] if skip < len(wav) else np.array([], dtype=np.float32)
    return _float_to_pcm16(_resample_to_24k(wav, sr))


async def _decode_worker_loop():
    loop = asyncio.get_running_loop()
    while True:
        item = await _decode_queue.get()
        if item is None:
            return
        batch = [item]
        while not _decode_queue.empty():
            nxt = _decode_queue.get_nowait()
            if nxt is None:
                await _decode_queue.put(None)
                break
            batch.append(nxt)

        def _do(reqs=batch):
            return [_decode_trim_sync(r["audio_codes"], r["left_context_frames"]) for r in reqs]

        try:
            results = await loop.run_in_executor(None, _do)
            for req, pcm in zip(batch, results):
                if not req["future"].done():
                    req["future"].set_result(pcm)
        except Exception as exc:
            for req in batch:
                if not req["future"].done():
                    req["future"].set_exception(exc)


async def _decode_batched(audio_codes: list, left_context_frames: int) -> bytes:
    future = asyncio.get_running_loop().create_future()
    await _decode_queue.put({
        "audio_codes": audio_codes,
        "left_context_frames": left_context_frames,
        "future": future,
    })
    return await future


async def synthesize_stream(text: str, speaker: str, language: str):
    interface = _load_interface()
    gen = interface.generate_custom_voice_async(
        text="..." + text, language=language, speaker=speaker,
    )
    codes_queue: asyncio.Queue = asyncio.Queue()

    async def producer():
        codes: list = []
        try:
            async for code in gen:
                codes.append(code)
                n = len(codes)
                if n <= _FIRST_CODES_THRESHOLD:
                    if n % FIRST_CHUNK_SIZE == 0:
                        await codes_queue.put(list(codes))
                elif n % STREAMING_CHUNK_SIZE == 0:
                    await codes_queue.put(list(codes))
            if codes:
                n = len(codes)
                if (n <= _FIRST_CODES_THRESHOLD and n % FIRST_CHUNK_SIZE != 0) or (
                    n > _FIRST_CODES_THRESHOLD and n % STREAMING_CHUNK_SIZE != 0
                ):
                    await codes_queue.put(list(codes))
        finally:
            await codes_queue.put(None)

    producer_task = asyncio.create_task(producer())
    prev_pos = 0
    try:
        while True:
            item = await codes_queue.get()
            if item is None:
                break
            if len(item) <= prev_pos:
                continue
            pcm = await _decode_batched(item, prev_pos)
            prev_pos = len(item)
            if pcm:
                yield pcm
                await asyncio.sleep(0)
        if producer_task.done() and (exc := producer_task.exception()):
            raise exc
    finally:
        producer_task.cancel()
        try:
            await producer_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await gen.aclose()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _decode_queue, _decode_worker_task
    interface = _load_interface()
    _load_tokenizer()
    await interface.start_zmq_tasks()
    _decode_queue = asyncio.Queue()
    _decode_worker_task = asyncio.create_task(_decode_worker_loop())

    async def _warm_one(i: int):
        try:
            async for _ in synthesize_stream("Hello.", DEFAULT_SPEAKER, DEFAULT_LANGUAGE):
                pass
        except Exception:
            log.exception("warmup synth %d failed (continuing)", i)

    t0 = time.monotonic()
    batch = 1
    while batch <= WARMUP_MAX_BATCH:
        await asyncio.gather(*(_warm_one(i) for i in range(batch)))
        batch *= 2
    log.info("warmup ramp (1..%d) done in %dms", WARMUP_MAX_BATCH, round((time.monotonic() - t0) * 1000))

    yield

    if _decode_queue is not None:
        await _decode_queue.put(None)
    if _decode_worker_task is not None:
        await _decode_worker_task
    try:
        await interface.stop_zmq_tasks()
    except Exception:
        log.exception("stop_zmq_tasks failed during shutdown")


app = FastAPI(title="Tone TTS — Qwen3-TTS 0.6B CustomVoice (nano-qwen3tts-vllm)", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok" if _interface is not None else "loading",
        "model": MODEL_NAME,
        "engine": "nano-qwen3tts-vllm",
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
    d0 = time.monotonic()
    chunks = [pcm async for pcm in synthesize_stream(req.text, speaker, language)]
    pcm_all = b"".join(chunks)
    wav = np.frombuffer(pcm_all, dtype="<i2").astype(np.float32) / 32767.0
    log.info("/tts %r speaker=%s -> %.2fs audio (synth %dms)", req.text[:60], speaker,
             len(wav) / TARGET_SAMPLE_RATE, round((time.monotonic() - d0) * 1000))
    buf = io.BytesIO()
    sf.write(buf, wav, TARGET_SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return Response(content=buf.getvalue(), media_type="audio/wav")


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
            n_chunks = 0
            first_ms = 0
            try:
                async for pcm in synthesize_stream(text, speaker, language):
                    if n_chunks == 0:
                        first_ms = round((time.monotonic() - t0) * 1000)
                        await ws.send_json({"type": "start", "sample_rate": TARGET_SAMPLE_RATE})
                    n_chunks += 1
                    await ws.send_bytes(pcm)
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                log.exception("ws/tts %s synth failed", client)
                await ws.send_json({"type": "error", "detail": str(exc)})
                continue
            total_ms = round((time.monotonic() - t0) * 1000)
            await ws.send_json({"type": "end", "ms": total_ms})
            log.info("ws/tts %s %r speaker=%s -> %d chunks @ %dHz (first %dms, total %dms)",
                     client, text[:60], speaker, n_chunks, TARGET_SAMPLE_RATE, first_ms, total_ms)
    except WebSocketDisconnect:
        log.info("ws/tts %s disconnected (WebSocketDisconnect)", client)
    except Exception:
        log.exception("ws/tts %s loop failed", client)
        try:
            await ws.send_json({"type": "error", "detail": "internal error"})
        except Exception:
            pass
