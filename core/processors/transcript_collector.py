"""Processors to collect call transcripts (user speech + bot responses).

Two processors share one entries list:
- UserTranscriptProcessor  — placed after STT, captures TranscriptionFrame
- BotTranscriptProcessor   — placed after LLMTextProcessor, captures LLM response text

Both accept an optional ``current_turn`` dict (owned by the runner and mutated
on ``on_turn_started``) so each captured entry is stamped with the pipecat turn
number that produced it — downstream consolidation joins transcript + tool
executions + turn metrics on that field.
"""

import time
from typing import Optional

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


def _current_turn_number(current_turn: Optional[dict]) -> Optional[int]:
    """Snapshot the live ``current_turn`` dict at entry-append time."""
    if not current_turn:
        return None
    return current_turn.get("number")


class UserTranscriptProcessor(FrameProcessor):
    """Captures user speech from TranscriptionFrame (STT output).

    Place after STT in the pipeline, before the context aggregator.
    """

    def __init__(self, entries: list[dict], current_turn: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._entries = entries
        self._current_turn = current_turn

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame) and frame.text and frame.text.strip():
            self._entries.append({
                "role": "user",
                "text": frame.text.strip(),
                "timestamp": int(time.time()),
                "turn_number": _current_turn_number(self._current_turn),
            })

        await self.push_frame(frame, direction)


class BotTranscriptProcessor(FrameProcessor):
    """Captures bot responses from LLM text frames.

    Place after LLMTextProcessor in the pipeline, before TTS.
    Listens for LLMFullResponseStartFrame / TextFrame / LLMFullResponseEndFrame.
    """

    def __init__(self, entries: list[dict], current_turn: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._entries = entries
        self._current_turn = current_turn
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
                        "turn_number": _current_turn_number(self._current_turn),
                    })
            self._bot_text_buffer.clear()
            self._collecting = False

        if isinstance(frame, EndFrame):
            logger.info("Call ended. Transcript has {} entries", len(self._entries))

        await self.push_frame(frame, direction)
