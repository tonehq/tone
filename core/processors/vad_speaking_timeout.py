"""Forces VADUserStoppedSpeakingFrame after max continuous speaking duration.

On phone calls, Silero VAD can get stuck in "speaking" state due to line noise.
This processor injects a synthetic VADUserStoppedSpeakingFrame when VAD has been
in speaking state for too long, which:
1. Forces segmented STTs (like OpenAI) to process buffered audio
2. Allows turn stop strategies to fire
3. If the user is actually still speaking, VAD will fire start again
"""

import time

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class VADSpeakingTimeoutProcessor(FrameProcessor):
    """Injects VADUserStoppedSpeakingFrame after max_duration_secs of continuous speaking."""

    def __init__(self, *, max_duration_secs: float = 8.0, **kwargs):
        super().__init__(**kwargs)
        self._max_duration = max_duration_secs
        self._speaking = False
        self._speak_start: float = 0
        self._forced_stop = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, VADUserStartedSpeakingFrame):
            self._speaking = True
            self._speak_start = time.time()
            self._forced_stop = False
            await self.push_frame(frame, direction)

        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self._speaking = False
            self._forced_stop = False
            await self.push_frame(frame, direction)

        elif isinstance(frame, InputAudioRawFrame):
            if self._speaking and not self._forced_stop:
                elapsed = time.time() - self._speak_start
                if elapsed >= self._max_duration:
                    logger.info(
                        f"[VADSpeakingTimeout] VAD stuck in speaking state for "
                        f"{elapsed:.1f}s, forcing stop"
                    )
                    self._forced_stop = True
                    self._speaking = False
                    await self.push_frame(VADUserStoppedSpeakingFrame(), direction)
            await self.push_frame(frame, direction)

        else:
            await self.push_frame(frame, direction)
