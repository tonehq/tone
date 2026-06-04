from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import List

import openai
from loguru import logger

try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODING = None


def _count_tokens(texts: List[str]) -> int:
    if _ENCODING is None:
        return sum(len(t) // 4 + 1 for t in texts)
    return sum(len(_ENCODING.encode(t)) for t in texts)


class _TokenRateLimiter:
    def __init__(self, tokens_per_minute: int):
        self.limit = tokens_per_minute
        self.window = 60.0
        self._events: deque = deque()
        self._used = 0
        self._lock = threading.Lock()

    def acquire(self, tokens: int) -> None:
        with self._lock:
            while True:
                now = time.monotonic()
                while self._events and now - self._events[0][0] >= self.window:
                    self._used -= self._events.popleft()[1]
                if self._used + tokens <= self.limit or not self._events:
                    self._events.append((time.monotonic(), tokens))
                    self._used += tokens
                    return
                time.sleep(max(0.0, self.window - (now - self._events[0][0])))


_LIMITERS: dict = {}
_LIMITERS_LOCK = threading.Lock()


def _get_limiter(tokens_per_minute: int) -> _TokenRateLimiter:
    with _LIMITERS_LOCK:
        limiter = _LIMITERS.get(tokens_per_minute)
        if limiter is None:
            limiter = _TokenRateLimiter(tokens_per_minute)
            _LIMITERS[tokens_per_minute] = limiter
        return limiter


class Embedder(ABC):
    dimensions: int = 0

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]


class OpenAIEmbedder(Embedder):
    MODEL = "text-embedding-3-small"
    dimensions = 1536

    def __init__(self, api_key: str, model: str = None, batch_size: int = 100,
                 max_retries: int = 6, tokens_per_minute: int = 900_000):
        self.api_key = api_key
        self.model = model or self.MODEL
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._limiter = _get_limiter(tokens_per_minute)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        client = openai.OpenAI(api_key=self.api_key, max_retries=self.max_retries)
        out: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            self._limiter.acquire(_count_tokens(batch))
            response = client.embeddings.create(model=self.model, input=batch)
            out.extend(item.embedding for item in response.data)
        logger.info(
            "Generated {} embeddings (model={}, dimensions={})",
            len(out), self.model, len(out[0]) if out else 0,
        )
        return out
