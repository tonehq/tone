from __future__ import annotations

from typing import Any, Dict, List

from benchmarks.base import BaseBenchmark
from core.services.pipeline import service_factory
from core.services.readiness.probes import _extract_transcript_text, _load_stt_audio
from pipecat.frames.frames import (
    InputAudioRawFrame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    UserStoppedSpeakingFrame,
)


class STTBenchmark(BaseBenchmark):
    service_type = "stt"
    timeout_s = 30.0
    warmup_s = 3.0
    end_frame_after_s = 3.0

    def build_service(self) -> Any:
        return service_factory.build_stt(self.spec)

    def input_frames(self, service: Any) -> List[Any]:
        sample_rate = int((self.spec.get("metadata") or {}).get("sample_rate") or 16000)
        audio, using_real_audio = _load_stt_audio(sample_rate, service)
        if not using_real_audio:
            raise RuntimeError(
                "probe_sample.wav missing -- STT benchmark needs real audio, "
                "silence would report timings that prove nothing"
            )

        chunk = sample_rate // 10 * 2
        frames: List[Any] = [
            InputAudioRawFrame(audio=audio[i : i + chunk], sample_rate=sample_rate, num_channels=1)
            for i in range(0, len(audio), chunk)
        ]
        frames.append(UserStoppedSpeakingFrame())
        return frames

    def is_target(self, frame: Any) -> bool:
        return (
            _extract_transcript_text(frame, (TranscriptionFrame, InterimTranscriptionFrame))
            is not None
        )

    def sample_detail(self, frame: Any) -> Dict[str, Any]:
        text = (getattr(frame, "text", "") or "").strip()
        return {"transcript": text[:120]} if text else {}
