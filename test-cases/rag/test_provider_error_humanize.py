"""Negative/edge tests for the RAG provider-error humanizer
(``core/services/rag/errors.py``).

These lock in the security invariant that a raw provider exception (Google /
Vertex quota dump, OpenAI SDK envelope, an arbitrary dict/URL blob) is NEVER
surfaced verbatim to the UI — it is translated to a short, safe one-liner
BEFORE being stored on the ingestion run / upload. A typed ``RagError`` (which
already carries a curated message) passes straight through unchanged.
"""

from core.services.rag.errors import (
    EmbeddingProviderUnavailableError,
    humanize_ingestion_error,
    humanize_provider_error,
)


def test_google_quota_dump_is_reduced_to_clean_quota_line():
    """A raw Google/Vertex RESOURCE_EXHAUSTED dict must not leak any of its
    internal structure — only the curated quota one-liner reaches the UI."""
    raw = (
        "ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': "
        "'Quota exceeded for aiplatform.googleapis.com/global_embed_content_requests_per_minute_per_base_model "
        "with base model: gemini-embedding. Please submit a quota increase...'}}"
    )
    result = humanize_provider_error(Exception(raw))

    # No raw structure of any kind leaks.
    assert "{" not in result
    assert "googleapis" not in result
    assert "RESOURCE_EXHAUSTED" not in result
    assert "Traceback" not in result
    # And it IS the clean quota one-liner.
    assert "quota" in result.lower()


def test_openai_invalid_api_key_dump_is_reduced_to_clean_message():
    """OpenAI's stringified SDK envelope with an ``invalid_api_key`` code maps
    to a clean invalid-key sentence with no dict fragments."""
    raw = "Error code: 400 - {'error': {'message': '...', 'code': 'invalid_api_key'}}"
    result = humanize_provider_error(Exception(raw))

    assert "{" not in result
    assert "invalid api key" in result.lower()


def test_unknown_dict_or_url_dump_becomes_generic_safe_line():
    """An unclassified failure that carries raw dict/URL structure must fall
    back to the generic safe line — never echo the dict or the internal URL."""
    raw = "Unexpected failure {'trace': 'abc'} at https://vpc.internal/xyz"
    result = humanize_provider_error(Exception(raw))

    assert "{" not in result
    assert "http" not in result.lower()
    assert "vpc.internal" not in result
    # The generic fallback wording.
    assert "unexpected provider error" in result.lower()


def test_rag_error_subclass_passes_through_unchanged():
    """A typed ``RagError`` (e.g. a missing embedding key) is already curated —
    it must be returned verbatim, proving a missing-key failure surfaces
    cleanly instead of as a raw crash."""
    curated = "No 'openai' API key configured for embedding"
    exc = EmbeddingProviderUnavailableError(curated)
    assert humanize_provider_error(exc) == curated


def test_ingestion_wrapper_uses_embedding_provider_subject():
    """``humanize_ingestion_error`` is the ingestion-flavoured wrapper — its
    subject is the embedding provider, so a quota failure reads as such."""
    raw = "429 RESOURCE_EXHAUSTED quota exceeded"
    result = humanize_ingestion_error(Exception(raw))

    assert "{" not in result
    assert "embedding provider" in result.lower()
    assert "quota" in result.lower()
