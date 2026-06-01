import time
from typing import Optional

from loguru import logger
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


def _normalize(text: str) -> str:
    return " ".join((text or "").split()).lower()


class DuplicateTranscriptionFilter(FrameProcessor):
    """Filters out duplicate final transcriptions within a time window."""

    def __init__(self, *, window: float = 8.0, **kwargs):
        super().__init__(**kwargs)
        self._window = window
        self._last_text: Optional[str] = None
        self._last_time: float = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            normalized = _normalize(frame.text)
            if normalized:
                now = time.monotonic()
                if (
                    self._last_text
                    and (now - self._last_time) <= self._window
                    and (normalized == self._last_text or normalized.startswith(self._last_text))
                ):
                    logger.info(
                        f"[DuplicateTranscriptionFilter] dropping duplicate final "
                        f"text={frame.text!r} (prev={self._last_text!r}, "
                        f"{now - self._last_time:.1f}s ago)"
                    )
                    return
                self._last_text = normalized
                self._last_time = now

        await self.push_frame(frame, direction)
