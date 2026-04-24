"""Observer for measuring user-to-bot response latency.

Handles both transport-level VAD frames (VADUserStarted/StoppedSpeakingFrame)
and STT-level speaking frames (UserStarted/StoppedSpeakingFrame) so latency
is recorded regardless of whether VAD comes from Silero or Speechmatics.
"""

import time
from statistics import mean

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    CancelFrame,
    EndFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.processors.frame_processor import FrameDirection


class UserBotLatencyObserver(BaseObserver):
    """Measures time between user stopping speech and bot starting speech.

    Unlike the upstream UserBotLatencyLogObserver which only listens for
    VADUser* frames, this observer also handles UserStarted/StoppedSpeakingFrame
    emitted by STT services with built-in turn detection (e.g. Speechmatics SMART_TURN).
    """

    def __init__(self):
        super().__init__()
        self._processed_frames = set()
        self._user_stopped_time = 0
        self._latencies = []

    async def on_push_frame(self, data: FramePushed):
        if data.direction != FrameDirection.DOWNSTREAM:
            return

        if data.frame.id in self._processed_frames:
            return

        self._processed_frames.add(data.frame.id)

        if isinstance(data.frame, (VADUserStartedSpeakingFrame, UserStartedSpeakingFrame)):
            self._user_stopped_time = 0
        elif isinstance(data.frame, (VADUserStoppedSpeakingFrame, UserStoppedSpeakingFrame)):
            self._user_stopped_time = time.time()
        elif isinstance(data.frame, (EndFrame, CancelFrame)):
            self._log_summary()
        elif isinstance(data.frame, BotStartedSpeakingFrame) and self._user_stopped_time:
            latency = time.time() - self._user_stopped_time
            self._user_stopped_time = 0
            self._latencies.append(latency)
            self._log_latency(latency)

    def _log_summary(self):
        if not self._latencies:
            return
        avg_latency = mean(self._latencies)
        min_latency = min(self._latencies)
        max_latency = max(self._latencies)
        logger.info(
            f"LATENCY FROM USER STOPPED SPEAKING TO BOT STARTED SPEAKING - "
            f"Avg: {avg_latency:.3f}s, Min: {min_latency:.3f}s, Max: {max_latency:.3f}s"
        )

    def _log_latency(self, latency: float):
        logger.info(
            f"LATENCY FROM USER STOPPED SPEAKING TO BOT STARTED SPEAKING: {latency:.3f}s"
        )
