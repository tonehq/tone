"""Chonkie-backed ``Chunker`` implementations.

Each class in this module wraps one strategy from the ``chonkie`` package and
adapts its output to Tone's :class:`~core.services.rag.types.Chunk` shape. They
are registered in :mod:`core.services.rag.tokeniser_factory` under the
``chonkie_*`` slugs; the factory instantiates them with ``**tokeniser_config``
JSON, so every constructor argument is a plain kwarg with a safe default.

Chonkie's ``Chunk`` objects carry ``text``, ``start_index``, ``end_index``,
``token_count``, etc.; only ``text`` flows into Tone's pipeline (the RAG
embedder re-tokenises downstream, so token counts here are informational).
"""

from __future__ import annotations

from typing import List

from chonkie import (
    RecursiveChunker as _ChonkieRecursive,
    SemanticChunker as _ChonkieSemantic,
    SentenceChunker as _ChonkieSentence,
)
from loguru import logger

from core.services.rag.chunkers import Chunker
from core.services.rag.types import Chunk, Document


def _to_tone_chunks(raw_chunks) -> List[Chunk]:
    """Convert chonkie ``Chunk`` objects to Tone ``Chunk`` objects, filtering
    empty/whitespace-only outputs and re-indexing sequentially so downstream
    ``chunk_index`` columns stay dense."""
    out: List[Chunk] = []
    for ch in raw_chunks:
        text = getattr(ch, "text", "") or ""
        if text.strip():
            out.append(Chunk(index=len(out), text=text))
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
        self.chunk_size = chunk_size
        self.tokenizer = tokenizer
        self.min_characters_per_chunk = min_characters_per_chunk
        self._chunker = _ChonkieRecursive(
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
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.min_characters_per_sentence = min_characters_per_sentence
        self._chunker = _ChonkieSentence(
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
    """

    _default_embedding_model = "minishlab/potion-base-32M"

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
        self.chunk_size = chunk_size
        self.embedding_model = embedding_model
        self.threshold = threshold
        self.similarity_window = similarity_window
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.min_characters_per_sentence = min_characters_per_sentence
        self.skip_window = skip_window
        self._chunker = _ChonkieSemantic(
            embedding_model=embedding_model,
            threshold=threshold,
            chunk_size=chunk_size,
            similarity_window=similarity_window,
            min_sentences_per_chunk=min_sentences_per_chunk,
            min_characters_per_sentence=min_characters_per_sentence,
            skip_window=skip_window,
        )

    def chunk(self, document: Document) -> List[Chunk]:
        logger.debug(
            "[chonkie:semantic] input chars={} chunk_size={} threshold={} embedding_model={}",
            len(document.text), self.chunk_size, self.threshold, self.embedding_model,
        )
        if not document.text or not document.text.strip():
            return []
        try:
            raw = self._chunker.chunk(document.text)
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
    documents by merging non-adjacent similar groups.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        embedding_model: str = ChonkieSemanticChunker._default_embedding_model,
        threshold: float = 0.8,
        similarity_window: int = 3,
        min_sentences_per_chunk: int = 1,
        min_characters_per_sentence: int = 24,
        skip_window: int = 1,
    ):
        super().__init__(
            chunk_size=chunk_size,
            embedding_model=embedding_model,
            threshold=threshold,
            similarity_window=similarity_window,
            min_sentences_per_chunk=min_sentences_per_chunk,
            min_characters_per_sentence=min_characters_per_sentence,
            skip_window=skip_window,
        )
