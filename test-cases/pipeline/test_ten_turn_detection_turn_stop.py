import asyncio
import json
import unittest

import httpx
from pipecat.frames.frames import TranscriptionFrame
from pipecat.utils.asyncio.task_manager import TaskManager

from core.processors.ten_turn_detection_turn_stop import (
    TENTurnDetectionParams,
    TENTurnDetectionUserTurnStopStrategy,
)
from core.processors.text_turn_detection_turn_stop import TurnDecision


class TestTENTurnDetectionUserTurnStopStrategy(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.task_manager = TaskManager()
        self.requests = []
        self.label = "finished"
        self.status = 200
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self._handle))

    async def asyncTearDown(self):
        await self.client.aclose()

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            {
                "url": str(request.url),
                "authorization": request.headers.get("authorization"),
                "body": json.loads(request.content),
            }
        )
        if self.status != 200:
            return httpx.Response(self.status, text="boom")
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": self.label}}]}
        )

    async def _create(self, **overrides):
        params = TENTurnDetectionParams(
            base_url="http://ten.local/v1/", api_key="secret", model="ten-model", **overrides
        )
        strategy = TENTurnDetectionUserTurnStopStrategy(
            params=params, client=self.client, unfinished_timeout=0.1
        )
        await strategy.setup(self.task_manager)
        return strategy

    async def test_predict_sends_reference_payload(self):
        strategy = await self._create()

        decision, probability = await strategy.predict("Hello, I have a question!", None)
        await strategy.cleanup()

        self.assertEqual(decision, TurnDecision.COMPLETE)
        self.assertEqual(probability, 1.0)
        request = self.requests[0]
        self.assertEqual(request["url"], "http://ten.local/v1/chat/completions")
        self.assertEqual(request["authorization"], "Bearer secret")
        body = request["body"]
        self.assertEqual(body["model"], "ten-model")
        self.assertEqual(body["messages"], [{"role": "user", "content": "Hello I have a question"}])
        self.assertEqual(body["max_tokens"], 1)
        self.assertEqual(body["temperature"], 0.1)
        self.assertEqual(body["top_p"], 0.1)
        self.assertFalse(body["stream"])

    async def test_labels_map_to_decisions(self):
        strategy = await self._create()
        expectations = (
            ("unfinished", TurnDecision.INCOMPLETE),
            ("wait", TurnDecision.WAIT),
            ("finished", TurnDecision.COMPLETE),
            ("Finished.", TurnDecision.COMPLETE),
            ("something else", TurnDecision.COMPLETE),
        )

        for label, expected in expectations:
            self.label = label
            decision, _ = await strategy.predict("text", None)
            self.assertEqual(decision, expected, label)
        await strategy.cleanup()

    async def test_punctuation_kept_when_disabled(self):
        strategy = await self._create(strip_punctuation=False)

        await strategy.predict("Hello, there.", None)
        await strategy.cleanup()

        self.assertEqual(self.requests[0]["body"]["messages"][0]["content"], "Hello, there.")

    async def test_http_error_raises(self):
        strategy = await self._create()
        self.status = 500

        with self.assertRaises(httpx.HTTPStatusError):
            await strategy.predict("text", None)
        await strategy.cleanup()

    async def test_injected_client_is_not_closed(self):
        strategy = await self._create()
        await strategy.cleanup()
        self.assertFalse(self.client.is_closed)

    async def test_transcription_ends_turn_through_endpoint(self):
        strategy = await self._create()
        stopped = []

        @strategy.event_handler("on_user_turn_stopped")
        async def on_user_turn_stopped(strategy, params):
            stopped.append(params)

        await strategy.process_frame(
            TranscriptionFrame(text="Book a table", user_id="cat", timestamp="")
        )
        await asyncio.sleep(0.2)
        await strategy.cleanup()

        self.assertEqual(len(stopped), 1)
        self.assertEqual(self.requests[0]["body"]["messages"][0]["content"], "Book a table")
