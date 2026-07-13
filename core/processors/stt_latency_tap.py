"""STT TTFB derivation tap.

Sits upstream of the user-context aggregator to compute STT TTFB ourselves
and emit it as a synthetic ``MetricsFrame`` that the existing
``MetricsCollectorProcessor`` can consume.

Why this exists
---------------
Pipecat's ``STTService._emit_stt_ttfb_metric`` only fires when the underlying
STT implementation marks its ``TranscriptionFrame`` with ``finalized=True``.
Several streaming STTs — Deepgram included — push the final transcript as a
plain ``TranscriptionFrame`` without that flag, so the upstream metric is
never emitted for real user utterances (only the 0.0 placeholder at session
start).

The user context aggregator (``LLMUserContextAggregator._handle_transcription``)
**absorbs** ``TranscriptionFrame`` without pushing it downstream, so a
collector positioned at the end of the pipeline (where it must sit to also
see LLM/TTS metrics and ``UserStoppedSpeakingFrame``) never observes the
transcript at all. We work around it by tapping the frame *before* the
aggregator absorbs it.

Pipeline placement
------------------
Insert between the STT-related upstream processors (``stt``,
``duplicate_filter``) and the user context aggregator. The exact slot is::

    stt → duplicate_filter → stt_latency_tap → user_aggregator → ...

Frame contract
--------------
Every frame is passed through unchanged (no consumption). Side effects are
limited to:

* On ``UserStoppedSpeakingFrame`` → record ``user_stopped_at`` (overwrites
  any prior unmatched stop; one stop "arms" one TTFB).
* On the first ``TranscriptionFrame`` after a stop → push a
  ``MetricsFrame`` carrying a ``TTFBMetricsData`` so the collector's normal
  STT-handling path catches it.
"""

import os
import time
from typing import Optional

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    CancelFrame,
    EndFrame,
    Frame,
    MetricsFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import TTFBMetricsData
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

# Upper bound (seconds) on a plausible STT TTFB. A streaming STT emits its final
# transcript within a few hundred ms of the caller stopping; it never legitimately
# takes seconds. Anything above this is a measurement artifact — the armed
# `user_stopped_at` anchor survived a long real-world SILENCE (caller pausing/
# thinking, end of call, or a late/spurious transcript) and the gap got recorded
# as "STT latency". Those samples produced phantom 60s+ p99 spikes on the dashboard
# while the real STT was ~300-800ms. We discard them instead of emitting a metric.
# Env-tunable so it can be relaxed without a redeploy.
MAX_SANE_STT_TTFB_S = float(os.getenv("STT_MAX_SANE_TTFB_S", "5.0"))


class STTLatencyTap(FrameProcessor):
    """Emits derived STT TTFB ``MetricsFrame``s in-line on the pipeline.

    Args:
        stt_processor_name: Canonical processor name to label the synthesized
            ``TTFBMetricsData`` with (e.g. ``"DeepgramSTTService#0"``). Must
            match the name registered in
            ``MetricsCollectorProcessor._service_categories`` so the
            collector classifies the metric as STT.
        stt_model_name: Optional model name to copy onto the metric for
            flat-list readability. ``None`` is fine.
    """

    def __init__(
        self,
        *,
        stt_processor_name: str,
        stt_model_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._stt_processor_name = stt_processor_name
        self._stt_model_name = stt_model_name
        self._user_stopped_at: Optional[float] = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            # New utterance starting — any unconsumed user-stop from a
            # previous utterance is stale. Clearing it prevents the next
            # transcript from being measured against an anchor that's many
            # seconds (or turns) old, which would inflate the first STT
            # TTFB of every new turn.
            self._user_stopped_at = None
        elif isinstance(frame, UserStoppedSpeakingFrame):
            # One stop arms one TTFB. A second stop without a transcript
            # in between overwrites — we'd rather attribute the next
            # transcript to the most recent stop than to a stale one.
            self._user_stopped_at = time.time()
        elif isinstance(frame, (BotStartedSpeakingFrame, EndFrame, CancelFrame)):
            # The bot has started responding (so this turn's STT already
            # resolved), or the call is ending. Any still-armed stop is stale —
            # disarm it so a later/spurious transcript isn't matched to it and
            # recorded as a multi-second "STT latency".
            self._user_stopped_at = None
        elif isinstance(frame, TranscriptionFrame) and self._user_stopped_at is not None:
            await self._emit_stt_ttfb()

        await self.push_frame(frame, direction)

    async def _emit_stt_ttfb(self) -> None:
        """Build a ``TTFBMetricsData`` and wrap it in a downstream ``MetricsFrame``.

        The collector at the end of the pipeline picks this up through its
        normal ``_record_metric_data`` path (TTFBMetricsData → category=STT
        → FIFO attribution into the right turn).
        """
        assert self._user_stopped_at is not None  # checked by caller
        ttfb = time.time() - self._user_stopped_at
        # Consume the slot — the next transcript belongs to the next stop.
        self._user_stopped_at = None
        if ttfb < 0:
            return
        if ttfb > MAX_SANE_STT_TTFB_S:
            # Silence-gap artifact, not real STT time — drop it so it doesn't
            # inflate the STT p99 with phantom multi-second spikes.
            logger.debug(
                "[stt-ttfb] discarding implausible STT TTFB {:.1f}s (> {:.0f}s cap) "
                "— treated as a silence gap, not STT processing time",
                ttfb, MAX_SANE_STT_TTFB_S,
            )
            return
        data = TTFBMetricsData(
            processor=self._stt_processor_name,
            model=self._stt_model_name,
            value=ttfb,
        )
        await self.push_frame(MetricsFrame(data=[data]), FrameDirection.DOWNSTREAM)
