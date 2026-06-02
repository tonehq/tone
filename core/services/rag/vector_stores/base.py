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
        self, embedding: List[float], top_k: int = 3, *, filters: Optional[dict] = None
    ) -> List[SearchResult]:
        ...

    @abstractmethod
    def delete(self, *, filters: dict) -> int:
        ...

    @abstractmethod
    def count(self, *, filters: Optional[dict] = None) -> int:
        ...
