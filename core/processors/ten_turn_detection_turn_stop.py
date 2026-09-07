import re
from typing import Optional, Tuple

import httpx
from pipecat.utils.asyncio.task_manager import BaseTaskManager
from pydantic import BaseModel

from core.processors.text_turn_detection_turn_stop import (
    TextTurnDetectionUserTurnStopStrategy,
    TurnDecision,
)

PUNCTUATION = re.compile(r"[,，.。!！?？:：;；、]")

LABELS = (
    ("unfinished", TurnDecision.INCOMPLETE),
    ("wait", TurnDecision.WAIT),
    ("finished", TurnDecision.COMPLETE),
)


class TENTurnDetectionParams(BaseModel):
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "TEN_Turn_Detection"
    model: str = "TEN_Turn_Detection"
    temperature: float = 0.1
    top_p: float = 0.1
    request_timeout: float = 2.0
    strip_punctuation: bool = True


class TENTurnDetectionUserTurnStopStrategy(TextTurnDetectionUserTurnStopStrategy):
    def __init__(
        self,
        *,
        params: Optional[TENTurnDetectionParams] = None,
        client: Optional[httpx.AsyncClient] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._params = params or TENTurnDetectionParams()
        self._client = client
        self._owns_client = client is None
        self._url = f"{self._params.base_url.rstrip('/')}/chat/completions"
        self._headers = {"Authorization": f"Bearer {self._params.api_key}"}

    @property
    def params(self) -> TENTurnDetectionParams:
        return self._params

    async def setup(self, task_manager: BaseTaskManager):
        await super().setup(task_manager)
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._params.request_timeout)

    async def cleanup(self):
        await super().cleanup()
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def predict(self, text: str, language: Optional[str]) -> Tuple[TurnDecision, float]:
        client = self._client
        if client is None:
            raise RuntimeError(f"{self} used before setup()")
        content = PUNCTUATION.sub("", text) if self._params.strip_punctuation else text
        payload = {
            "model": self._params.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 1,
            "temperature": self._params.temperature,
            "top_p": self._params.top_p,
            "stream": False,
        }
        response = await client.post(
            self._url, json=payload, headers=self._headers, timeout=self._params.request_timeout
        )
        response.raise_for_status()
        data = response.json()
        label = (data["choices"][0]["message"]["content"] or "").strip().lower()
        decision = next((d for word, d in LABELS if label.startswith(word)), TurnDecision.COMPLETE)
        return decision, 1.0 if decision == TurnDecision.COMPLETE else 0.0
