"""Verify a single upload can carry multiple RAG runs (A/B, re-embed, store
swap) and each run's chunks stay isolated at retrieval time. Runs against the
InMemoryVectorStore so no DB / network is required."""

import uuid
from dataclasses import dataclass

from core.services.rag.embedders import Embedder
from core.services.rag.pipeline import RAGPipeline
from core.services.rag.readers import DocumentReader
from core.services.rag.types import Chunk, Document
from core.services.rag.vector_stores.memory_store import InMemoryVectorStore
from core.services.rag.chunkers import Chunker


@dataclass
class FakeRun:
    id: uuid.UUID
    organization_id: uuid.UUID = uuid.uuid4()
    upload_id: uuid.UUID = uuid.uuid4()
    knowledge_base_id: uuid.UUID = uuid.uuid4()


class OneChunkChunker(Chunker):
    def __init__(self, text):
        self._text = text

    def chunk(self, document):
        return [Chunk(index=0, text=self._text)]


class ConstEmbedder(Embedder):
    def __init__(self, provider, model, dims, vector):
        self.provider = provider
        self.model = model
        self.dimensions = dims
        self._vector = vector

    def embed_texts(self, texts):
        return [list(self._vector) for _ in texts]

    def embed_query(self, query):
        return list(self._vector)


class NoopReader(DocumentReader):
    def supports(self, content_type):
        return True

    def read(self, file_bytes, content_type, page_range=None):
        return Document(text="")


def test_two_runs_on_same_upload_stamp_distinct_run_ids():
    upload_id = uuid.uuid4()
    run_a = FakeRun(id=uuid.uuid4(), upload_id=upload_id)
    run_b = FakeRun(id=uuid.uuid4(), upload_id=upload_id, organization_id=run_a.organization_id, knowledge_base_id=run_a.knowledge_base_id)
    store = InMemoryVectorStore()

    pipe_a = RAGPipeline(
        run=run_a,
        parser=NoopReader(),
        chunker=OneChunkChunker("run A content"),
        embedder=ConstEmbedder("openai", "text-embedding-3-small", 1536, [0.1] * 1536),
        store=store,
    )
    pipe_b = RAGPipeline(
        run=run_b,
        parser=NoopReader(),
        chunker=OneChunkChunker("run B content"),
        embedder=ConstEmbedder("openai", "text-embedding-3-large", 3072, [0.2] * 3072),
        store=store,
    )
    pipe_a.ingest_text("ignored — chunker returns fixed text")
    pipe_b.ingest_text("ignored — chunker returns fixed text")

    assert store.count() == 2
    metas_by_run = {m["ingestion_run_id"]: m for m in (r.metadata for r in store._records)}
    assert metas_by_run[str(run_a.id)]["embedding_model"] == "text-embedding-3-small"
    assert metas_by_run[str(run_a.id)]["embedding_dimensions"] == 1536
    assert metas_by_run[str(run_b.id)]["embedding_model"] == "text-embedding-3-large"
    assert metas_by_run[str(run_b.id)]["embedding_dimensions"] == 3072


def test_retrieve_by_run_id_isolates_chunks():
    upload_id = uuid.uuid4()
    run_a = FakeRun(id=uuid.uuid4(), upload_id=upload_id)
    run_b = FakeRun(id=uuid.uuid4(), upload_id=upload_id, organization_id=run_a.organization_id, knowledge_base_id=run_a.knowledge_base_id)
    store = InMemoryVectorStore()

    RAGPipeline(
        run=run_a, parser=NoopReader(), chunker=OneChunkChunker("A"),
        embedder=ConstEmbedder("openai", "small", 4, [1.0, 0, 0, 0]),
        store=store,
    ).ingest_text("x")
    RAGPipeline(
        run=run_b, parser=NoopReader(), chunker=OneChunkChunker("B"),
        embedder=ConstEmbedder("openai", "large", 4, [0, 1.0, 0, 0]),
        store=store,
    ).ingest_text("x")

    # Filter by run_a's id — must only see the "A" chunk.
    hits = store.query([1.0, 0, 0, 0], top_k=10, filters={"ingestion_run_id": str(run_a.id)})
    assert [h.text for h in hits] == ["A"]

    hits_b = store.query([0, 1.0, 0, 0], top_k=10, filters={"ingestion_run_id": str(run_b.id)})
    assert [h.text for h in hits_b] == ["B"]
