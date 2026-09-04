"""Chonkie-backed ``Chunker`` implementations.

Each class in this module wraps one strategy from the ``chonkie`` package and
adapts its output to Tone's :class:`~core.services.rag.types.Chunk` shape. They
are registered in :mod:`core.services.rag.tokeniser_factory` under the
``chonkie_*`` slugs; the factory instantiates them with ``**tokeniser_config``
JSON, so every constructor argument is a plain kwarg with a safe default.

Chonkie's ``Chunk`` objects carry ``text``, ``start_index``, ``end_index``,
``token_count``, etc. ``text``/``start_index``/``end_index`` flow through to
Tone's :class:`~core.services.rag.types.Chunk`; token counts are informational
(the RAG embedder re-tokenises downstream).

Chonkie itself is imported lazily (on first chunker construction, not at module
top): importing this module — which happens at API-pod startup via
``tokeniser_factory`` — must NOT pull chonkie and its heavy transitive deps
(nltk, scikit-learn, torch) into API pods that never chunk. The module still
loads and all four ``Chunker`` classes still exist so ``tokeniser_factory``'s
``TOKENISERS`` registry can be built (keeping every non-chonkie tokeniser —
docling_hybrid, recursive_char, token_aware — fully functional) even when
chonkie isn't installed. Attempting to actually instantiate a ``Chonkie*Chunker``
without the package raises a clear :class:`RuntimeError` at ``__init__`` time.
The embedding-based variants additionally defer construction of the underlying
chonkie chunker to the first ``chunk()`` call so a first-time HuggingFace model
download can't block worker startup or non-semantic tokeniser use.
"""

from __future__ import annotations

from typing import Any, List, Optional

from loguru import logger

from core.services.rag.chunkers import Chunker
from core.services.rag.types import Chunk, Document

class _ChonkieDependencyError(RuntimeError):
    """Raised when a chonkie chunker is instantiated but the ``chonkie``
    package (or the relevant extras) is not installed. Kept as a distinct
    class so callers can distinguish install/env problems from real chunking
    failures."""


# Resolved chonkie chunker classes are cached here after the first successful
# import; ``_CHONKIE_MISSING`` marks a class chonkie couldn't provide so a
# failed import isn't retried on every construction.
_CHONKIE_MISSING = object()
_CHONKIE_CACHE: dict = {}


def _load_chonkie(class_name: str, dep_label: str) -> Any:
    """Import a chonkie chunker class on first use and return it.

    chonkie is imported lazily (NOT at module top) so importing this module —
    which happens at API-pod startup via ``tokeniser_factory`` — does not pull
    chonkie and its heavy transitive deps (nltk, scikit-learn, torch) into API
    pods that never chunk. Only the ingestion worker, which actually constructs
    a chonkie chunker, pays that import cost.

    Raises :class:`_ChonkieDependencyError` if chonkie (or the relevant extras)
    is not installed — preserving the previous fail-fast behaviour.
    """
    cached = _CHONKIE_CACHE.get(class_name)
    if cached is None:
        try:
            import chonkie

            cached = getattr(chonkie, class_name)
        except Exception:  # ImportError, or missing attr on a partial install
            cached = _CHONKIE_MISSING
        _CHONKIE_CACHE[class_name] = cached
    if cached is _CHONKIE_MISSING:
        raise _ChonkieDependencyError(
            f"{dep_label} is not available. Install `chonkie` (and the "
            "`chonkie[semantic]` extras for the semantic/SDPM variants) to "
            "use this tokeniser."
        )
    return cached


def _to_tone_chunks(raw_chunks) -> List[Chunk]:
    """Convert chonkie ``Chunk`` objects to Tone ``Chunk`` objects, filtering
    empty/whitespace-only outputs and re-indexing sequentially so downstream
    ``chunk_index`` columns stay dense. Preserves ``start_index`` / ``end_index``
    when the chonkie chunk provides them (used later for source-excerpt UI)."""
    out: List[Chunk] = []
    for ch in raw_chunks:
        text = getattr(ch, "text", "") or ""
        if not text.strip():
            continue
        start = getattr(ch, "start_index", None)
        end = getattr(ch, "end_index", None)
        out.append(
            Chunk(
                index=len(out),
                text=text,
                start_index=start if isinstance(start, int) else None,
                end_index=end if isinstance(end, int) else None,
            )
        )
    return out


class ChonkieRecursiveChunker(Chunker):
    """Hierarchical recursive splitter (chonkie ``RecursiveChunker``).

    General-purpose default; safer to use than character-only splitting because
    it respects paragraph/sentence structure via chonkie's ``RecursiveRules``.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        tokenizer: str = "character",
        min_characters_per_chunk: int = 24,
    ):
        recursive_cls = _load_chonkie("RecursiveChunker", "chonkie RecursiveChunker")
        self.chunk_size = chunk_size
        self.tokenizer = tokenizer
        self.min_characters_per_chunk = min_characters_per_chunk
        self._chunker = recursive_cls(
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            min_characters_per_chunk=min_characters_per_chunk,
        )

    def chunk(self, document: Document) -> List[Chunk]:
        logger.debug(
            "[chonkie:recursive] input chars={} chunk_size={} tokenizer={}",
            len(document.text), self.chunk_size, self.tokenizer,
        )
        if not document.text or not document.text.strip():
            return []
        try:
            raw = self._chunker.chunk(document.text)
        except Exception:
            logger.exception(
                "[chonkie:recursive] chunk failed chars={} chunk_size={}",
                len(document.text), self.chunk_size,
            )
            raise
        chunks = _to_tone_chunks(raw)
        logger.info(
            "[chonkie:recursive] produced {} chunks (chunk_size={}, tokenizer={})",
            len(chunks), self.chunk_size, self.tokenizer,
        )
        return chunks


class ChonkieSentenceChunker(Chunker):
    """Sentence-boundary aware chunker (chonkie ``SentenceChunker``).

    Best fit for prose and call transcripts — never cuts mid-sentence, which
    materially improves retrieval quality on conversational content.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        tokenizer: str = "character",
        min_sentences_per_chunk: int = 1,
        min_characters_per_sentence: int = 12,
    ):
        sentence_cls = _load_chonkie("SentenceChunker", "chonkie SentenceChunker")
        # Chonkie's SentenceChunker raises ValueError deep inside the SDK
        # when overlap >= size; catch it early with a clearer message so a
        # bad tokeniser_config fails fast with a message the user can act on.
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than "
                f"chunk_size ({chunk_size})."
            )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.min_characters_per_sentence = min_characters_per_sentence
        self._chunker = sentence_cls(
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_sentences_per_chunk=min_sentences_per_chunk,
            min_characters_per_sentence=min_characters_per_sentence,
        )

    def chunk(self, document: Document) -> List[Chunk]:
        logger.debug(
            "[chonkie:sentence] input chars={} chunk_size={} overlap={}",
            len(document.text), self.chunk_size, self.chunk_overlap,
        )
        if not document.text or not document.text.strip():
            return []
        try:
            raw = self._chunker.chunk(document.text)
        except Exception:
            logger.exception(
                "[chonkie:sentence] chunk failed chars={} chunk_size={}",
                len(document.text), self.chunk_size,
            )
            raise
        chunks = _to_tone_chunks(raw)
        logger.info(
            "[chonkie:sentence] produced {} chunks (chunk_size={}, overlap={})",
            len(chunks), self.chunk_size, self.chunk_overlap,
        )
        return chunks


class ChonkieSemanticChunker(Chunker):
    """Embedding-similarity clustering (chonkie ``SemanticChunker``).

    Higher retrieval recall on domain-specific corpora at the cost of slower
    ingestion; the local ``minishlab/potion-*`` model runs on CPU and pulls no
    third-party API keys.

    The underlying chonkie chunker downloads a small HuggingFace model the
    first time it's constructed. We defer construction until the first
    ``chunk()`` call so worker startup can't hang on a network fetch and
    other tokenisers in the registry aren't affected by a failed download.
    """

    _default_embedding_model = "minishlab/potion-base-32M"
    # Names of kwargs this class forwards to chonkie's SemanticChunker. Kept
    # as a single source of truth so subclasses (SDPM) can override defaults
    # via **kwargs without duplicating the whole signature (signature drift
    # was flagged in review).
    _CHONKIE_KWARGS = (
        "chunk_size",
        "embedding_model",
        "threshold",
        "similarity_window",
        "min_sentences_per_chunk",
        "min_characters_per_sentence",
        "skip_window",
    )

    def __init__(
        self,
        chunk_size: int = 512,
        embedding_model: str = _default_embedding_model,
        threshold: float = 0.8,
        similarity_window: int = 3,
        min_sentences_per_chunk: int = 1,
        min_characters_per_sentence: int = 24,
        skip_window: int = 0,
    ):
        # Fail fast if the semantic extras aren't installed (matches previous
        # behaviour); the actual chunker is still built lazily in _get_chunker
        # so a first-time model download can't block worker startup.
        _load_chonkie(
            "SemanticChunker", "chonkie SemanticChunker (chonkie[semantic] extras)"
        )
        self.chunk_size = chunk_size
        self.embedding_model = embedding_model
        self.threshold = threshold
        self.similarity_window = similarity_window
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.min_characters_per_sentence = min_characters_per_sentence
        self.skip_window = skip_window
        self._chunker: Optional[Any] = None  # lazy — see class docstring

    def _get_chunker(self) -> Any:
        if self._chunker is None:
            semantic_cls = _load_chonkie(
                "SemanticChunker", "chonkie SemanticChunker (chonkie[semantic] extras)"
            )
            self._chunker = semantic_cls(
                **{k: getattr(self, k) for k in self._CHONKIE_KWARGS}
            )
        return self._chunker

    def chunk(self, document: Document) -> List[Chunk]:
        logger.debug(
            "[chonkie:semantic] input chars={} chunk_size={} threshold={} embedding_model={}",
            len(document.text), self.chunk_size, self.threshold, self.embedding_model,
        )
        if not document.text or not document.text.strip():
            return []
        try:
            raw = self._get_chunker().chunk(document.text)
        except Exception:
            logger.exception(
                "[chonkie:semantic] chunk failed chars={} chunk_size={} embedding_model={}",
                len(document.text), self.chunk_size, self.embedding_model,
            )
            raise
        chunks = _to_tone_chunks(raw)
        logger.info(
            "[chonkie:semantic] produced {} chunks (chunk_size={}, threshold={})",
            len(chunks), self.chunk_size, self.threshold,
        )
        return chunks


class ChonkieSdpmChunker(ChonkieSemanticChunker):
    """Semantic Double-Pass Merging preset (chonkie ``SemanticChunker`` with
    ``skip_window > 0``).

    Recovers coherence when the plain semantic pass over-splits long-form
    documents by merging non-adjacent similar groups. Delegates to the parent
    via ``**kwargs`` so any future param added to
    :class:`ChonkieSemanticChunker` propagates automatically — only the
    ``skip_window`` default differs.
    """

    def __init__(self, *, skip_window: int = 1, **kwargs: Any):
        super().__init__(skip_window=skip_window, **kwargs)
