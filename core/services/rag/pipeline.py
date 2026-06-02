from __future__ import annotations

import time
from typing import Callable, List, Optional

from core.services.rag.chunkers import Chunker, RecursiveCharacterChunker
from core.services.rag.embedders import Embedder
from core.services.rag.readers import CompositeReader, DocumentReader
from core.services.rag.types import Document, SearchResult, VectorRecord
from core.services.rag.vector_stores.base import VectorStore


class RAGPipeline:
    def __init__(
        self,
        *,
        embedder: Embedder,
        store: VectorStore,
        reader: Optional[DocumentReader] = None,
        chunker: Optional[Chunker] = None,
    ):
        self.embedder = embedder
        self.store = store
        self.reader = reader or CompositeReader()
        self.chunker = chunker or RecursiveCharacterChunker()

    def _ingest_document(self, document: Document, metadata: Optional[dict]) -> int:
        metadata = metadata or {}
        chunks = self.chunker.chunk(document)
        if not chunks:
            return 0
        embeddings = self.embedder.embed_texts([c.text for c in chunks])
        records = [
            VectorRecord(
                text=c.text,
                embedding=emb,
                metadata={**metadata, "chunk_index": c.index},
            )
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
        metadata = metadata or {}
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
                VectorRecord(
                    text=c.text,
                    embedding=emb,
                    metadata={**metadata, "chunk_index": c.index},
                )
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

    def retrieve(self, query: str, top_k: int = 3, *, filters: Optional[dict] = None) -> List[SearchResult]:
        query_embedding = self.embedder.embed_query(query)
        return self.store.query(query_embedding, top_k=top_k, filters=filters)
