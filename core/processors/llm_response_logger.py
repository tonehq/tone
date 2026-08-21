"""LLM response observability — logs one line per assistant response.

Inserted into the Pipecat pipeline AFTER ``LLMTextProcessor`` and before TTS
so it observes the fully-assembled LLM answer text and the model that
produced it. Does not mutate frames — pure logging.

Pairs with the ``[pgvector.query]`` line emitted by the RAG store: for one
voice turn, grep by ``trace_id`` gives you the user query → retrieved chunks
→ LLM answer trail without opening any DB row.
"""

from __future__ import annotations

import time
from typing import Optional

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

# Reuse the same "trim text for a log line" helper as the RAG logs so a long
# LLM answer is truncated the same way as a long user query (200 chars +
# ellipsis marker on cut). Single source of truth.
from core.services.rag.logging_utils import truncate_query_text as _truncate_for_log


class LLMResponseLogger(FrameProcessor):
    """Emit one INFO line per LLM full response.

    Buffers ``TextFrame`` chunks between ``LLMFullResponseStartFrame`` and
    ``LLMFullResponseEndFrame``, then logs the assembled text with the model
    name, turn number, and elapsed duration.

    ``llm_model`` is captured at construction time (from the built LLM
    service or the request spec) so the log line is self-contained — no
    lookup on the current frame's service instance is needed.
    """

    def __init__(
        self,
        *,
        llm_model: Optional[str] = None,
        current_turn: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._llm_model = llm_model or "unknown"
        self._current_turn = current_turn
        self._buffer: list[str] = []
        self._collecting = False
        self._t_start: float = 0.0

    def _turn_number(self) -> Optional[int]:
        if not self._current_turn:
            return None
        return self._current_turn.get("number")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            self._collecting = True
            self._buffer.clear()
            self._t_start = time.monotonic()

        elif isinstance(frame, TextFrame) and self._collecting:
            if frame.text and frame.text.strip():
                self._buffer.append(frame.text)

        elif isinstance(frame, LLMFullResponseEndFrame):
            duration_ms = round((time.monotonic() - self._t_start) * 1000)
            full_text = "".join(self._buffer).strip()
            char_count = len(full_text)
            # ONE line per assistant response — carries the model name, the
            # exact answer text (truncated), the length in chars, the turn
            # number the answer belongs to, and how long the LLM took. Grep
            # by trace_id to correlate with [pgvector.query] for the same
            # user query.
            logger.info(
                "[llm.response] model={} turn={} chars={} duration_ms={} answer='{}'",
                self._llm_model,
                self._turn_number(),
                char_count,
                duration_ms,
                _truncate_for_log(full_text),
            )
            self._buffer.clear()
            self._collecting = False

        await self.push_frame(frame, direction)
