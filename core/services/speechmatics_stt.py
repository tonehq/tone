"""Custom Speechmatics STT service that emits VAD frames for LocalSmartTurnAnalyzerV3.

Speechmatics (adaptive mode) provides fast basic VAD via StartOfTurn/EndOfTurn.
This subclass converts those into VADUserStarted/StoppedSpeakingFrame so that
LocalSmartTurnAnalyzerV3 can use them alongside raw audio for smart turn detection.

No transport-level SileroVADAnalyzer needed.
"""

import time
from typing import Any

from pipecat.frames.frames import (
    MetricsFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import ProcessingMetricsData
from pipecat.services.speechmatics.stt import SpeechmaticsSTTService


class ToneSpeechmaticsSTTService(SpeechmaticsSTTService):
    """Speechmatics STT that emits VAD frames for LocalSmartTurnAnalyzerV3 compatibility."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_segment_time: float = 0
        self._turn_active: bool = False

    async def _handle_segment(self, message: dict[str, Any]) -> None:
        """Track when the last finalized segment arrives."""
        self._last_segment_time = time.time()
        await super()._handle_segment(message)

    async def _handle_start_of_turn(self, message: dict[str, Any]) -> None:
        self._turn_active = True
        self._last_segment_time = 0
        await self.start_processing_metrics()
        await self.push_frame(VADUserStartedSpeakingFrame())
        if self._should_interrupt:
            await self.push_interruption_task_frame_and_wait()

    async def _handle_end_of_turn(self, message: dict[str, Any]) -> None:
        # Emit STT processing metric
        if self._turn_active and self._last_segment_time > 0:
            latency = time.time() - self._last_segment_time
            model_name = getattr(self, '_model_name', None)
            if callable(model_name):
                model_name = model_name()
            processing = ProcessingMetricsData(
                processor=self.name,
                value=latency,
                model=model_name,
            )
            await self.push_frame(MetricsFrame(data=[processing]))

        self._turn_active = False
        self._last_segment_time = 0
        await self.stop_processing_metrics()
        await self.push_frame(VADUserStoppedSpeakingFrame())
