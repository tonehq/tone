import asyncio
import unittest
from unittest.mock import patch

import numpy as np
from pipecat.frames.frames import TranscriptionFrame
from pipecat.transcriptions.language import Language
from pipecat.utils.asyncio.task_manager import TaskManager

from core.processors.livekit_turn_detector_turn_stop import (
    LiveKitTurnDetectorModel,
    LiveKitTurnDetectorParams,
    LiveKitTurnDetectorUserTurnStopStrategy,
)
from core.processors.text_turn_detection_turn_stop import TurnDecision


class FakeEncoding:
    def __init__(self, ids):
        self.ids = ids


class FakeTokenizer:
    def __init__(self):
        self.texts = []

    def encode(self, text, add_special_tokens=False):
        self.texts.append(text)
        return FakeEncoding(list(range(len(text.split()))))


class FakeSession:
    def __init__(self, probability):
        self.probability = probability
        self.inputs = []

    def run(self, outputs, feeds):
        self.inputs.append(feeds["input_ids"])
        return [np.array([[0.01, self.probability]], dtype=np.float32)]


class FakeContext:
    def __init__(self, messages):
        self._messages = messages

    def get_messages(self):
        return self._messages


def make_model(probability=0.5, normalize=True, languages=None):
    model = LiveKitTurnDetectorModel.__new__(LiveKitTurnDetectorModel)
    model._session = FakeSession(probability)
    model._tokenizer = FakeTokenizer()
    model._languages = (
        languages
        if languages is not None
        else {"en": {"threshold": 0.011}, "hi": {"threshold": 0.0398}}
    )
    model._normalize = normalize
    return model


class TestLiveKitTurnDetectorModel(unittest.TestCase):
    def test_multilingual_normalization(self):
        model = make_model()
        self.assertEqual(
            model.normalize_text("Hello,  WORLD! It's  well-known."), "hello world it's well-known"
        )

    def test_english_variant_keeps_raw_text(self):
        model = make_model(normalize=False)
        self.assertEqual(model.normalize_text("Hello, World!"), "Hello, World!")

    def test_format_chat_merges_adjacent_roles_and_leaves_last_turn_open(self):
        model = make_model()
        text = model.format_chat(
            [
                {"role": "assistant", "content": "How can I help?"},
                {"role": "user", "content": "I need"},
                {"role": "user", "content": "a table"},
                {"role": "assistant", "content": ""},
            ]
        )
        self.assertEqual(
            text,
            "<|im_start|>assistant\nhow can i help<|im_end|>\n<|im_start|>user\ni need a table",
        )

    def test_threshold_lookup_falls_back_to_base_language(self):
        model = make_model()
        self.assertEqual(model.threshold("en-US"), 0.011)
        self.assertEqual(model.threshold("hi"), 0.0398)
        self.assertIsNone(model.threshold("xx"))
        self.assertIsNone(model.threshold(None))

    def test_predict_left_truncates_and_returns_last_probability(self):
        model = make_model(probability=0.42)

        probability = model.predict(
            [{"role": "user", "content": "one two three four five"}], max_tokens=3
        )

        self.assertAlmostEqual(probability, 0.42, places=5)
        fed = model._session.inputs[0]
        self.assertEqual(fed.dtype, np.int64)
        self.assertEqual(fed.shape, (1, 3))
        self.assertEqual(fed.tolist(), [[3, 4, 5]])


class TestLiveKitTurnDetectorUserTurnStopStrategy(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.task_manager = TaskManager()

    async def _create(self, model, **kwargs):
        with patch.object(LiveKitTurnDetectorModel, "load", return_value=model):
            strategy = LiveKitTurnDetectorUserTurnStopStrategy(unfinished_timeout=0.1, **kwargs)
            await strategy.setup(self.task_manager)
        return strategy

    async def test_history_from_context_feeds_model(self):
        model = make_model(probability=0.5)
        context = FakeContext(
            [
                {"role": "system", "content": "rules"},
                {"role": "assistant", "content": [{"type": "text", "text": "Hi there"}]},
                {"role": "user", "content": "I want"},
            ]
        )
        strategy = await self._create(model, context=context)

        decision, probability = await strategy.predict("a table", "en")
        await strategy.cleanup()

        self.assertEqual(decision, TurnDecision.COMPLETE)
        self.assertEqual(probability, 0.5)
        prompt = model._tokenizer.texts[0]
        self.assertIn("<|im_start|>assistant\nhi there<|im_end|>", prompt)
        self.assertTrue(prompt.endswith("<|im_start|>user\ni want a table"))
        self.assertNotIn("rules", prompt)

    async def test_history_is_truncated_to_max_turns(self):
        model = make_model(probability=0.5)
        context = FakeContext(
            [{"role": "user" if i % 2 else "assistant", "content": f"turn {i}"} for i in range(10)]
        )
        strategy = await self._create(
            model, context=context, params=LiveKitTurnDetectorParams(max_history_turns=2)
        )

        await strategy.predict("last words", "en")
        await strategy.cleanup()

        prompt = model._tokenizer.texts[0]
        self.assertNotIn("turn 8", prompt)
        self.assertIn("turn 9 last words", prompt)

    async def test_below_threshold_is_incomplete(self):
        strategy = await self._create(make_model(probability=0.001))

        decision, _ = await strategy.predict("i want", "en")
        await strategy.cleanup()

        self.assertEqual(decision, TurnDecision.INCOMPLETE)

    async def test_threshold_override(self):
        strategy = await self._create(
            make_model(probability=0.3), params=LiveKitTurnDetectorParams(threshold=0.2)
        )

        decision, _ = await strategy.predict("i want", "xx")
        await strategy.cleanup()

        self.assertEqual(decision, TurnDecision.COMPLETE)

    async def test_unsupported_language_completes(self):
        strategy = await self._create(make_model(probability=0.0))

        decision, _ = await strategy.predict("i want", "xx")
        await strategy.cleanup()

        self.assertEqual(decision, TurnDecision.COMPLETE)

    async def test_transcript_language_selects_threshold(self):
        strategy = await self._create(make_model(probability=0.02))
        stopped = []

        @strategy.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(strategy, params):
            stopped.append(params)

        await strategy.process_frame(
            TranscriptionFrame(text="namaste", user_id="cat", timestamp="", language=Language.HI)
        )
        await asyncio.sleep(0.05)
        self.assertEqual(stopped, [])

        await asyncio.sleep(0.2)
        self.assertEqual(len(stopped), 1)
        await strategy.cleanup()
