"""Custom Speechmatics STT service with processing metrics enabled.

The upstream SpeechmaticsSTTService has start/stop_processing_metrics()
commented out in _handle_start_of_turn and _handle_end_of_turn, causing
STT latency to always report 0.00. This subclass re-enables them.
"""

from typing import Any

from loguru import logger

from pipecat.frames.frames import UserStartedSpeakingFrame, UserStoppedSpeakingFrame
from pipecat.services.speechmatics.stt import SpeechmaticsSTTService


class ToneSpeechmaticsSTTService(SpeechmaticsSTTService):
    """Speechmatics STT with processing metrics enabled."""

    async def _handle_start_of_turn(self, message: dict[str, Any]) -> None:
        logger.debug(f"{self} StartOfTurn received")
        await self.start_processing_metrics()
        await self.broadcast_frame(UserStartedSpeakingFrame)
        if self._should_interrupt:
            await self.push_interruption_task_frame_and_wait()

    async def _handle_end_of_turn(self, message: dict[str, Any]) -> None:
        logger.debug(f"{self} EndOfTurn received")
        await self.stop_processing_metrics()
        await self.broadcast_frame(UserStoppedSpeakingFrame)
