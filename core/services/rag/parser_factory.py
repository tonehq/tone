"""Parser factory — resolves a parser slug (from ``ingestion_pipeline_runs.parser``)
to an instantiated ``DocumentReader``. Mirrors the shape of
``core/services/rag/factory.py`` for vector stores so every extension point
(parsers / tokenisers / embedders / vector stores) reads the same way.

Adding a parser = subclass ``DocumentReader`` in ``readers.py`` (or elsewhere)
then ``register_parser("slug", MyReader)``. No core edit required.
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from core.services.rag.errors import UnknownParserError
from core.services.rag.readers import (
    CompositeReader,
    DocumentReader,
    DocxReader,
    PdfReader,
    TextReader,
)
from core.services.rag.readers import DoclingReader

PARSERS: Dict[str, Type[DocumentReader]] = {
    "docling": DoclingReader,
    "pypdf": PdfReader,
    "docx": DocxReader,
    "text": TextReader,
    "composite": CompositeReader,
}


def register_parser(name: str, cls: Type[DocumentReader]) -> None:
    PARSERS[name] = cls


def get_parser(name: str, *, config: Optional[dict] = None) -> DocumentReader:
    try:
        parser_cls = PARSERS[name]
    except KeyError:
        raise UnknownParserError(
            f"Unknown parser: {name!r}. Available: {sorted(PARSERS)}"
        )
    return parser_cls(**(config or {}))
