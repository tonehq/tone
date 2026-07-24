"""Unit tests for core.services.rag.pipeline.RAGPipeline (isolated, no DB/network).

The pipeline is now a run runner: it takes an ``IngestionPipelineRun`` and
pre-built parser/chunker/embedder/store and stamps the full run identity
into every record's metadata. Tests use a fake run so they run without a DB.
"""

import io
import uuid
from dataclasses import dataclass
from typing import Optional

import pytest

from core.services.rag.pipeline import RAGPipeline
from core.services.rag.chunkers import Chunker
from core.services.rag.embedders import Embedder, EmbeddingMetadata
from core.services.rag.readers import DocumentReader
from core.services.rag.types import Chunk, Document, SearchResult
from core.services.rag.vector_stores.base import VectorStore
from core.services.rag.vector_stores.memory_store import InMemoryVectorStore


@dataclass
class FakeRun:
    """Stand-in for IngestionPipelineRun that avoids needing a DB row."""
    id: uuid.UUID = uuid.uuid4()
    organization_id: uuid.UUID = uuid.uuid4()
    upload_id: uuid.UUID = uuid.uuid4()
    knowledge_base_id: uuid.UUID = uuid.uuid4()


class RecordingEmbedder(Embedder):
    provider = "test"
    dimensions = 3
    model = "test-embed"
    version = "v0"

    def __init__(self, per_text=None):
        self._per_text = per_text
        self.embed_texts_calls = []
        self.embed_query_calls = []

    def embed_texts(self, texts):
        self.embed_texts_calls.append(list(texts))
        if self._per_text is not None:
            return [self._per_text(t) for t in texts]
        return [[float(len(t)), 0.0, 1.0] for t in texts]

    def embed_query(self, query):
        self.embed_query_calls.append(query)
        return [float(len(query)), 0.0, 1.0]


class KeywordEmbedder(Embedder):
    provider = "test-kw"
    model = "kw"

    def __init__(self, vocab):
        self.vocab = vocab
        self.dimensions = len(vocab)

    def embed_texts(self, texts):
        out = []
        for t in texts:
            low = t.lower()
            out.append([1.0 if w in low else 0.0 for w in self.vocab])
        return out


class FakeChunker(Chunker):
    def __init__(self, chunks=None, per_call=None):
        self._chunks = chunks
        self._per_call = per_call
        self.documents = []

    def chunk(self, document):
        self.documents.append(document)
        if self._chunks is not None:
            return [Chunk(index=c.index, text=c.text) for c in self._chunks]
        n = self._per_call if self._per_call is not None else 1
        return [Chunk(index=i, text=f"c{i}") for i in range(n)]


class SingleChunkPassthroughChunker(Chunker):
    def chunk(self, document):
        return [Chunk(index=0, text=document.text)]


class FakeReader(DocumentReader):
    def __init__(self, document=None, per_range=None):
        self._document = document
        self._per_range = per_range
        self.read_calls = []
        self.read_path_calls = []

    def supports(self, content_type):
        return True

    def read(self, file_bytes, content_type, page_range=None):
        self.read_calls.append((content_type, page_range))
        if self._per_range is not None:
            return self._per_range(page_range)
        return self._document

    def read_path(self, file_path, content_type, page_range=None):
        self.read_path_calls.append((file_path, content_type, page_range))
        return self._document


class RecordingStore(VectorStore):
    def __init__(self, results=None):
        self.records = []
        self.query_calls = []
        self._results = results or []

    def add(self, records):
        self.records.extend(records)
        return len(records)

    def query(self, embedding, top_k=3, *, filters=None):
        self.query_calls.append({"embedding": embedding, "top_k": top_k, "filters": filters})
        return list(self._results)

    def delete(self, *, filters):
        return 0

    def count(self, *, filters=None):
        return len(self.records)


def build_pipeline(*, embedder=None, store=None, parser=None, chunker=None, run=None):
    return RAGPipeline(
        run=run or FakeRun(),
        embedder=embedder or RecordingEmbedder(),
        store=store or InMemoryVectorStore(),
        parser=parser or FakeReader(document=Document(text="body")),
        chunker=chunker or FakeChunker(per_call=1),
    )


def _make_pdf(pages):
    from PyPDF2 import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_ingest_text_returns_count_and_calls_collaborators():
    embedder = RecordingEmbedder()
    store = InMemoryVectorStore()
    chunker = FakeChunker(chunks=[Chunk(0, "alpha"), Chunk(1, "beta")])
    pipe = build_pipeline(embedder=embedder, store=store, chunker=chunker)

    result = pipe.ingest_text("alpha beta")

    assert result == 2
    assert store.count() == 2
    assert embedder.embed_texts_calls == [["alpha", "beta"]]
    assert len(chunker.documents) == 1


def test_ingest_text_empty_chunks_skips_embed_and_store():
    embedder = RecordingEmbedder()
    store = InMemoryVectorStore()
    pipe = build_pipeline(embedder=embedder, store=store, chunker=FakeChunker(chunks=[]))

    result = pipe.ingest_text("anything")

    assert result == 0
    assert embedder.embed_texts_calls == []
    assert store.count() == 0


def test_ingest_text_stamps_full_run_identity():
    run = FakeRun()
    embedder = RecordingEmbedder()
    store = InMemoryVectorStore()
    chunker = FakeChunker(chunks=[Chunk(0, "one"), Chunk(1, "two")])
    pipe = build_pipeline(run=run, embedder=embedder, store=store, chunker=chunker)

    pipe.ingest_text("body", metadata={"agent_id": 7, "source": "kb"})

    metas = sorted((r.metadata for r in store._records), key=lambda m: m["chunk_index"])
    for m in metas:
        assert m["ingestion_run_id"] == str(run.id)
        assert m["organization_id"] == run.organization_id
        assert m["upload_id"] == run.upload_id
        assert m["knowledge_base_id"] == run.knowledge_base_id
        assert m["embedding_provider"] == "test"
        assert m["embedding_model"] == "test-embed"
        assert m["embedding_dimensions"] == 3
        assert m["embedding_version"] == "v0"
        assert m["agent_id"] == 7
        assert m["source"] == "kb"


def test_ingest_document_aligns_text_with_embedding():
    store = RecordingStore()
    chunker = FakeChunker(chunks=[Chunk(0, "aa"), Chunk(1, "bbbb")])
    embedder = RecordingEmbedder(per_text=lambda t: [float(len(t))])
    pipe = build_pipeline(embedder=embedder, store=store, chunker=chunker)

    pipe.ingest_text("x")

    by_text = {r.text: r.embedding for r in store.records}
    assert by_text == {"aa": [2.0], "bbbb": [4.0]}


def test_ingest_file_reads_then_ingests():
    reader = FakeReader(document=Document(text="hello world"))
    pipe = build_pipeline(parser=reader, chunker=FakeChunker(per_call=1))

    result = pipe.ingest_file(b"raw", "text/plain")

    assert result == 1
    assert reader.read_calls == [("text/plain", None)]


def test_ingest_file_raises_when_no_text_and_no_native():
    reader = FakeReader(document=Document(text="   ", native=None))
    pipe = build_pipeline(parser=reader)

    with pytest.raises(ValueError):
        pipe.ingest_file(b"raw", "application/pdf")


def test_ingest_file_allows_empty_text_when_native_present():
    reader = FakeReader(document=Document(text="", native=object()))
    pipe = build_pipeline(parser=reader, chunker=FakeChunker(per_call=1))

    assert pipe.ingest_file(b"raw", "application/pdf") == 1


def test_streaming_batches_and_reports_each_batch():
    embedder = RecordingEmbedder()
    store = InMemoryVectorStore()
    chunker = FakeChunker(per_call=5)
    pipe = build_pipeline(embedder=embedder, store=store, chunker=chunker)
    seen = []

    total = pipe.ingest_text_streaming(
        "body", batch_size=2, on_batch=lambda idx, size, elapsed: seen.append((idx, size))
    )

    assert total == 5
    assert [len(c) for c in embedder.embed_texts_calls] == [2, 2, 1]
    assert seen == [(0, 2), (1, 2), (2, 1)]
    assert store.count() == 5


def test_streaming_zero_chunks_never_flushes():
    embedder = RecordingEmbedder()
    pipe = build_pipeline(embedder=embedder, chunker=FakeChunker(chunks=[]))
    seen = []

    total = pipe.ingest_text_streaming("body", batch_size=4, on_batch=lambda i, s, e: seen.append(s))

    assert total == 0
    assert embedder.embed_texts_calls == []
    assert seen == []


def test_streaming_preserves_chunk_index_from_chunker():
    store = InMemoryVectorStore()
    chunker = FakeChunker(chunks=[Chunk(3, "x"), Chunk(7, "y")])
    pipe = build_pipeline(store=store, chunker=chunker)

    pipe.ingest_text_streaming("body", batch_size=10)

    assert sorted(r.metadata["chunk_index"] for r in store._records) == [3, 7]


def test_ingest_file_streaming_raises_on_empty():
    reader = FakeReader(document=Document(text="", native=None))
    pipe = build_pipeline(parser=reader)

    with pytest.raises(ValueError):
        pipe.ingest_file_streaming(b"raw", "text/plain")


def test_ingest_path_uses_read_path():
    reader = FakeReader(document=Document(text="from disk"))
    pipe = build_pipeline(parser=reader, chunker=FakeChunker(per_call=2))

    result = pipe.ingest_path("/tmp/doc.txt", "text/plain")

    assert result == 2
    assert reader.read_path_calls == [("/tmp/doc.txt", "text/plain", None)]


def test_paged_non_pdf_delegates_to_streaming():
    reader = FakeReader(document=Document(text="plain body"))
    pipe = build_pipeline(parser=reader, chunker=FakeChunker(per_call=1))

    result = pipe.ingest_file_paged(b"raw", "text/plain")

    assert result == 1
    assert reader.read_calls == [("text/plain", None)]


def test_paged_pdf_batches_pages_and_offsets_chunk_index():
    pdf_bytes = _make_pdf(3)
    store = InMemoryVectorStore()
    reader = FakeReader(per_range=lambda pr: Document(text=f"page {pr}"))
    chunker = FakeChunker(per_call=2)
    pipe = build_pipeline(store=store, parser=reader, chunker=chunker)
    batches = []

    total = pipe.ingest_file_paged(
        pdf_bytes, "application/pdf", page_batch=1,
        on_batch=lambda bi, start, end, n, elapsed: batches.append((start, end, n)),
    )

    assert total == 6
    assert [pr for _, pr in reader.read_calls] == [(1, 1), (2, 2), (3, 3)]
    assert batches == [(1, 1, 2), (2, 2, 2), (3, 3, 2)]
    assert sorted(r.metadata["chunk_index"] for r in store._records) == [0, 1, 2, 3, 4, 5]


def test_retrieve_embeds_query_and_forwards_top_k_and_filters():
    embedder = RecordingEmbedder()
    store = RecordingStore(results=[SearchResult(text="hit", score=0.1)])
    pipe = build_pipeline(embedder=embedder, store=store)

    results = pipe.retrieve("who is the CEO?", top_k=5, filters={"agent_id": 1})

    assert [r.text for r in results] == ["hit"]
    assert embedder.embed_query_calls == ["who is the CEO?"]
    assert store.query_calls[0]["top_k"] == 5
    assert store.query_calls[0]["filters"] == {"agent_id": 1}


def test_embedder_metadata_defaults_to_class_attrs():
    e = RecordingEmbedder()
    meta = e.metadata
    assert isinstance(meta, EmbeddingMetadata)
    assert meta.provider == "test"
    assert meta.model == "test-embed"
    assert meta.dimensions == 3
    assert meta.version == "v0"
