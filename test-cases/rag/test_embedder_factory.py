"""Factory registry tests — all four factories share the same "unknown name
raises UnknownXxxError" contract. Adding a provider / parser / tokeniser /
vector-store slug must never require a core edit."""

import pytest

from core.services.rag.embedder_factory import (
    EMBEDDERS,
    build_embedder_from_run,
    get_embedder,
    register_embedder,
)
from core.services.rag.embedders import Embedder
from core.services.rag.errors import (
    EmbeddingProviderUnavailableError,
    UnknownParserError,
    UnknownTokeniserError,
)
from core.services.rag.parser_factory import get_parser
from core.services.rag.tokeniser_factory import get_tokeniser


class StubEmbedder(Embedder):
    provider = "stub"
    dimensions = 4
    model = "stub-m"

    def __init__(self, api_key: str, model: str = "stub-m", dimensions: int = 4, **kwargs):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    def embed_texts(self, texts):
        return [[0.1] * self.dimensions for _ in texts]


def test_get_embedder_unknown_provider_raises():
    with pytest.raises(EmbeddingProviderUnavailableError):
        get_embedder("nosuch", model="x", api_key="k")


def test_register_embedder_lets_new_provider_resolve():
    register_embedder("stub", StubEmbedder)
    try:
        e = get_embedder("stub", model="stub-m", api_key="key")
        assert isinstance(e, StubEmbedder)
        assert e.dimensions == 4
    finally:
        EMBEDDERS.pop("stub", None)


def test_build_embedder_from_run_passes_dimensions():
    register_embedder("stub", StubEmbedder)
    try:
        class FakeRun:
            embedding_provider = "stub"
            embedding_model = "stub-m"
            embedding_dimensions = 7

        e = build_embedder_from_run(FakeRun(), api_key="k")
        assert e.dimensions == 7
    finally:
        EMBEDDERS.pop("stub", None)


def test_get_parser_unknown_raises():
    with pytest.raises(UnknownParserError):
        get_parser("nosuch")


def test_get_tokeniser_unknown_raises():
    with pytest.raises(UnknownTokeniserError):
        get_tokeniser("nosuch")
