"""Processors to collect call transcripts (user speech + bot responses).

Two processors share one entries list:
- UserTranscriptProcessor  — placed after STT, captures TranscriptionFrame
- BotTranscriptProcessor   — placed after LLMTextProcessor, captures LLM response text
"""

import time

from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


def build_transcript_text(entries: list[dict]) -> str:
    """Format a shared entries list into readable transcript text."""
    lines = []
    for entry in entries:
        role = entry["role"].capitalize()
        lines.append(f"{role}: {entry['text']}")
    return "\n".join(lines)


class UserTranscriptProcessor(FrameProcessor):
    """Captures user speech from TranscriptionFrame (STT output).

    Place after STT in the pipeline, before the context aggregator.
    """

    def __init__(self, entries: list[dict], **kwargs):
        super().__init__(**kwargs)
        self._entries = entries

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame) and frame.text and frame.text.strip():
            self._entries.append({
                "role": "user",
                "text": frame.text.strip(),
                "timestamp": int(time.time()),
            })

        await self.push_frame(frame, direction)


class BotTranscriptProcessor(FrameProcessor):
    """Captures bot responses from LLM text frames.

    Place after LLMTextProcessor in the pipeline, before TTS.
    Listens for LLMFullResponseStartFrame / TextFrame / LLMFullResponseEndFrame.
    """

    def __init__(self, entries: list[dict], **kwargs):
        super().__init__(**kwargs)
        self._entries = entries
        self._bot_text_buffer: list[str] = []
        self._collecting = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._collecting = True
            self._bot_text_buffer.clear()

        if isinstance(frame, TextFrame) and self._collecting:
            if frame.text and frame.text.strip():
                self._bot_text_buffer.append(frame.text)

        if isinstance(frame, LLMFullResponseEndFrame):
            if self._bot_text_buffer:
                full_text = "".join(self._bot_text_buffer).strip()
                if full_text:
                    self._entries.append({
                        "role": "assistant",
                        "text": full_text,
                        "timestamp": int(time.time()),
                    })
            self._bot_text_buffer.clear()
            self._collecting = False

        if isinstance(frame, EndFrame):
            logger.info("Call ended. Transcript has {} entries", len(self._entries))

        await self.push_frame(frame, direction)
