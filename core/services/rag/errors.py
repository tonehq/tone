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


def humanize_provider_error(exc: BaseException, *, subject: str = "The AI provider") -> str:
    """Return a short, user-safe one-liner for a provider / SDK failure.

    Shared by the ingestion AND eval error surfaces so no raw provider dict,
    internal URL, or stack trace ever reaches the UI (backend standards
    §"Never expose raw exceptions / internal implementation details"). The full
    technical text is still captured by the ``logger.exception`` at each
    failure site — this is only what surfaces to the user.

    Rules (in order):
    1. Typed ``RagError`` subclasses already carry a clean message — pass through.
    2. Common provider failures (missing model, bad key, quota, rate limit,
       timeout, connection, auth) → short human sentence, worded around
       ``subject`` (e.g. "The embedding provider" / "The AI provider").
    3. Anything else → a generic safe line when the text looks like a raw dump
       (dict / URL / SDK envelope), else ``<ExceptionType>: <first line>``.
    """
    if isinstance(exc, RagError):
        # Our own typed errors are already curated (e.g.
        # ``EmbeddingProviderUnavailableError``, ``UnknownParserError``).
        return str(exc)

    raw = str(exc) or exc.__class__.__name__
    lower = raw.lower()
    subject_mid = subject[0].lower() + subject[1:]  # "the AI provider" mid-sentence

    # OpenAI-style structured errors — pattern-match on the ``code`` /
    # ``type`` fields the SDK embeds in its stringified representation.
    if "model_not_found" in lower or "does not exist or you do not have access" in lower:
        return "Model not found. Check the configured model name and retry."
    if "invalid_api_key" in lower or "incorrect api key" in lower or "invalid api key" in lower:
        return f"Invalid API key for {subject_mid}. Update the provider key and retry."
    # Quota / resource-exhausted — covers OpenAI ("insufficient_quota",
    # "exceeded your current quota") AND Google/Vertex ("RESOURCE_EXHAUSTED",
    # "Quota exceeded for …requests_per_minute…", "submit a quota increase").
    if (
        "insufficient_quota" in lower
        or "exceeded your current quota" in lower
        or "quota exceeded" in lower
        or "resource_exhausted" in lower
        or "resource exhausted" in lower
        or "quota increase" in lower
        or "requests_per_minute" in lower
        or "billing" in lower
    ):
        return f"{subject} quota exceeded. Check the provider's quota/billing and retry."
    if (
        "rate_limit" in lower
        or "rate limit" in lower
        or "too many requests" in lower
        or "429" in lower
    ):
        return f"{subject} rate limit hit. Retry in a moment."
    if "timeout" in lower or "timed out" in lower:
        return f"{subject} request timed out. Retry in a moment."
    if "connection" in lower and ("refused" in lower or "reset" in lower or "aborted" in lower):
        return f"Could not reach {subject_mid}. Check network / provider status."
    if "unauthorized" in lower or "401" in lower:
        return "Provider rejected credentials. Update the API key and retry."

    # Generic fallback — first line only. If it carries raw provider structure
    # (a dict / JSON dump, an internal URL, or an SDK error envelope), that is
    # internal implementation detail we must NOT surface (backend standards
    # §"Never expose raw exceptions / internal implementation details"): return
    # a safe generic message — the full text is already captured by the
    # ``logger.exception`` at the failure site. Plain one-line messages pass
    # through with their exception-type label.
    first_line = raw.strip().splitlines()[0] if raw.strip() else raw
    if "{" in first_line or "http" in lower or "googleapis" in lower:
        return (
            "The request failed due to an unexpected provider error. "
            "Please retry — if it keeps failing, contact support."
        )
    label = type(exc).__name__
    if len(first_line) > _MAX_FALLBACK_LEN:
        first_line = first_line[: _MAX_FALLBACK_LEN - 1].rstrip() + "…"
    return f"{label}: {first_line}"


def humanize_ingestion_error(exc: BaseException) -> str:
    """Ingestion-flavoured wrapper of :func:`humanize_provider_error` — the
    ``subject`` is the embedding provider. Kept as the existing entry point for
    the ingestion call sites (``document_processing_service``)."""
    return humanize_provider_error(exc, subject="The embedding provider")
