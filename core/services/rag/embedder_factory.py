"""Embedder factory — resolves an embedding provider slug (from
``ingestion_pipeline_runs.embedding_provider``) to an instantiated ``Embedder``.

Adding a provider = subclass ``Embedder`` in ``embedders.py`` (or elsewhere)
then ``register_embedder("slug", MyEmbedder)``. The subclass must set the
``provider`` classvar to the same slug.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type

from core.services.rag.embedders import Embedder, OpenAIEmbedder
from core.services.rag.errors import EmbeddingProviderUnavailableError

if TYPE_CHECKING:  # avoid circular import — model imports service tree
    from core.models.ingestion_pipeline_run import IngestionPipelineRun

EMBEDDERS: Dict[str, Type[Embedder]] = {
    "openai": OpenAIEmbedder,
}


def register_embedder(provider: str, cls: Type[Embedder]) -> None:
    EMBEDDERS[provider] = cls


def get_embedder(provider: str, *, model: str, api_key: str, **kwargs) -> Embedder:
    try:
        embedder_cls = EMBEDDERS[provider]
    except KeyError:
        raise EmbeddingProviderUnavailableError(
            f"Unknown embedding provider: {provider!r}. Available: {sorted(EMBEDDERS)}"
        )
    return embedder_cls(api_key=api_key, model=model, **kwargs)


def build_embedder_from_run(run: "IngestionPipelineRun", api_key: str) -> Embedder:
    """Build the embedder pinned by a run's identity. Dimensions is passed
    through so providers that support variable-length embeddings (e.g. OpenAI
    text-embedding-3-*) produce vectors that match the run's
    ``embedding_dimensions`` — and therefore fit the matching
    ``knowledge_base_chunk_embeddings.embedding_<dim>`` column."""
    return get_embedder(
        run.embedding_provider,
        model=run.embedding_model,
        api_key=api_key,
        dimensions=run.embedding_dimensions,
    )
