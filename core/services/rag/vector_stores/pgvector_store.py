from __future__ import annotations

from contextlib import contextmanager
from typing import List, Optional

from sqlalchemy import text

from core.database.session import get_db_context
from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.services.rag.types import SearchResult, VectorRecord
from core.services.rag.vector_stores.base import VectorStore


class PgVectorStore(VectorStore):
    def __init__(self, session=None):
        self._session = session

    @contextmanager
    def _db(self):
        if self._session is not None:
            yield self._session
        else:
            with get_db_context() as db:
                yield db

    def add(self, records: List[VectorRecord]) -> int:
        rows = [
            KnowledgeBaseChunk(
                organization_id=r.metadata.get("organization_id"),
                upload_id=r.metadata.get("upload_id"),
                chunk_index=r.metadata.get("chunk_index"),
                chunk_text=r.text,
                embedding=r.embedding,
            )
            for r in records
        ]
        with self._db() as db:
            db.add_all(rows)
            db.flush()
            if self._session is None:
                db.commit()
        return len(rows)

    def query(
        self, embedding: List[float], top_k: int = 3, *, filters: Optional[dict] = None
    ) -> List[SearchResult]:
        filters = filters or {}
        emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
        params = {"e": emb_str, "k": top_k}

        agent_id = filters.get("agent_id")
        upload_id = filters.get("upload_id")

        if agent_id is not None:
            sql = """
                SELECT kbc.chunk_text, kbc.embedding <=> :e AS distance,
                       kbc.upload_id, kbc.chunk_index
                FROM knowledge_base_chunks kbc
                JOIN uploads u ON kbc.upload_id = u.id
                JOIN agent_knowledge_bases akb ON akb.upload_id = u.id
                WHERE akb.agent_id = :agent_id AND u.status = :status
                ORDER BY kbc.embedding <=> :e
                LIMIT :k
            """
            params["agent_id"] = str(agent_id)
            params["status"] = filters.get("status", "ready")
        elif upload_id is not None:
            sql = """
                SELECT chunk_text, embedding <=> :e AS distance, upload_id, chunk_index
                FROM knowledge_base_chunks
                WHERE upload_id = :upload_id
                ORDER BY embedding <=> :e
                LIMIT :k
            """
            params["upload_id"] = str(upload_id)
        else:
            sql = """
                SELECT chunk_text, embedding <=> :e AS distance, upload_id, chunk_index
                FROM knowledge_base_chunks
                ORDER BY embedding <=> :e
                LIMIT :k
            """

        with self._db() as db:
            rows = db.execute(text(sql), params).fetchall()
        return [
            SearchResult(
                text=r[0],
                score=float(r[1]),
                metadata={"upload_id": r[2], "chunk_index": r[3]},
            )
            for r in rows
        ]

    def delete(self, *, filters: dict) -> int:
        upload_id = (filters or {}).get("upload_id")
        if upload_id is None:
            raise ValueError("PgVectorStore.delete requires filters['upload_id']")
        with self._db() as db:
            n = (
                db.query(KnowledgeBaseChunk)
                .filter(KnowledgeBaseChunk.upload_id == upload_id)
                .delete(synchronize_session=False)
            )
            if self._session is None:
                db.commit()
        return n

    def count(self, *, filters: Optional[dict] = None) -> int:
        filters = filters or {}
        with self._db() as db:
            q = db.query(KnowledgeBaseChunk)
            if filters.get("upload_id") is not None:
                q = q.filter(KnowledgeBaseChunk.upload_id == filters["upload_id"])
            if filters.get("organization_id") is not None:
                q = q.filter(KnowledgeBaseChunk.organization_id == filters["organization_id"])
            return q.count()
