from __future__ import annotations

from typing import Dict, Type

from core.services.rag.vector_stores.base import VectorStore
from core.services.rag.vector_stores.pgvector_store import PgVectorStore

# ``InMemoryVectorStore`` (``core/services/rag/vector_stores/memory_store.py``)
# is intentionally NOT registered here — pgvector is the only production
# backend. The class is kept for the RAG test suite (``test-cases/rag/…``)
# which imports it directly by class; if you re-add it, also revisit the
# frontend Configure-params schema in
# ``frontend/src/components/knowledge-base/optionParamSchemas.ts``.
VECTOR_STORES: Dict[str, Type[VectorStore]] = {
    "pgvector": PgVectorStore,
}

DEFAULT_BACKEND = "pgvector"


def get_vector_store(backend: str = None, **kwargs) -> VectorStore:
    backend = backend or DEFAULT_BACKEND
    try:
        store_cls = VECTOR_STORES[backend]
    except KeyError:
        raise ValueError(
            f"Unknown vector store backend: {backend!r}. Available: {sorted(VECTOR_STORES)}"
        )
    return store_cls(**kwargs)
