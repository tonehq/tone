from __future__ import annotations

from contextlib import contextmanager
from typing import List, Optional

from core.database.session import get_db_context
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.knowledge_base import KnowledgeBase
from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.models.upload import Upload
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
        distance = KnowledgeBaseChunk.embedding.cosine_distance(embedding)

        agent_id = filters.get("agent_id")
        upload_id = filters.get("upload_id")

        with self._db() as db:
            q = db.query(
                KnowledgeBaseChunk.chunk_text,
                distance.label("distance"),
                KnowledgeBaseChunk.upload_id,
                KnowledgeBaseChunk.chunk_index,
            )

            if agent_id is not None:
                # Per-version KB: only chunks attached to the agent's published
                # config should be retrievable at call-time. Otherwise a draft
                # version's docs could leak into a live conversation.
                from sqlalchemy import select

                from core.models.agent import Agent

                published_config_sq = (
                    select(Agent.published_config_id)
                    .where(Agent.id == str(agent_id))
                    .scalar_subquery()
                )
                q = (
                    q.join(Upload, KnowledgeBaseChunk.upload_id == Upload.id)
                    .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
                    .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
                    .filter(
                        AgentKnowledgeBase.agent_id == str(agent_id),
                        AgentKnowledgeBase.agent_config_id == published_config_sq,
                        Upload.status == filters.get("status", "ready"),
                    )
                )
            elif upload_id is not None:
                q = q.filter(KnowledgeBaseChunk.upload_id == str(upload_id))

            rows = q.order_by(distance).limit(top_k).all()

        return [
            SearchResult(
                text=r.chunk_text,
                score=float(r.distance),
                metadata={"upload_id": r.upload_id, "chunk_index": r.chunk_index},
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
