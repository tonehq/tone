import re
from typing import Optional

from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


_MAX_WORDS = 6

_DEFAULT_TRIGGERS = ["bye", "goodbye", "thank you bye", "thanks bye"]


def _build_trigger_pattern(phrases: list[str]) -> Optional[re.Pattern]:
    if not phrases:
        return None
    return re.compile(
        "|".join(rf"^{re.escape(p)}[.!?]?\s*$" for p in phrases),
        re.IGNORECASE,
    )


class CallEndDetectorProcessor(FrameProcessor):
    def __init__(self, end_call_message: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        configured = [
            p.strip().lower()
            for p in (end_call_message or "").split(",")
            if p.strip()
        ]
        self._triggers = configured or _DEFAULT_TRIGGERS
        self._using_defaults = not configured
        self._trigger_pattern = _build_trigger_pattern(self._triggers)
        self._end_call_requested = False

        logger.info(
            "CallEndDetector enabled; user-trigger phrases: {} (source: {})",
            self._triggers,
            "default" if self._using_defaults else "config",
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if (
            self._trigger_pattern
            and isinstance(frame, TranscriptionFrame)
            and frame.text
            and not self._end_call_requested
        ):
            text = frame.text.strip()
            word_count = len(text.split())
            if word_count <= _MAX_WORDS and self._trigger_pattern.match(text):
                logger.info("End-of-call trigger matched from user: {!r}", text)
                self._end_call_requested = True
                await self.push_frame(EndFrame())
                return

        await self.push_frame(frame, direction)
