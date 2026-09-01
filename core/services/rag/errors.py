"""Typed RAG errors — every ingestion / retrieval failure raised by the RAG
service tree is a subclass of ``RagError`` so callers can distinguish
recoverable misconfiguration from unexpected exceptions.
"""

from __future__ import annotations


class RagError(Exception):
    """Base for every RAG-layer error."""


class UnknownParserError(RagError):
    """The parser slug in an ``ingestion_pipeline_runs`` row has no registry entry."""


class UnknownTokeniserError(RagError):
    """The tokeniser slug in an ``ingestion_pipeline_runs`` row has no registry entry."""


class EmbeddingProviderUnavailableError(RagError):
    """The embedding provider is not registered, or no API key is configured for the org."""


class EmbeddingDimensionUnsupportedError(RagError):
    """The run's ``embedding_dimensions`` does not match any dedicated
    ``knowledge_base_chunk_embeddings.embedding_<dim>`` column. Adding a new
    dimension is a schema follow-up."""


class EmbeddingCompatibilityError(RagError):
    """A retrieval-time embedder does not match the run that produced the
    stored embeddings (different provider, model, or dimensions). Cosine
    similarity across mismatched models is meaningless."""


class IngestionRunFailed(RagError):
    """An ingestion run terminated with ``status='failed'``. Carries the run
    id and stored error message so callers can surface both."""

    def __init__(self, run_id, error: str):
        super().__init__(f"Ingestion run {run_id} failed: {error}")
        self.run_id = run_id
        self.error = error


# ── User-facing error humanizer ─────────────────────────────────────────────

# Ingestion failures are written to ``ingestion_pipeline_runs.error`` and
# ``uploads.meta_data['error']`` where the UI reads them back. The raw
# provider exception (OpenAI ``NotFoundError``, ``AuthenticationError``,
# ``RateLimitError``, etc.) stringifies to a shape like:
#   ``Error code: 404 - {'error': {'message': '…', 'type': '…', 'code': '…'}}``
# which is noisy and confusing for end users. ``humanize_ingestion_error``
# translates the common provider failures to a short, plain-English one-liner
# BEFORE the message is stored, so both surfaces (upload detail + runs table
# tooltip) show something readable without any frontend work.
_MAX_FALLBACK_LEN = 240


def humanize_ingestion_error(exc: BaseException) -> str:
    """Return a short, user-friendly one-liner for an ingestion failure.

    Rules (in order):
    1. Typed ``RagError`` subclasses already carry a clean message — pass through.
    2. Common provider failures (missing model, bad key, quota, rate limit,
       timeout, connection) → short human sentence.
    3. Anything else → ``<ExceptionType>: <first line, truncated>``. Full
       traceback is still available in logs via the ``logger.exception`` call
       at the failure site — this is only what surfaces in the UI.
    """
    if isinstance(exc, RagError):
        # Our own typed errors are already curated (e.g.
        # ``EmbeddingProviderUnavailableError``, ``UnknownParserError``).
        return str(exc)

    raw = str(exc) or exc.__class__.__name__
    lower = raw.lower()

    # OpenAI-style structured errors — pattern-match on the ``code`` /
    # ``type`` fields the SDK embeds in its stringified representation.
    if "model_not_found" in lower or "does not exist or you do not have access" in lower:
        return (
            "Embedding model not found. Check the model name in the ingestion "
            "config (e.g. text-embedding-3-small)."
        )
    if "invalid_api_key" in lower or "incorrect api key" in lower or "invalid api key" in lower:
        return "Invalid API key for the embedding provider. Update the provider key and retry."
    if "insufficient_quota" in lower or "exceeded your current quota" in lower or "billing" in lower:
        return "Embedding provider quota exhausted. Check your billing and retry."
    if "rate_limit" in lower or "rate limit" in lower or "too many requests" in lower:
        return "Embedding provider rate limit hit. Retry in a moment."
    if "timeout" in lower or "timed out" in lower:
        return "Embedding provider request timed out. Retry in a moment."
    if "connection" in lower and ("refused" in lower or "reset" in lower or "aborted" in lower):
        return "Could not reach the embedding provider. Check network / provider status."
    if "unauthorized" in lower or "401" in lower:
        return "Provider rejected credentials. Update the API key and retry."

    # Generic fallback — first line only, hard-capped, no raw dicts.
    first_line = raw.strip().splitlines()[0] if raw.strip() else raw
    label = type(exc).__name__
    if len(first_line) > _MAX_FALLBACK_LEN:
        first_line = first_line[: _MAX_FALLBACK_LEN - 1].rstrip() + "…"
    return f"{label}: {first_line}"
