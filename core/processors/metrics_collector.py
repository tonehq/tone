"""Pipeline metrics collector.

Collects two views of pipeline metrics from MetricsFrame objects:

1. Flat lists (legacy) — every TTFB / processing / token / TTS-usage event,
   in arrival order. Persisted to the existing ``call_metrics`` JSONB columns
   and consumed by existing frontend code.

2. Per-turn aggregation — buckets metrics into turns using ``on_turn_started``
   / ``on_turn_ended`` callbacks driven by pipecat's ``TurnTrackingObserver``
   (wired by the runner). Each turn yields one row with the user-felt
   headline values (first STT/LLM/TTS TTFB) plus the full raw lists for
   deeper analysis, and a wall-clock ``end_to_end`` from user-stopped to
   bot-started.

Pipeline placement: at the very end of the pipeline (after transport.output()).
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    Frame,
    MetricsFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import (
    LLMUsageMetricsData,
    MetricsData,
    ProcessingMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

# Service-role categories used by the per-turn aggregation. The builder
# supplies a {processor_instance_name -> category} map so the collector can
# bucket TTFB samples without string-matching service class names.
CATEGORY_STT = "stt"
CATEGORY_LLM = "llm"
CATEGORY_TTS = "tts"
_TTFB_CATEGORIES = (CATEGORY_STT, CATEGORY_LLM, CATEGORY_TTS)

# Bucket for metrics that arrive before pipecat's first turn (e.g. the
# agent's initial greeting). Stored as turn 0 — pipecat's turn counter
# starts at 1, so collisions are impossible.
_PRE_TURN = 0


@dataclass
class _TurnBuffer:
    """Mutable per-turn accumulator. Converted to an output dict at turn end."""

    turn_number: int
    started_at: Optional[float] = None
    user_stopped_at: Optional[float] = None
    bot_started_at: Optional[float] = None
    ttfb: Dict[str, List[float]] = field(
        default_factory=lambda: {c: [] for c in _TTFB_CATEGORIES}
    )
    processing: List[dict] = field(default_factory=list)
    llm_usage: List[dict] = field(default_factory=list)
    tts_usage: List[dict] = field(default_factory=list)


def _round_optional(value: Optional[float], digits: int = 3) -> Optional[float]:
    return round(value, digits) if value is not None else None


def _sum_field(items: List[dict], key: str) -> int:
    return sum(int(item.get(key) or 0) for item in items)


def _finalize_buffer(
    buffer: _TurnBuffer,
    *,
    status: str,
    duration: Optional[float] = None,
) -> dict:
    """Turn an in-progress ``_TurnBuffer`` into the immutable per-turn row.

    The headline ``stt_ttfb`` / ``llm_ttfb`` / ``tts_ttfb`` are the first
    sample of each — that's the value the user actually perceives. The full
    raw lists are kept in ``*_ttfb_all`` for deeper analysis (e.g. slow
    sentence boundaries on TTS, tool-call follow-ups on LLM).

    ``end_to_end`` is the wall-clock gap between the user finishing speaking
    and the bot starting to speak. Null when either timestamp wasn't
    captured (e.g. the agent's first greeting has no preceding user speech).
    """
    stt = buffer.ttfb[CATEGORY_STT]
    llm = buffer.ttfb[CATEGORY_LLM]
    tts = buffer.ttfb[CATEGORY_TTS]

    end_to_end: Optional[float] = None
    if buffer.user_stopped_at is not None and buffer.bot_started_at is not None:
        end_to_end = round(buffer.bot_started_at - buffer.user_stopped_at, 3)

    llm_summary: Optional[dict] = None
    if buffer.llm_usage:
        llm_summary = {
            "prompt_tokens": _sum_field(buffer.llm_usage, "prompt_tokens"),
            "completion_tokens": _sum_field(buffer.llm_usage, "completion_tokens"),
            "total_tokens": _sum_field(buffer.llm_usage, "total_tokens"),
        }

    return {
        "turn": buffer.turn_number,
        "status": status,
        "duration": _round_optional(duration),
        "started_at": buffer.started_at,
        "user_stopped_at": buffer.user_stopped_at,
        "bot_started_at": buffer.bot_started_at,
        "end_to_end": end_to_end,
        "stt_ttfb": _round_optional(stt[0]) if stt else None,
        "llm_ttfb": _round_optional(llm[0]) if llm else None,
        "tts_ttfb": _round_optional(tts[0]) if tts else None,
        "stt_ttfb_all": [_round_optional(v) for v in stt],
        "llm_ttfb_all": [_round_optional(v) for v in llm],
        "tts_ttfb_all": [_round_optional(v) for v in tts],
        "llm_usage": llm_summary,
        "tts_characters": _sum_field(buffer.tts_usage, "characters") if buffer.tts_usage else None,
    }


class MetricsCollectorProcessor(FrameProcessor):
    """Collects pipeline metrics from MetricsFrames flowing through the pipeline.

    Maintains two views over the same stream of events:

    * **Flat lists** (``ttfb``/``processing``/``llm_usage``/``tts_usage``) —
      the historical shape persisted in the existing ``call_metrics`` columns.
    * **Per-turn aggregation** (``turn_metrics``) — one summary row per turn,
      joining metrics with user-stopped / bot-started timestamps. Driven by
      external ``on_turn_started`` / ``on_turn_ended`` calls from the runner
      (which forwards pipecat's ``TurnTrackingObserver`` events).

    ``service_categories`` maps a pipecat service's ``name`` (e.g.
    ``"DeepgramSTTService#0"``) to its role (``"stt"`` / ``"llm"`` / ``"tts"``).
    Without it the per-turn TTFB breakdown is empty — the flat lists are
    unaffected.
    """

    def __init__(
        self,
        service_categories: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._service_categories: Dict[str, str] = dict(service_categories or {})

        # Flat-list view (legacy, persisted to the existing columns).
        self.ttfb_metrics: List[dict] = []
        self.processing_metrics: List[dict] = []
        self.llm_usage_metrics: List[dict] = []
        self.tts_usage_metrics: List[dict] = []

        # Per-turn view.
        self._buffers: Dict[int, _TurnBuffer] = {}
        self._current_turn: Optional[int] = None
        self._turn_metrics: List[dict] = []

    # ------------------------------------------------------------------
    # Turn-tracking hooks (called by the runner from TurnTrackingObserver)
    # ------------------------------------------------------------------

    def on_turn_started(self, turn_number: int) -> None:
        """Open a fresh buffer for ``turn_number`` and make it current."""
        self._current_turn = turn_number
        # Preserve an already-open buffer if process_frame created one early
        # (a TTFB metric can arrive concurrently with the turn-start event).
        existing = self._buffers.get(turn_number)
        if existing is None:
            self._buffers[turn_number] = _TurnBuffer(
                turn_number=turn_number,
                started_at=time.time(),
            )
        elif existing.started_at is None:
            existing.started_at = time.time()

    def on_turn_ended(
        self,
        turn_number: int,
        duration: Optional[float] = None,
        was_interrupted: bool = False,
    ) -> None:
        """Finalize ``turn_number``'s buffer into ``turn_metrics``."""
        buffer = self._buffers.pop(turn_number, None)
        if buffer is None:
            return
        status = "interrupted" if was_interrupted else "completed"
        self._turn_metrics.append(
            _finalize_buffer(buffer, status=status, duration=duration)
        )
        if self._current_turn == turn_number:
            self._current_turn = None

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, MetricsFrame):
            for data in frame.data:
                self._record_metric_data(data)
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._mark_user_stopped()
        elif isinstance(frame, BotStartedSpeakingFrame):
            self._mark_bot_started()

        await self.push_frame(frame, direction)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _active_buffer(self) -> _TurnBuffer:
        """Return the buffer events should be bucketed into.

        Events that arrive before pipecat's first turn (e.g. the agent's
        first greeting) bucket into a ``_PRE_TURN`` buffer that's flushed
        in :py:meth:`get_turn_metrics`.
        """
        turn = self._current_turn if self._current_turn is not None else _PRE_TURN
        buffer = self._buffers.get(turn)
        if buffer is None:
            buffer = _TurnBuffer(turn_number=turn, started_at=time.time())
            self._buffers[turn] = buffer
        return buffer

    def _category_for(self, processor_name: Optional[str]) -> Optional[str]:
        if not processor_name:
            return None
        return self._service_categories.get(processor_name)

    def _mark_user_stopped(self) -> None:
        buffer = self._active_buffer()
        if buffer.user_stopped_at is None:
            buffer.user_stopped_at = time.time()

    def _mark_bot_started(self) -> None:
        buffer = self._active_buffer()
        # Capture only the first bot_started per turn — that's the user-felt
        # latency edge. Later BotStartedSpeaking frames in the same turn
        # (e.g. after a tool-call pause) don't change what the user felt.
        if buffer.bot_started_at is None:
            buffer.bot_started_at = time.time()

    def _record_metric_data(self, data: MetricsData) -> None:
        if isinstance(data, TTFBMetricsData):
            entry = {
                "processor": data.processor,
                "model": data.model,
                "value": data.value,
            }
            self.ttfb_metrics.append(entry)
            category = self._category_for(data.processor)
            if category in _TTFB_CATEGORIES:
                self._active_buffer().ttfb[category].append(data.value)

        elif isinstance(data, ProcessingMetricsData):
            entry = {
                "processor": data.processor,
                "model": data.model,
                "value": data.value,
            }
            self.processing_metrics.append(entry)
            self._active_buffer().processing.append(entry)

        elif isinstance(data, LLMUsageMetricsData):
            usage = data.value
            entry = {
                "processor": data.processor,
                "model": data.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            self.llm_usage_metrics.append(entry)
            self._active_buffer().llm_usage.append(entry)

        elif isinstance(data, TTSUsageMetricsData):
            entry = {
                "processor": data.processor,
                "model": data.model,
                "characters": data.value,
            }
            self.tts_usage_metrics.append(entry)
            self._active_buffer().tts_usage.append(entry)

    # ------------------------------------------------------------------
    # Read-out
    # ------------------------------------------------------------------

    def get_collected_metrics(self) -> dict:
        """Return all collected metrics as a dictionary."""
        return {
            "ttfb": self.ttfb_metrics,
            "processing": self.processing_metrics,
            "llm_usage": self.llm_usage_metrics,
            "tts_usage": self.tts_usage_metrics,
            "turn_metrics": self.get_turn_metrics(),
        }

    def get_turn_metrics(self) -> List[dict]:
        """Return the finalized per-turn rows.

        Drains any still-open buffers (a pre-turn bucket, or a turn that
        ended abnormally without an ``on_turn_ended`` callback) so no
        in-flight data is silently dropped at call end. Safe to call
        multiple times: drained buffers don't reappear.
        """
        for turn_number in sorted(self._buffers.keys()):
            buffer = self._buffers[turn_number]
            self._turn_metrics.append(_finalize_buffer(buffer, status="pending"))
        self._buffers.clear()
        return list(self._turn_metrics)
