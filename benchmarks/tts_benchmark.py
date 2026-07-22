from __future__ import annotations

from typing import Any, Dict, List

from benchmarks.base import BaseBenchmark
from core.services.pipeline import service_factory
from pipecat.frames.frames import TTSAudioRawFrame, TTSSpeakFrame, TTSStoppedFrame

DEFAULT_SENTENCE = "Thanks for calling. I can help you book an appointment today."


class TTSBenchmark(BaseBenchmark):
    service_type = "tts"
    timeout_s = 25.0
    warmup_s = 2.0
    end_frame_after_s = None

    def __init__(self, spec: Dict[str, Any], *, sentence: str = DEFAULT_SENTENCE, **kwargs):
        super().__init__(spec, **kwargs)
        self.sentence = sentence

    def build_service(self) -> Any:
        return service_factory.build_tts(self.spec)

    def input_frames(self, _service: Any) -> List[Any]:
        return [TTSSpeakFrame(self.sentence)]

    def is_target(self, frame: Any) -> bool:
        return isinstance(frame, TTSAudioRawFrame) and bool(getattr(frame, "audio", b""))

    def is_complete(self, frame: Any) -> bool:
        return isinstance(frame, TTSStoppedFrame)

    def sample_detail(self, frame: Any) -> Dict[str, Any]:
        audio = getattr(frame, "audio", b"") or b""
        rate = getattr(frame, "sample_rate", None)
        detail: Dict[str, Any] = {"first_chunk_bytes": len(audio)}
        if rate:
            detail["sample_rate"] = rate
        return detail
