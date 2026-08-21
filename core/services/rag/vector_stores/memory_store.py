from __future__ import annotations

import math
from typing import List, Optional

from core.services.rag.types import SearchResult, VectorRecord
from core.services.rag.vector_stores.base import VectorStore


def _cosine_distance(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._records: List[VectorRecord] = []

    @staticmethod
    def _matches(metadata: dict, filters: Optional[dict]) -> bool:
        return all(metadata.get(k) == v for k, v in (filters or {}).items())

    def add(self, records: List[VectorRecord]) -> int:
        self._records.extend(records)
        return len(records)

    def query(
        self,
        embedding: List[float],
        top_k: int = 3,
        *,
        filters: Optional[dict] = None,
        query_text: Optional[str] = None,
    ) -> List[SearchResult]:
        # ``query_text`` accepted for protocol parity; the in-memory store is
        # test-only and doesn't emit search logs (the pgvector path owns the
        # canonical [pgvector.query] line).
        del query_text
        candidates = [r for r in self._records if self._matches(r.metadata, filters)]
        scored = sorted(
            ((_cosine_distance(embedding, r.embedding), r) for r in candidates),
            key=lambda t: t[0],
        )
        return [
            SearchResult(text=r.text, score=dist, metadata=r.metadata, id=r.id)
            for dist, r in scored[:top_k]
        ]

    def delete(self, *, filters: dict) -> int:
        before = len(self._records)
        self._records = [r for r in self._records if not self._matches(r.metadata, filters)]
        return before - len(self._records)

    def count(self, *, filters: Optional[dict] = None) -> int:
        return sum(1 for r in self._records if self._matches(r.metadata, filters))
