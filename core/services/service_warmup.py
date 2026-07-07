import importlib
import time
from typing import Any, Optional

from loguru import logger
from pipecat.audio.filters.rnnoise_filter import RNNoiseFilter
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

_silero_vad_analyzer: Optional[Any] = None
_silero_vad_analyzer_phone: Optional[Any] = None
_smart_turn_analyzer: Optional[Any] = None
_rnnoise_available: bool = False
_warmed_up: bool = False


_MODULES_TO_WARM = [
    "pipecat.audio.turn.smart_turn.base_smart_turn",
    "pipecat.audio.turn.smart_turn.local_smart_turn_v3",
    "pipecat.audio.vad.silero",
    "pipecat.frames.frames",
    "pipecat.pipeline.pipeline",
    "pipecat.pipeline.runner",
    "pipecat.pipeline.task",
    "pipecat.processors.aggregators.llm_context",
    "pipecat.processors.aggregators.llm_response_universal",
    "pipecat.processors.aggregators.llm_text_processor",
    "pipecat.processors.audio.audio_buffer_processor",
    "pipecat.processors.frame_processor",
    "pipecat.processors.frameworks.rtvi",
    "pipecat.serializers.twilio",
    "pipecat.services.anthropic.llm",
    "pipecat.services.cartesia.stt",
    "pipecat.services.cartesia.tts",
    "pipecat.services.deepgram.stt",
    "pipecat.services.deepgram.tts",
    "pipecat.services.elevenlabs.tts",
    "pipecat.services.google.llm",
    "pipecat.services.groq.llm",
    "pipecat.services.nvidia.stt",
    "pipecat.services.openai.llm",
    "pipecat.services.openai.stt",
    "pipecat.services.openai.tts",
    "pipecat.services.rime.tts",
    "pipecat.transports.websocket.fastapi",
    "pipecat.turns.user_stop",
    "pipecat.turns.user_turn_strategies",
    "pydub",
    "pydub.audio_segment",
    "core.processors.metrics_collector",
]


def _import_pipecat_services() -> None:
    succeeded = 0
    for mod_name in _MODULES_TO_WARM:
        try:
            importlib.import_module(mod_name)
            succeeded += 1
        except Exception as e:
            logger.debug(f"[warmup] could not import {mod_name}: {e}")
    logger.info(f"[warmup] preloaded {succeeded}/{len(_MODULES_TO_WARM)} pipecat modules")


def _preload_silero_vad() -> Optional[Any]:
    global _silero_vad_analyzer
    if _silero_vad_analyzer is not None:
        return _silero_vad_analyzer
    try:
        _silero_vad_analyzer = SileroVADAnalyzer(
            params=VADParams(
                confidence=0.7,
                start_secs=0.4,
                stop_secs=0.4,
                min_volume=0.4,
            )
        )
        return _silero_vad_analyzer
    except Exception as e:
        logger.warning(f"[warmup] Silero VAD preload failed: {e}")
        return None


def _preload_silero_vad_phone() -> Optional[Any]:
    global _silero_vad_analyzer_phone
    if _silero_vad_analyzer_phone is not None:
        return _silero_vad_analyzer_phone
    try:
        _silero_vad_analyzer_phone = SileroVADAnalyzer(
            params=VADParams(
                confidence=0.7,
                start_secs=0.2,
                stop_secs=0.4,
                min_volume=0.4,
            )
        )
        return _silero_vad_analyzer_phone
    except Exception as e:
        logger.warning(f"[warmup] Silero VAD (phone) preload failed: {e}")
        return None


def _preload_smart_turn() -> Optional[Any]:
    global _smart_turn_analyzer
    if _smart_turn_analyzer is not None:
        return _smart_turn_analyzer
    try:
        _smart_turn_analyzer = LocalSmartTurnAnalyzerV3(
            confidence_threshold=0.5,
            params=SmartTurnParams(stop_secs=0.4),
        )
        return _smart_turn_analyzer
    except Exception as e:
        logger.warning(f"[warmup] Smart Turn preload failed: {e}")
        return None


def _probe_rnnoise() -> bool:
    global _rnnoise_available
    try:
        from pyrnnoise import RNNoise
        probe = RNNoise(sample_rate=48000)
        del probe
        _rnnoise_available = True
        return True
    except Exception as e:
        logger.warning(f"[warmup] RNNoise unavailable, calls will run without noise suppression: {e}")
        _rnnoise_available = False
        return False


def warm_up_services() -> None:
    global _warmed_up
    if _warmed_up:
        return

    t0 = time.monotonic()

    t = time.monotonic()
    _import_pipecat_services()
    logger.info(f"[warmup] pipecat module imports finished (+{time.monotonic() - t:.3f}s)")

    t = time.monotonic()
    _preload_silero_vad()
    _preload_silero_vad_phone()
    logger.info(f"[warmup] Silero VAD preloaded (+{time.monotonic() - t:.3f}s)")

    t = time.monotonic()
    _preload_smart_turn()
    logger.info(f"[warmup] Smart Turn ONNX preloaded (+{time.monotonic() - t:.3f}s)")

    t = time.monotonic()
    if _probe_rnnoise():
        logger.info(f"[warmup] RNNoise probe ok (+{time.monotonic() - t:.3f}s)")

    _warmed_up = True
    logger.info(f"[warmup] all services warmed up in {time.monotonic() - t0:.3f}s")


def get_silero_vad():
    return _silero_vad_analyzer


def get_silero_vad_phone():
    return _silero_vad_analyzer_phone or _silero_vad_analyzer


def get_smart_turn():
    return _smart_turn_analyzer


def build_rnnoise_filter() -> Optional[RNNoiseFilter]:
    if not _rnnoise_available:
        return None
    try:
        return RNNoiseFilter(resampler_quality="QQ")
    except Exception as e:
        logger.warning(f"[transport] failed to build RNNoise filter: {e}")
        return None


def is_warmed_up() -> bool:
    return _warmed_up
