"""Unit tests for the chonkie-backed chunkers registered under the
``chonkie_*`` slugs.

Recursive and Sentence chunkers are pure-CPU and always run. Semantic and SDPM
require the ``chonkie[semantic]`` extras plus a first-run model download
(``minishlab/potion-base-32M``); those tests skip gracefully if the extras
aren't installed or the model can't be fetched offline.
"""

from __future__ import annotations

import pytest

from core.services.rag.errors import UnknownTokeniserError
from core.services.rag.tokeniser_factory import TOKENISERS, get_tokeniser
from core.services.rag.types import Chunk, Document


SAMPLE_PROSE = (
    "Voice agents are software programs that hold real-time spoken "
    "conversations. They combine speech-to-text, a language model, and "
    "text-to-speech into a single pipeline. Each stage can be swapped for "
    "a different provider. That flexibility is why Tone exists. "
) * 12  # ~1500 chars — enough to force multiple chunks at chunk_size=256.


def _assert_chunk_shape(chunks):
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for i, ch in enumerate(chunks):
        assert isinstance(ch, Chunk)
        assert ch.index == i, "Tone chunk indexes must be dense and sequential"
        assert isinstance(ch.text, str)
        assert ch.text.strip(), "empty/whitespace-only chunks must be filtered"


def test_all_four_chonkie_slugs_are_registered():
    for slug in ("chonkie_recursive", "chonkie_sentence", "chonkie_semantic", "chonkie_sdpm"):
        assert slug in TOKENISERS, f"missing chonkie slug: {slug}"


def test_get_tokeniser_unknown_chonkie_slug_raises():
    with pytest.raises(UnknownTokeniserError):
        get_tokeniser("chonkie_nosuch")


# ── recursive ────────────────────────────────────────────────────────────

def test_chonkie_recursive_produces_valid_chunks():
    chunker = get_tokeniser("chonkie_recursive", config={"chunk_size": 256})
    chunks = chunker.chunk(Document(text=SAMPLE_PROSE))
    _assert_chunk_shape(chunks)


def test_chonkie_recursive_empty_document_returns_empty_list():
    chunker = get_tokeniser("chonkie_recursive")
    assert chunker.chunk(Document(text="")) == []
    assert chunker.chunk(Document(text="   \n   ")) == []


# ── sentence ─────────────────────────────────────────────────────────────

def test_chonkie_sentence_produces_valid_chunks():
    chunker = get_tokeniser(
        "chonkie_sentence",
        config={"chunk_size": 256, "chunk_overlap": 0, "min_sentences_per_chunk": 1},
    )
    chunks = chunker.chunk(Document(text=SAMPLE_PROSE))
    _assert_chunk_shape(chunks)


def test_chonkie_sentence_empty_document_returns_empty_list():
    chunker = get_tokeniser("chonkie_sentence")
    assert chunker.chunk(Document(text="")) == []


# ── semantic / sdpm ──────────────────────────────────────────────────────
# These download minishlab/potion-base-32M on first construction. Skip
# gracefully in offline / no-extras environments so unit-test runs stay green.


def _build_semantic_or_skip(slug: str):
    pytest.importorskip("model2vec", reason="chonkie[semantic] extras not installed")
    try:
        return get_tokeniser(slug, config={"chunk_size": 256})
    except (OSError, RuntimeError) as e:  # HuggingFace network/download failures
        pytest.skip(f"{slug}: model unavailable offline ({e})")


def test_chonkie_semantic_produces_valid_chunks():
    chunker = _build_semantic_or_skip("chonkie_semantic")
    chunks = chunker.chunk(Document(text=SAMPLE_PROSE))
    _assert_chunk_shape(chunks)
    assert chunker.chunk(Document(text="")) == []


def test_chonkie_sdpm_produces_valid_chunks():
    chunker = _build_semantic_or_skip("chonkie_sdpm")
    chunks = chunker.chunk(Document(text=SAMPLE_PROSE))
    _assert_chunk_shape(chunks)
    # SDPM = SemanticChunker with skip_window>0
    assert chunker.skip_window >= 1
