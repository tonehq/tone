"""Processor to detect end-of-call phrases and gracefully terminate the pipeline."""

import re
from typing import List, Optional

from loguru import logger
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    EndFrame,
    Frame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


# Max number of words for a transcription to be considered a standalone farewell.
# This prevents matching "thank you" inside longer sentences like
# "will provide the details later thank you".
_MAX_WORDS = 5


def _build_end_pattern(phrases: List[str]) -> re.Pattern:
    """Build a compiled regex that matches any of the given phrases (case-insensitive).

    Each phrase is escaped and wrapped so it matches as a standalone transcription,
    allowing optional trailing punctuation.
    """
    escaped = [
        rf"^{re.escape(phrase.strip())}\.?!?\s*$"
        for phrase in phrases
        if phrase.strip()
    ]
    if not escaped:
        # Return a pattern that never matches
        return re.compile(r"(?!)")
    return re.compile("|".join(escaped), re.IGNORECASE)


class CallEndDetectorProcessor(FrameProcessor):
    """Detects user end-of-call intent and terminates the pipeline after the bot responds.

    Pipeline placement: between STT and user aggregator, so it sees
    TranscriptionFrames (downstream) and BotStoppedSpeakingFrames (upstream).

    Flow:
      1. User says a configured end-call phrase → TranscriptionFrame matched → flag set
      2. LLM generates farewell → TTS speaks it
      3. BotStoppedSpeakingFrame arrives (upstream) → EndFrame pushed → call ends

    Args:
        end_call_message: Comma-separated string of phrases that trigger call end.
                          If None or empty, no end-call detection is performed.
    """

    def __init__(self, end_call_message: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._end_call_requested = False

        if end_call_message and end_call_message.strip():
            phrases = [p.strip() for p in end_call_message.split(",") if p.strip()]
            self._end_pattern = _build_end_pattern(phrases)
            self._enabled = bool(phrases)
            logger.info("CallEndDetector configured with phrases: {}", phrases)
        else:
            self._end_pattern = None
            self._enabled = False
            logger.info("CallEndDetector disabled — no end_call_message configured")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if self._enabled:
            # Detect end-of-call phrases in user transcriptions (flowing downstream)
            if isinstance(frame, TranscriptionFrame) and frame.text:
                text = frame.text.strip()
                word_count = len(text.split())
                if text and word_count <= _MAX_WORDS and self._end_pattern.match(text):
                    logger.info(
                        "End-of-call phrase detected in transcription: '{}'", text
                    )
                    self._end_call_requested = True

            # BotStoppedSpeakingFrame is a SystemFrame pushed both upstream and
            # downstream by transport.output(). When placed before the user
            # aggregator, we receive the upstream copy after the bot finishes
            # speaking its farewell.
            if isinstance(frame, BotStoppedSpeakingFrame) and self._end_call_requested:
                logger.info("Bot finished farewell response — ending call")
                self._end_call_requested = False
                await self.push_frame(frame, direction)
                await self.push_frame(EndFrame())
                return

        await self.push_frame(frame, direction)
