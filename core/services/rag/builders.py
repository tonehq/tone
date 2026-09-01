"""Composition helpers that build a RAG stack from an ``IngestionPipelineRun``.

The recipe pinned on a run row (parser / tokeniser / embedder / vector store)
was previously wired by hand at every call site — the ingestion worker, the
eval harness, and the live retrieval tool each re-assembled the same factory
calls. That is the duplication the reuse doctrine forbids: "build the RAG stack
pinned by a run" now lives here ONCE so a change to how a run resolves into
components is made in a single place.

- :func:`build_pipeline_from_run` returns a full :class:`RAGPipeline`
  (parser → chunker → embedder → store) for INGESTION.
- :func:`build_retriever_from_run` returns just ``(embedder, store)`` for the
  RETRIEVAL / eval path, which embeds a query and hits the store directly and
  never needs a parser or chunker.

Both read every component slug/config straight off the run row, so callers pass
only the run and the already-resolved embedding-provider ``api_key``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from core.services.rag.embedder_factory import build_embedder_from_run
from core.services.rag.factory import get_vector_store
from core.services.rag.parser_factory import get_parser
from core.services.rag.pipeline import RAGPipeline
from core.services.rag.tokeniser_factory import get_tokeniser

if TYPE_CHECKING:
    from core.models.ingestion_pipeline_run import IngestionPipelineRun
    from core.services.rag.embedders import Embedder
    from core.services.rag.vector_stores.base import VectorStore


def build_pipeline_from_run(
    run: "IngestionPipelineRun", *, api_key: str
) -> RAGPipeline:
    """Assemble the full ingestion pipeline pinned by ``run``.

    Reproduces the exact factory wiring the ingestion worker used inline:
    parser (+ config) → tokeniser/chunker (+ config) → embedder (from run) →
    vector store (+ ref). ``api_key`` is the caller-resolved key for the run's
    embedding provider.
    """
    parser = get_parser(run.parser, config=dict(run.parser_config or {}))
    chunker = get_tokeniser(run.tokeniser, config=run.tokeniser_config)
    embedder = build_embedder_from_run(run, api_key=api_key)
    store = get_vector_store(run.vector_store, **(run.vector_store_ref or {}))
    return RAGPipeline(
        run=run,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        store=store,
    )


def build_retriever_from_run(
    run: "IngestionPipelineRun", *, api_key: str
) -> Tuple["Embedder", "VectorStore"]:
    """Assemble just the ``(embedder, store)`` pair for the retrieval / eval
    path — no parser or chunker is needed to embed a query and query the store.
    """
    embedder = build_embedder_from_run(run, api_key=api_key)
    store = get_vector_store(run.vector_store, **(run.vector_store_ref or {}))
    return embedder, store
