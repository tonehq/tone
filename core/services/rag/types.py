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
    # Optional source-position metadata. Set by chunkers that know where each
    # chunk sits in the original document (chonkie exposes these on its own
    # Chunk objects) so downstream features like source-excerpt highlighting
    # and diff-based re-ingest can locate the span without re-parsing. None
    # for chunkers that don't track positions (e.g. Docling's HybridChunker).
    start_index: Optional[int] = None
    end_index: Optional[int] = None


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
