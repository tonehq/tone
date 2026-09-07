import asyncio
import unittest

from pipecat.frames.frames import (
    InterimTranscriptionFrame,
    MetricsFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.transcriptions.language import Language
from pipecat.utils.asyncio.task_manager import TaskManager

from core.processors.text_turn_detection_turn_stop import (
    TextTurnDetectionUserTurnStopStrategy,
    TurnDecision,
)

UNFINISHED_TIMEOUT = 0.1
SETTLE = 0.05


class ScriptedStrategy(TextTurnDetectionUserTurnStopStrategy):
    def __init__(self, decisions, **kwargs):
        super().__init__(**kwargs)
        self._decisions = list(decisions)
        self.calls = []

    async def predict(self, text, language):
        self.calls.append((text, language))
        decision = self._decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision, 0.9 if decision == TurnDecision.COMPLETE else 0.1


class BlockingStrategy(TextTurnDetectionUserTurnStopStrategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.release = asyncio.Event()
        self.calls = 0

    async def predict(self, text, language):
        self.calls += 1
        await self.release.wait()
        return TurnDecision.COMPLETE, 1.0


class TestTextTurnDetectionUserTurnStopStrategy(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.task_manager = TaskManager()

    async def _create(self, decisions, **kwargs):
        strategy = ScriptedStrategy(decisions, unfinished_timeout=UNFINISHED_TIMEOUT, **kwargs)
        await strategy.setup(self.task_manager)
        stopped = []
        pushed = []

        @strategy.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(strategy, params):
            stopped.append(params)

        @strategy.event_handler("on_push_frame")
        async def on_push_frame(strategy, frame, direction):
            pushed.append(frame)

        return strategy, stopped, pushed

    async def _transcribe(self, strategy, text, language=None):
        await strategy.process_frame(
            TranscriptionFrame(text=text, user_id="cat", timestamp="", language=language)
        )
        await asyncio.sleep(SETTLE)

    async def test_complete_ends_turn_and_emits_metrics(self):
        strategy, stopped, pushed = await self._create([TurnDecision.COMPLETE])

        await strategy.process_frame(VADUserStartedSpeakingFrame())
        await self._transcribe(strategy, "book a table for two")

        self.assertEqual(len(stopped), 1)
        self.assertEqual(strategy.calls, [("book a table for two", None)])
        metrics = [f for f in pushed if isinstance(f, MetricsFrame)]
        self.assertEqual(len(metrics), 1)
        self.assertTrue(metrics[0].data[0].is_complete)
        self.assertEqual(metrics[0].data[0].probability, 0.9)
        await strategy.cleanup()

    async def test_incomplete_ends_turn_after_timeout(self):
        strategy, stopped, _ = await self._create([TurnDecision.INCOMPLETE])

        await self._transcribe(strategy, "i would like to")
        self.assertEqual(stopped, [])

        await asyncio.sleep(UNFINISHED_TIMEOUT + 0.1)
        self.assertEqual(len(stopped), 1)
        await strategy.cleanup()

    async def test_renewed_speech_cancels_timeout_and_accumulates_text(self):
        strategy, stopped, _ = await self._create(
            [TurnDecision.INCOMPLETE, TurnDecision.COMPLETE]
        )

        await self._transcribe(strategy, "i would like to")
        await strategy.process_frame(VADUserStartedSpeakingFrame())
        await asyncio.sleep(UNFINISHED_TIMEOUT + 0.1)
        self.assertEqual(stopped, [])

        await self._transcribe(strategy, "order a pizza")
        self.assertEqual(len(stopped), 1)
        self.assertEqual(strategy.calls[-1][0], "i would like to order a pizza")
        await strategy.cleanup()

    async def test_wait_keeps_turn_open(self):
        strategy, stopped, _ = await self._create([TurnDecision.WAIT])

        await self._transcribe(strategy, "hold on")
        await asyncio.sleep(UNFINISHED_TIMEOUT + 0.1)

        self.assertEqual(stopped, [])
        await strategy.cleanup()

    async def test_interim_cancels_pending_evaluation(self):
        strategy = BlockingStrategy(unfinished_timeout=UNFINISHED_TIMEOUT)
        await strategy.setup(self.task_manager)
        stopped = []

        @strategy.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(strategy, params):
            stopped.append(params)

        await strategy.process_frame(TranscriptionFrame(text="hello", user_id="cat", timestamp=""))
        await asyncio.sleep(SETTLE)
        await strategy.process_frame(
            InterimTranscriptionFrame(text="hello th", user_id="cat", timestamp="")
        )
        strategy.release.set()
        await asyncio.sleep(SETTLE)

        self.assertEqual(strategy.calls, 1)
        self.assertEqual(stopped, [])
        await strategy.cleanup()

    async def test_failure_ends_turn_and_skips_model_during_cooldown(self):
        strategy, stopped, _ = await self._create(
            [RuntimeError("boom"), TurnDecision.INCOMPLETE], failure_cooldown=5.0
        )

        await self._transcribe(strategy, "hello")
        self.assertEqual(len(stopped), 1)

        await strategy.handle_user_turn_stopped()
        await self._transcribe(strategy, "again")
        self.assertEqual(len(stopped), 2)
        self.assertEqual(len(strategy.calls), 1)
        await strategy.cleanup()

    async def test_turn_boundary_resets_text(self):
        strategy, stopped, _ = await self._create([TurnDecision.COMPLETE, TurnDecision.COMPLETE])

        await self._transcribe(strategy, "first")
        await strategy.handle_user_turn_stopped()
        await strategy.handle_user_turn_started()
        await self._transcribe(strategy, "second")

        self.assertEqual([c[0] for c in strategy.calls], ["first", "second"])
        self.assertEqual(len(stopped), 2)
        await strategy.cleanup()

    async def test_language_prefers_explicit_then_transcript(self):
        strategy, _, _ = await self._create([TurnDecision.COMPLETE])
        await self._transcribe(strategy, "namaste", language=Language.HI)
        self.assertEqual(strategy.calls[0][1], "hi")
        await strategy.cleanup()

        strategy, _, _ = await self._create([TurnDecision.COMPLETE], language="en-US")
        await self._transcribe(strategy, "namaste", language=Language.HI)
        self.assertEqual(strategy.calls[0][1], "en-US")
        await strategy.cleanup()
