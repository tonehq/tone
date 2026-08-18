"""Tests for the Google Gemini embedding provider — mirrors the OpenAI
coverage: provider is registered, get_embedder resolves it, build_embedder_from_run
carries model/dimensions through, and embed_texts batches while preserving
input order. Live API calls are gated behind the `integration` marker so the
default suite runs offline.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# All tests below patch `google.genai.Client` — skip cleanly if the SDK is
# absent (build-time trimmed image, offline CI) instead of erroring on a
# None-typed patch target.
pytest.importorskip("google.genai")

from core.services.rag.embedder_factory import (
    EMBEDDERS,
    build_embedder_from_run,
    get_embedder,
)
from core.services.rag.embedders import GoogleEmbedder


def _fake_embedding(dim: int, seed: float) -> SimpleNamespace:
    return SimpleNamespace(values=[seed + i * 0.001 for i in range(dim)])


def _fake_response(dim: int, seeds: list[float]) -> SimpleNamespace:
    return SimpleNamespace(embeddings=[_fake_embedding(dim, s) for s in seeds])


def test_google_provider_is_registered():
    assert "google" in EMBEDDERS
    assert EMBEDDERS["google"] is GoogleEmbedder


def test_get_embedder_google_builds_instance():
    e = get_embedder("google", model="gemini-embedding-001", api_key="fake")
    assert isinstance(e, GoogleEmbedder)
    assert e.provider == "google"
    assert e.model == "gemini-embedding-001"
    # No explicit dimensions passed → fall back to catalogued native size.
    assert e.dimensions == GoogleEmbedder._MODEL_NATIVE_DIMENSIONS["gemini-embedding-001"]


def test_build_embedder_from_run_google():
    class FakeRun:
        embedding_provider = "google"
        embedding_model = "gemini-embedding-001"
        embedding_dimensions = 3072
        embedding_config = {"batch_size": 25, "max_retries": 2}

    e = build_embedder_from_run(FakeRun(), api_key="fake")
    assert isinstance(e, GoogleEmbedder)
    assert e.model == "gemini-embedding-001"
    assert e.dimensions == 3072
    assert e.batch_size == 25
    assert e.max_retries == 2


def test_embed_texts_batches_and_preserves_order():
    fake_client = MagicMock()

    call_seeds = [
        [0.10, 0.11],
        [0.20],
    ]

    def _side_effect(*, model, contents, config):
        assert model == "gemini-embedding-001"
        assert config.task_type == "RETRIEVAL_DOCUMENT"
        assert config.output_dimensionality == 8
        seeds = call_seeds.pop(0)
        assert len(contents) == len(seeds)
        return _fake_response(dim=8, seeds=seeds)

    fake_client.models.embed_content.side_effect = _side_effect

    with patch("core.services.rag.embedders.google_genai.Client", return_value=fake_client):
        embedder = GoogleEmbedder(
            api_key="fake",
            model="gemini-embedding-001",
            dimensions=8,
            batch_size=2,
        )
        vectors = embedder.embed_texts(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(v) == 8 for v in vectors)
    # Order preserved: first two seeds from call 1, third from call 2.
    assert vectors[0][0] == pytest.approx(0.10)
    assert vectors[1][0] == pytest.approx(0.11)
    assert vectors[2][0] == pytest.approx(0.20)
    assert fake_client.models.embed_content.call_count == 2


def test_embed_query_uses_retrieval_query_task_type():
    fake_client = MagicMock()

    captured = {}

    def _side_effect(*, model, contents, config):
        captured["task_type"] = config.task_type
        return _fake_response(dim=4, seeds=[0.5])

    fake_client.models.embed_content.side_effect = _side_effect

    with patch("core.services.rag.embedders.google_genai.Client", return_value=fake_client):
        embedder = GoogleEmbedder(api_key="fake", dimensions=4)
        vec = embedder.embed_query("hello")

    assert captured["task_type"] == "RETRIEVAL_QUERY"
    assert len(vec) == 4


@pytest.mark.integration
def test_live_gemini_embedding():
    """Hits the real Gemini API — skipped unless `-m integration` is passed
    and GOOGLE_API_KEY is exported."""
    import os

    pytest.importorskip("google.genai")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set")

    embedder = GoogleEmbedder(api_key=api_key, model="gemini-embedding-001", dimensions=3072)
    vectors = embedder.embed_texts(["The quick brown fox jumps over the lazy dog."])
    assert len(vectors) == 1
    assert len(vectors[0]) == 3072
