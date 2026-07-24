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


class UnknownVectorStoreError(RagError):
    """The vector-store slug in an ``ingestion_pipeline_runs`` row has no registry entry."""


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
