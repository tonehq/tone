"""Processor to detect end-of-call phrases and gracefully terminate the pipeline."""

import re

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

# Patterns that indicate the user wants to end the call.
# These only trigger when the ENTIRE (short) transcription is a farewell.
_END_PATTERNS = [
    r"^(bye\s*bye|bye|goodbye|good\s*bye)\.?!?\s*$",
    r"^thanks?\.?!?\s*$",
    r"^thank\s*you\.?!?\s*$",
    r"^(ok\s+)?(that'?s?\s*(all|it))\.?!?\s*$",
    r"^hang\s*up\.?!?\s*$",
    r"^(please\s+)?end\s*(the\s*)?(call|conversation)\.?!?\s*$",
    r"^no\s*more\s*questions?\.?!?\s*$",
    r"^i'?m\s*done\.?!?\s*$",
    r"^nothing\s*(else|more)\.?!?\s*$",
    r"^(ok\s+)?(bye|thanks?|thank\s*you)\s*(bye|thanks?|thank\s*you)?\.?!?\s*$",
    r"^(ok|okay|alright)\s*(bye|goodbye|thank\s*you|thanks?)\.?!?\s*$",
    r"^thank\s*you\.?\s*bye\.?\s*$",
]

_END_PATTERN = re.compile("|".join(_END_PATTERNS), re.IGNORECASE)


class CallEndDetectorProcessor(FrameProcessor):
    """Detects user end-of-call intent and terminates the pipeline after the bot responds.

    Pipeline placement: between STT and user aggregator, so it sees
    TranscriptionFrames (downstream) and BotStoppedSpeakingFrames (upstream).

    Flow:
      1. User says "bye" → TranscriptionFrame matched (downstream) → flag set
      2. LLM generates farewell → TTS speaks it
      3. BotStoppedSpeakingFrame arrives (upstream) → EndFrame pushed → call ends
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._end_call_requested = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Detect end-of-call phrases in user transcriptions (flowing downstream)
        if isinstance(frame, TranscriptionFrame) and frame.text:
            text = frame.text.strip()
            word_count = len(text.split())
            if text and word_count <= _MAX_WORDS and _END_PATTERN.match(text):
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
