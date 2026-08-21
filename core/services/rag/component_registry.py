"""Single source of truth for validating RAG component slugs.

Previously the same "unknown parser/tokeniser/embedder/store" fail-fast
lived in three places (``ingestion_config_service``, ``ingestion_run_service``,
and the ``knowledge_base_routes.create_pipeline_run`` handler). Every call
site rebuilt the same "Available: [...]" hint. This module centralises it
and raises the typed :class:`UnknownRagComponentError` so the service layer
stays transport-agnostic.
"""

from __future__ import annotations

from typing import Optional

from core.services.ingestion_errors import UnknownRagComponentError
from core.services.rag.embedder_factory import EMBEDDERS
from core.services.rag.factory import VECTOR_STORES
from core.services.rag.parser_factory import PARSERS
from core.services.rag.tokeniser_factory import TOKENISERS

_REGISTRIES = {
    "parser": PARSERS,
    "tokeniser": TOKENISERS,
    "embedding_provider": EMBEDDERS,
    "vector_store": VECTOR_STORES,
}


# Display form for error messages — the historic wording used spaces
# ("embedding provider", "vector store") rather than snake_case slugs. Kept
# byte-for-byte identical to the previous inline HTTPException wording so
# any FE code that string-matches on the error detail keeps working.
_KIND_DISPLAY = {
    "parser": "parser",
    "tokeniser": "tokeniser",
    "embedding_provider": "embedding provider",
    "vector_store": "vector store",
}


def ensure_rag_component(kind: str, slug: Optional[str]) -> None:
    """Raise :class:`UnknownRagComponentError` when ``slug`` is set but not
    registered for ``kind``. ``None`` is a no-op (unset field).

    ``kind`` must be one of ``parser`` / ``tokeniser`` /
    ``embedding_provider`` / ``vector_store``; anything else is a caller bug
    and raises ``ValueError`` (fail-fast — a mistyped kind would silently
    skip validation)."""
    if slug is None:
        return
    if kind not in _REGISTRIES:
        raise ValueError(
            f"ensure_rag_component: unknown kind={kind!r}; "
            f"expected one of {sorted(_REGISTRIES)}"
        )
    registry = _REGISTRIES[kind]
    if slug not in registry:
        raise UnknownRagComponentError(
            _KIND_DISPLAY[kind], slug, list(registry.keys())
        )


def ensure_rag_recipe(
    *,
    parser: Optional[str] = None,
    tokeniser: Optional[str] = None,
    embedding_provider: Optional[str] = None,
    vector_store: Optional[str] = None,
) -> None:
    """Convenience wrapper — validate every non-None slug in one call. Kept
    keyword-only so mixed callers (create with all four, update with a
    subset) share the same signature."""
    ensure_rag_component("parser", parser)
    ensure_rag_component("tokeniser", tokeniser)
    ensure_rag_component("embedding_provider", embedding_provider)
    ensure_rag_component("vector_store", vector_store)
