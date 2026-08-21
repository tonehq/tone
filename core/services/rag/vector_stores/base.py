from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.services.rag.types import SearchResult, VectorRecord


class VectorStore(ABC):
    @abstractmethod
    def add(self, records: List[VectorRecord]) -> int:
        ...

    @abstractmethod
    def query(
        self,
        embedding: List[float],
        top_k: int = 3,
        *,
        filters: Optional[dict] = None,
        query_text: Optional[str] = None,
    ) -> List[SearchResult]:
        """Similarity search. ``query_text`` is used ONLY for observability
        (log line for the search); implementations must not use it for
        matching. Optional so pre-existing callers stay valid."""
        ...

    @abstractmethod
    def delete(self, *, filters: dict) -> int:
        ...

    @abstractmethod
    def count(self, *, filters: Optional[dict] = None) -> int:
        ...
