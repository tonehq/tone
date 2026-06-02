from __future__ import annotations

from typing import Dict, Type

from core.services.rag.vector_stores.base import VectorStore
from core.services.rag.vector_stores.memory_store import InMemoryVectorStore
from core.services.rag.vector_stores.pgvector_store import PgVectorStore

VECTOR_STORES: Dict[str, Type[VectorStore]] = {
    "pgvector": PgVectorStore,
    "memory": InMemoryVectorStore,
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
