import asyncio
import time
from abc import abstractmethod
from enum import Enum
from typing import Optional, Tuple

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    MetricsFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.metrics.metrics import TurnMetricsData
from pipecat.turns.types import ProcessFrameResult
from pipecat.turns.user_stop.base_user_turn_stop_strategy import BaseUserTurnStopStrategy


class TurnDecision(Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    WAIT = "wait"


class TextTurnDetectionUserTurnStopStrategy(BaseUserTurnStopStrategy):
    def __init__(
        self,
        *,
        unfinished_timeout: float = 5.0,
        failure_cooldown: float = 10.0,
        language: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._unfinished_timeout = unfinished_timeout
        self._failure_cooldown = failure_cooldown
        self._language = language
        self._text = ""
        self._transcript_language: Optional[str] = None
        self._skip_until = 0.0
        self._eval_task: Optional[asyncio.Task] = None
        self._timeout_task: Optional[asyncio.Task] = None

    @property
    def language(self) -> Optional[str]:
        return self._language or self._transcript_language

    @property
    def text(self) -> str:
        return self._text

    @property
    def unfinished_timeout(self) -> float:
        return self._unfinished_timeout

    @abstractmethod
    async def predict(self, text: str, language: Optional[str]) -> Tuple[TurnDecision, float]:
        ...

    async def handle_user_turn_started(self):
        await self._reset()

    async def handle_user_turn_stopped(self):
        await self._reset()

    async def cleanup(self):
        await super().cleanup()
        await self._reset()

    async def process_frame(self, frame: Frame) -> ProcessFrameResult:
        if isinstance(frame, VADUserStartedSpeakingFrame):
            await self._cancel_tasks()
        elif isinstance(frame, InterimTranscriptionFrame):
            if frame.text:
                await self._cancel_tasks()
        elif isinstance(frame, TranscriptionFrame):
            await self._handle_transcription(frame)
        return ProcessFrameResult.CONTINUE

    async def _handle_transcription(self, frame: TranscriptionFrame):
        if not frame.text:
            return
        self._text = f"{self._text} {frame.text}".strip()
        if frame.language:
            self._transcript_language = str(frame.language)
        await self._cancel_tasks()
        self._eval_task = self.task_manager.create_task(
            self._evaluate(self._text), f"{self}::_evaluate"
        )

    async def _evaluate(self, text: str):
        started = time.perf_counter()
        if time.monotonic() < self._skip_until:
            decision, probability = TurnDecision.COMPLETE, 1.0
        else:
            try:
                decision, probability = await self.predict(text, self.language)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._skip_until = time.monotonic() + self._failure_cooldown
                logger.exception(
                    "[turn-detection] {} prediction failed, ending the turn and pausing for {}s",
                    self, self._failure_cooldown,
                )
                decision, probability = TurnDecision.COMPLETE, 1.0
        elapsed_ms = (time.perf_counter() - started) * 1000
        self._eval_task = None
        await self.push_frame(
            MetricsFrame(
                data=[
                    TurnMetricsData(
                        processor=self.name,
                        is_complete=decision == TurnDecision.COMPLETE,
                        probability=probability,
                        e2e_processing_time_ms=elapsed_ms,
                    )
                ]
            )
        )
        logger.debug(
            "[turn-detection] {} decision={} probability={:.4f} elapsed_ms={:.1f}",
            self, decision.value, probability, elapsed_ms,
        )
        if decision == TurnDecision.COMPLETE:
            await self.trigger_user_turn_stopped()
        elif decision == TurnDecision.INCOMPLETE:
            self._timeout_task = self.task_manager.create_task(
                self._timeout_handler(), f"{self}::_timeout_handler"
            )

    async def _timeout_handler(self):
        try:
            await asyncio.sleep(self._unfinished_timeout)
        except asyncio.CancelledError:
            return
        finally:
            self._timeout_task = None
        await self.trigger_user_turn_stopped()

    async def _cancel_tasks(self):
        if self._eval_task:
            await self.task_manager.cancel_task(self._eval_task)
            self._eval_task = None
        if self._timeout_task:
            await self.task_manager.cancel_task(self._timeout_task)
            self._timeout_task = None

    async def _reset(self):
        self._text = ""
        self._transcript_language = None
        await self._cancel_tasks()
