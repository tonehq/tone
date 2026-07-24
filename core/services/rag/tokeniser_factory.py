"""Tokeniser (chunker) factory — resolves a tokeniser slug (from
``ingestion_pipeline_runs.tokeniser``) to an instantiated ``Chunker``.

Named "tokeniser" externally to match the pipeline-run schema; internally the
returned objects are ``Chunker`` implementations that decide how documents are
split into embeddable pieces. Adding a tokeniser = subclass ``Chunker`` in
``chunkers.py`` (or elsewhere) then ``register_tokeniser("slug", MyChunker)``.
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from core.services.rag.chunkers import (
    Chunker,
    DoclingHybridChunker,
    RecursiveCharacterChunker,
    TokenAwareChunker,
)
from core.services.rag.errors import UnknownTokeniserError


class _TokenAwareChunkerAdapter(TokenAwareChunker):
    """Registry adapter for ``TokenAwareChunker`` — its constructor wants a live
    ``Tokenizer`` instance, but a JSON run_config can only carry plain values.
    This shim accepts ``tokenizer_model`` (an OpenAI model slug like
    ``text-embedding-3-small`` or a HuggingFace model id like
    ``sentence-transformers/all-MiniLM-L6-v2``) plus ``max_tokens`` /
    ``overlap_tokens`` and builds the tokenizer via ``get_tokenizer`` before
    delegating to the base class."""

    def __init__(
        self,
        tokenizer_model: Optional[str] = None,
        max_tokens: int = 512,
        overlap_tokens: int = 64,
    ):
        from core.services.rag.tokenizers import get_tokenizer

        super().__init__(
            tokenizer=get_tokenizer(tokenizer_model),
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )


TOKENISERS: Dict[str, Type[Chunker]] = {
    "docling_hybrid": DoclingHybridChunker,
    "recursive_char": RecursiveCharacterChunker,
    "token_aware": _TokenAwareChunkerAdapter,
}


def register_tokeniser(name: str, cls: Type[Chunker]) -> None:
    TOKENISERS[name] = cls


def get_tokeniser(name: str, *, config: Optional[dict] = None) -> Chunker:
    try:
        tokeniser_cls = TOKENISERS[name]
    except KeyError:
        raise UnknownTokeniserError(
            f"Unknown tokeniser: {name!r}. Available: {sorted(TOKENISERS)}"
        )
    return tokeniser_cls(**(config or {}))
