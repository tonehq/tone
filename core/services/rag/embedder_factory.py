"""Embedder factory — resolves an embedding provider slug (from
``ingestion_pipeline_runs.embedding_provider``) to an instantiated ``Embedder``.

Adding a provider = subclass ``Embedder`` in ``embedders.py`` (or elsewhere)
then ``register_embedder("slug", MyEmbedder)``. The subclass must set the
``provider`` classvar to the same slug.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Type

from loguru import logger

from core.services.rag.embedders import Embedder, GoogleEmbedder, OpenAIEmbedder
from core.services.rag.errors import EmbeddingProviderUnavailableError

if TYPE_CHECKING:  # avoid circular import — model imports service tree
    from core.models.ingestion_pipeline_run import IngestionPipelineRun

EMBEDDERS: Dict[str, Type[Embedder]] = {
    "openai": OpenAIEmbedder,
    "google": GoogleEmbedder,
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


def _embedder_accepted_kwargs(embedder_cls: Type[Embedder]) -> set[str]:
    """Return the set of keyword-argument names the embedder's ``__init__``
    accepts. Used to filter user-supplied ``embedding_config`` so a typo or
    stale key never becomes a mid-ingest ``TypeError``. Includes ``**kwargs``
    sentinel: if the constructor takes ``**kwargs`` we don't filter at all."""
    import inspect

    try:
        sig = inspect.signature(embedder_cls.__init__)
    except (TypeError, ValueError):
        return set()
    accepts_var_kw = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if accepts_var_kw:
        # Special sentinel — caller treats "no filtering" as pass-through.
        return {"*"}
    return {
        name
        for name, p in sig.parameters.items()
        if name != "self"
        and p.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }


def build_embedder_from_run(run: "IngestionPipelineRun", api_key: str) -> Embedder:
    """Build the embedder pinned by a run's identity. Dimensions is passed
    through so providers that support variable-length embeddings (e.g. OpenAI
    text-embedding-3-*) produce vectors that match the run's
    ``embedding_dimensions`` — and therefore fit the matching
    ``knowledge_base_chunk_embeddings.embedding_<dim>`` column.

    ``run.embedding_config`` (JSONB, optional) carries any extra per-provider
    kwargs the saved ingestion_config chose (e.g. ``batch_size``,
    ``max_retries``, ``tokens_per_minute`` for OpenAI). Unknown kwargs are
    silently DROPPED (with a warning log) rather than crashing the worker,
    so a stale/typo key in a saved config produces a run that succeeds on
    the known-good subset. ``api_key`` / ``model`` / ``dimensions`` always
    win so a config can never override the run identity."""
    try:
        embedder_cls = EMBEDDERS[run.embedding_provider]
    except KeyError:
        raise EmbeddingProviderUnavailableError(
            f"Unknown embedding provider: {run.embedding_provider!r}. "
            f"Available: {sorted(EMBEDDERS)}"
        )

    extra: dict = dict(run.embedding_config or {})
    for reserved in ("api_key", "model", "dimensions"):
        extra.pop(reserved, None)

    accepted = _embedder_accepted_kwargs(embedder_cls)
    if accepted != {"*"} and extra:
        unknown = [k for k in extra if k not in accepted]
        if unknown:
            logger.warning(
                "[embed:{}] dropping unknown embedding_config keys {} — not accepted by "
                "{}; ingest continues with the known subset {}",
                run.embedding_provider,
                unknown,
                embedder_cls.__name__,
                sorted(k for k in extra if k in accepted),
            )
        extra = {k: v for k, v in extra.items() if k in accepted}

    return embedder_cls(
        api_key=api_key,
        model=run.embedding_model,
        dimensions=run.embedding_dimensions,
        **extra,
    )
