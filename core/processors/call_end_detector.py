import re
from typing import Optional

from loguru import logger
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    EndFrame,
    Frame,
    TranscriptionFrame,
    TTSSpeakFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


_GOODBYE_TRIGGERS = [
    "bye",
    "goodbye",
    "good bye",
    "bye bye",
    "thats all",
    "that's all",
    "thats it",
    "that's it",
    "im done",
    "i'm done",
    "we're done",
    "were done",
    "hang up",
    "hang up the call",
    "end the call",
    "end call",
    "thank you bye",
    "thanks bye",
    "okay bye",
    "ok bye",
]

_MAX_WORDS = 6

_TRIGGER_PATTERN = re.compile(
    "|".join(rf"^{re.escape(p)}[.!?]?\s*$" for p in _GOODBYE_TRIGGERS),
    re.IGNORECASE,
)


class CallEndDetectorProcessor(FrameProcessor):
    def __init__(self, end_call_message: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._end_call_message = (end_call_message or "").strip() or None
        self._end_call_requested = False
        self._farewell_spoken = False

        if self._end_call_message:
            logger.info(
                "CallEndDetector enabled; bot farewell: {!r}", self._end_call_message
            )
        else:
            logger.info(
                "CallEndDetector running with hang-up only (no farewell configured)"
            )

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if (
            isinstance(frame, TranscriptionFrame)
            and frame.text
            and not self._end_call_requested
        ):
            text = frame.text.strip()
            word_count = len(text.split())
            if word_count <= _MAX_WORDS and _TRIGGER_PATTERN.match(text):
                logger.info("End-of-call trigger matched from user: {!r}", text)
                self._end_call_requested = True
                if self._end_call_message:
                    await self.push_frame(
                        TTSSpeakFrame(text=self._end_call_message), FrameDirection.DOWNSTREAM
                    )
                    self._farewell_spoken = True
                    return
                await self.push_frame(EndFrame())
                return

        if (
            isinstance(frame, BotStoppedSpeakingFrame)
            and self._end_call_requested
            and self._farewell_spoken
        ):
            logger.info("Bot finished farewell — ending call")
            await self.push_frame(frame, direction)
            await self.push_frame(EndFrame())
            return

        await self.push_frame(frame, direction)
