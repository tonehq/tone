from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    text: str
    native: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    index: int
    text: str


@dataclass
class VectorRecord:
    text: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
