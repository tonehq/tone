from __future__ import annotations

import io
import time
from typing import TYPE_CHECKING, Callable, List, Optional

from loguru import logger
from PyPDF2 import PdfReader as _PdfReader

from core.services.rag.chunkers import Chunker
from core.services.rag.embedders import Embedder
from core.services.rag.readers import DocumentReader
from core.services.rag.types import Document, SearchResult, VectorRecord
from core.services.rag.vector_stores.base import VectorStore

if TYPE_CHECKING:
    from core.models.ingestion_pipeline_run import IngestionPipelineRun


class RAGPipeline:
    """Runs a single ingestion pipeline against pre-built components pinned by
    an ``IngestionPipelineRun``. Every record written carries the full run
    identity (ingestion_run_id, embedding provider/model/dimensions/version,
    chunk_index, chunk_metadata) so the vector store can persist without any
    extra DB queries and retrieval can filter by run without joining back."""

    def __init__(
        self,
        *,
        run: "IngestionPipelineRun",
        parser: DocumentReader,
        chunker: Chunker,
        embedder: Embedder,
        store: VectorStore,
    ):
        self.run = run
        self.reader = parser
        self.chunker = chunker
        self.embedder = embedder
        self.store = store

    def _run_metadata(self) -> dict:
        meta = self.embedder.metadata
        return {
            "ingestion_run_id": str(self.run.id),
            "organization_id": self.run.organization_id,
            "upload_id": self.run.upload_id,
            "knowledge_base_id": self.run.knowledge_base_id,
            "embedding_provider": meta.provider,
            "embedding_model": meta.model,
            "embedding_dimensions": meta.dimensions,
            "embedding_version": meta.version,
        }

    def _build_record(
        self,
        chunk_text: str,
        chunk_index: int,
        embedding: List[float],
        base_metadata: dict,
        chunk_metadata: Optional[dict] = None,
    ) -> VectorRecord:
        return VectorRecord(
            text=chunk_text,
            embedding=embedding,
            metadata={
                **base_metadata,
                "chunk_index": chunk_index,
                "chunk_metadata": chunk_metadata or {},
            },
        )

    def _ingest_document(self, document: Document, metadata: Optional[dict]) -> int:
        base = {**self._run_metadata(), **(metadata or {})}
        chunks = self.chunker.chunk(document)
        if not chunks:
            return 0
        embeddings = self.embedder.embed_texts([c.text for c in chunks])
        records = [
            self._build_record(c.text, c.index, emb, base, document.metadata)
            for c, emb in zip(chunks, embeddings)
        ]
        return self.store.add(records)

    def ingest_text(self, text: str, *, metadata: Optional[dict] = None) -> int:
        return self._ingest_document(Document(text=text), metadata)

    def ingest_file(self, file_bytes: bytes, content_type: str, *, metadata: Optional[dict] = None) -> int:
        document = self.reader.read(file_bytes, content_type)
        if not document.text.strip() and document.native is None:
            raise ValueError("No text could be extracted from the file")
        return self._ingest_document(document, metadata)

    def _ingest_streaming(
        self,
        document: Document,
        metadata: Optional[dict],
        batch_size: int,
        on_batch: Optional[Callable[[int, int, float], None]] = None,
    ) -> int:
        base = {**self._run_metadata(), **(metadata or {})}
        total = 0
        buffer: List = []
        batch_index = 0

        def flush() -> int:
            nonlocal batch_index
            if not buffer:
                return 0
            t0 = time.monotonic()
            embeddings = self.embedder.embed_texts([c.text for c in buffer])
            records = [
                self._build_record(c.text, c.index, emb, base, document.metadata)
                for c, emb in zip(buffer, embeddings)
            ]
            n = self.store.add(records)
            elapsed = time.monotonic() - t0
            if on_batch is not None:
                on_batch(batch_index, len(buffer), elapsed)
            batch_index += 1
            buffer.clear()
            return n

        for chunk in self.chunker.chunk(document):
            buffer.append(chunk)
            if len(buffer) >= batch_size:
                total += flush()
        total += flush()
        return total

    def ingest_text_streaming(
        self, text: str, *, metadata: Optional[dict] = None, batch_size: int = 256,
        on_batch: Optional[Callable[[int, int, float], None]] = None,
    ) -> int:
        return self._ingest_streaming(Document(text=text), metadata, batch_size, on_batch)

    def ingest_file_streaming(
        self, file_bytes: bytes, content_type: str, *, metadata: Optional[dict] = None,
        batch_size: int = 256, on_batch: Optional[Callable[[int, int, float], None]] = None,
    ) -> int:
        document = self.reader.read(file_bytes, content_type)
        if not document.text.strip() and document.native is None:
            raise ValueError("No text could be extracted from the file")
        return self._ingest_streaming(document, metadata, batch_size, on_batch)

    def ingest_path(
        self, file_path: str, content_type: str, *, metadata: Optional[dict] = None,
        batch_size: int = 256, on_batch: Optional[Callable[[int, int, float], None]] = None,
    ) -> int:
        document = self.reader.read_path(file_path, content_type)
        if not document.text.strip() and document.native is None:
            raise ValueError("No text could be extracted from the file")
        return self._ingest_streaming(document, metadata, batch_size, on_batch)

    def ingest_file_paged(
        self, file_bytes: bytes, content_type: str, *, page_batch: int = 50,
        metadata: Optional[dict] = None,
        on_batch: Optional[Callable[[int, int, int, int, float], None]] = None,
    ) -> int:
        if content_type != "application/pdf":
            return self.ingest_file_streaming(file_bytes, content_type, metadata=metadata)
        total_pages = len(_PdfReader(io.BytesIO(file_bytes)).pages)
        base = {**self._run_metadata(), **(metadata or {})}
        total = 0
        offset = 0
        for batch_index, start in enumerate(range(1, total_pages + 1, page_batch)):
            end = min(start + page_batch - 1, total_pages)
            t0 = time.monotonic()
            document = self.reader.read(file_bytes, content_type, (start, end))
            chunks = self.chunker.chunk(document)
            n = 0
            if chunks:
                embeddings = self.embedder.embed_texts([c.text for c in chunks])
                records = [
                    self._build_record(c.text, offset + i, emb, base, document.metadata)
                    for i, (c, emb) in enumerate(zip(chunks, embeddings))
                ]
                n = self.store.add(records)
                offset += len(chunks)
                total += n
            if on_batch is not None:
                on_batch(batch_index, start, end, n, time.monotonic() - t0)
        return total

    def retrieve(self, query: str, top_k: int = 3, *, filters: Optional[dict] = None) -> List[SearchResult]:
        # Two-tier error handling mirrors the live ``read_document`` path so
        # eval failures tell the operator which step blew up (embed vs
        # store) from the summary line alone — no traceback dive required.
        try:
            query_embedding = self.embedder.embed_query(query)
        except Exception:
            logger.exception(
                "[rag.retrieve] embed failed query='{}' top_k={} filters={}",
                query, top_k, filters,
            )
            raise
        # Forward the natural-language query so the underlying store's log
        # line carries it. Used by the eval harness — same debug signal as
        # the live read_document path. The store logs its own failures with
        # ``[pgvector.query] failed`` so we don't wrap another try here.
        return self.store.query(
            query_embedding, top_k=top_k, filters=filters, query_text=query
        )
