"""VAD-independent fallback turn stop strategy.

Triggers end-of-turn when transcription activity stops for a configurable
timeout period. This works even when Silero VAD is stuck in the "speaking"
state due to phone line noise, providing a robust fallback for telephony.
"""

import asyncio
import time
from typing import Optional

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
)
from pipecat.turns.user_stop.base_user_turn_stop_strategy import BaseUserTurnStopStrategy
from pipecat.utils.asyncio.task_manager import BaseTaskManager


class TranscriptionTimeoutUserTurnStopStrategy(BaseUserTurnStopStrategy):
    """Fallback stop strategy that triggers based on transcription inactivity.

    Does NOT depend on VAD frames at all. Monitors transcription activity
    (both final and interim) and triggers end-of-turn when no new
    transcriptions arrive for `timeout` seconds after any speech was detected.
    """

    def __init__(self, *, timeout: float = 1.5, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout
        self._has_speech = False
        self._got_final = False
        self._last_activity_time: float = 0
        self._text = ""
        self._event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    async def reset(self):
        await super().reset()
        self._has_speech = False
        self._got_final = False
        self._last_activity_time = 0
        self._text = ""
        self._event.clear()

    async def setup(self, task_manager: BaseTaskManager):
        await super().setup(task_manager)
        self._task = task_manager.create_task(
            self._task_handler(), f"{self}::_task_handler"
        )

    async def cleanup(self):
        await super().cleanup()
        if self._task:
            await self.task_manager.cancel_task(self._task)
            self._task = None

    async def process_frame(self, frame: Frame):
        await super().process_frame(frame)

        if isinstance(frame, TranscriptionFrame):
            if frame.text:
                self._has_speech = True
                self._got_final = True
                self._text = frame.text
                self._last_activity_time = time.time()
                self._event.set()
                logger.debug(f"[TranscriptionTimeout] final: {frame.text!r}")
        elif isinstance(frame, InterimTranscriptionFrame):
            if frame.text:
                self._has_speech = True
                if not self._text:
                    self._text = frame.text
                self._last_activity_time = time.time()
                self._event.set()
                logger.debug(f"[TranscriptionTimeout] interim: {frame.text!r}")

    async def _task_handler(self):
        while True:
            try:
                await asyncio.wait_for(self._event.wait(), timeout=self._timeout)
                self._event.clear()
            except asyncio.TimeoutError:
                await self._maybe_trigger()

    async def _maybe_trigger(self):
        if self._got_final or not self._has_speech:
            return
        elapsed = time.time() - self._last_activity_time
        if elapsed >= self._timeout:
            logger.info(
                f"[TranscriptionTimeout] triggering end-of-turn after "
                f"{elapsed:.1f}s inactivity, text={self._text!r}"
            )
            await self.trigger_user_turn_stopped()
