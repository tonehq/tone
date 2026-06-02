from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import openai
from loguru import logger


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

    def __init__(self, api_key: str, model: str = None, batch_size: int = 100):
        self.api_key = api_key
        self.model = model or self.MODEL
        self.batch_size = batch_size

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        client = openai.OpenAI(api_key=self.api_key)
        out: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            response = client.embeddings.create(model=self.model, input=batch)
            out.extend(item.embedding for item in response.data)
        logger.info(
            "Generated {} embeddings (model={}, dimensions={})",
            len(out), self.model, len(out[0]) if out else 0,
        )
        return out
