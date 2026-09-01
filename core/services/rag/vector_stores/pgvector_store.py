from __future__ import annotations

from contextlib import contextmanager
from typing import List, Optional

from loguru import logger

from core.database.session import get_db_context
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.models.knowledge_base_chunk_embedding import KnowledgeBaseChunkEmbedding
from core.models.upload import Upload
from core.services.rag.errors import EmbeddingCompatibilityError
from core.services.rag.logging_utils import (
    format_scores,
    summarize_vector,
    truncate_query_text,
)
from core.services.rag.types import SearchResult, VectorRecord
from core.services.rag.vector_stores.base import VectorStore


class PgVectorStore(VectorStore):
    """pgvector-backed store. Writes each record's text into
    ``knowledge_base_chunks`` and its vector into
    ``knowledge_base_chunk_embeddings`` on the column that matches the run's
    ``embedding_dimensions`` (1024 / 1536 / 3072). Reads join both tables + the
    run row, filter by (provider, model, dimensions) so a mismatched query
    embedder can never return chunks from a different run's model space, then
    order by cosine distance on the matching dimension column."""

    def __init__(self, session=None):
        self._session = session

    @contextmanager
    def _db(self):
        if self._session is not None:
            yield self._session
        else:
            with get_db_context() as db:
                yield db

    @staticmethod
    def _require(meta: dict, key: str) -> object:
        value = meta.get(key)
        if value is None:
            raise ValueError(f"PgVectorStore.add: record.metadata missing required key {key!r}")
        return value

    def add(self, records: List[VectorRecord]) -> int:
        if not records:
            return 0
        # ingestion_run_id is the useful correlator here — every record in one
        # ``add`` call belongs to the same run, so peek the first record.
        run_id = records[0].metadata.get("ingestion_run_id")
        logger.debug(
            "[pgvector] add start run={} records={}", run_id, len(records),
        )
        with self._db() as db:
            try:
                chunk_rows: List[KnowledgeBaseChunk] = []
                for r in records:
                    dims = int(self._require(r.metadata, "embedding_dimensions"))
                    if dims != len(r.embedding):
                        logger.error(
                            "[pgvector] dimension mismatch run={} metadata_dims={} vector_dims={}",
                            run_id, dims, len(r.embedding),
                        )
                        raise EmbeddingCompatibilityError(
                            f"Embedding dimension mismatch: metadata says {dims} but vector is "
                            f"{len(r.embedding)}-D"
                        )
                    chunk_rows.append(
                        KnowledgeBaseChunk(
                            organization_id=self._require(r.metadata, "organization_id"),
                            upload_id=self._require(r.metadata, "upload_id"),
                            ingestion_run_id=self._require(r.metadata, "ingestion_run_id"),
                            chunk_index=int(self._require(r.metadata, "chunk_index")),
                            chunk_text=r.text,
                            chunk_metadata=r.metadata.get("chunk_metadata"),
                        )
                    )
                db.add_all(chunk_rows)
                db.flush()  # allocate chunk.id so embedding rows can reference them

                embedding_rows: List[KnowledgeBaseChunkEmbedding] = []
                for chunk, r in zip(chunk_rows, records):
                    dims = int(r.metadata["embedding_dimensions"])
                    column = KnowledgeBaseChunkEmbedding.column_for_dimension(dims)
                    embedding_rows.append(
                        KnowledgeBaseChunkEmbedding(
                            organization_id=chunk.organization_id,
                            chunk_id=chunk.id,
                            ingestion_run_id=chunk.ingestion_run_id,
                            embedding_dimensions=dims,
                            **{column.key: r.embedding},
                        )
                    )
                db.add_all(embedding_rows)
                db.flush()
                if self._session is None:
                    db.commit()
            except Exception:
                logger.exception(
                    "[pgvector] add failed run={} records={}",
                    run_id, len(records),
                )
                if self._session is None:
                    # Only roll back sessions we own; caller-supplied sessions
                    # manage their own transaction boundaries.
                    try:
                        db.rollback()
                    except Exception:
                        logger.exception(
                            "[pgvector] rollback failed run={}", run_id,
                        )
                raise
        logger.info(
            "[pgvector] added run={} chunks={} embeddings={}",
            run_id, len(chunk_rows), len(embedding_rows),
        )
        return len(chunk_rows)

    def query(
        self,
        embedding: List[float],
        top_k: int = 3,
        *,
        filters: Optional[dict] = None,
        query_text: Optional[str] = None,
    ) -> List[SearchResult]:
        import time as _time

        filters = filters or {}
        dims = filters.get("embedding_dimensions") or len(embedding)
        column = KnowledgeBaseChunkEmbedding.column_for_dimension(int(dims))
        distance = column.cosine_distance(embedding)

        agent_id = filters.get("agent_id")
        upload_id = filters.get("upload_id")
        ingestion_run_id = filters.get("ingestion_run_id")
        org_id = filters.get("organization_id")
        provider = filters.get("embedding_provider")
        model = filters.get("embedding_model")

        vector_summary = summarize_vector(embedding)
        query_preview = truncate_query_text(query_text)
        t_start = _time.monotonic()

        try:
            with self._db() as db:
                # Resolve which run to serve when the caller didn't pin one.
                # The resolver enforces the (agent-KB override → KB default →
                # legacy is_active fallback) chain — same rule in one place.
                if ingestion_run_id is None and upload_id is not None and org_id is not None:
                    from core.services.ingestion_run_service import IngestionRunService

                    ingestion_run_id = IngestionRunService.resolve_active_run_id(
                        db,
                        org_id=org_id,
                        upload_id=upload_id,
                        agent_id=agent_id,
                    )
                    if ingestion_run_id is None:
                        logger.warning(
                            "[pgvector.query] no active ingestion_run resolved "
                            "org={} upload={} agent={} — falling back to is_active",
                            org_id, upload_id, agent_id,
                        )

                q = (
                    db.query(
                        KnowledgeBaseChunk.id.label("chunk_id"),
                        KnowledgeBaseChunk.chunk_text,
                        distance.label("distance"),
                        KnowledgeBaseChunk.upload_id,
                        KnowledgeBaseChunk.chunk_index,
                        KnowledgeBaseChunk.chunk_metadata,
                        IngestionPipelineRun.id.label("run_id"),
                    )
                    .join(
                        KnowledgeBaseChunkEmbedding,
                        KnowledgeBaseChunkEmbedding.chunk_id == KnowledgeBaseChunk.id,
                    )
                    .join(
                        IngestionPipelineRun,
                        IngestionPipelineRun.id == KnowledgeBaseChunk.ingestion_run_id,
                    )
                    .filter(IngestionPipelineRun.embedding_dimensions == int(dims))
                )
                # Tenant scoping (defense-in-depth): when the caller supplies an
                # org, constrain the whole query to it so no branch below — in
                # particular the legacy ``is_active`` fallback that filters only
                # on dimensions — can return another org's chunks. Additive:
                # callers that don't pass ``organization_id`` are unchanged, and
                # the agent-scoped path is already bounded by its published-config
                # join.
                if org_id is not None:
                    q = q.filter(KnowledgeBaseChunk.organization_id == org_id)
                if provider is not None:
                    q = q.filter(IngestionPipelineRun.embedding_provider == provider)
                if model is not None:
                    q = q.filter(IngestionPipelineRun.embedding_model == model)
                if ingestion_run_id is not None:
                    q = q.filter(KnowledgeBaseChunk.ingestion_run_id == ingestion_run_id)
                else:
                    # Resolver returned None (nothing ready) or upstream didn't
                    # pass org/upload — legacy safety net keeps behavior consistent.
                    q = q.filter(IngestionPipelineRun.is_active.is_(True))

                if agent_id is not None:
                    # Per-version KB: only chunks attached to the agent's published
                    # config should be retrievable at call-time. Otherwise a draft
                    # version's docs could leak into a live conversation.
                    from core.utils.agent_scope import published_config_subquery

                    published_config_sq = published_config_subquery(str(agent_id))
                    q = (
                        q.join(Upload, KnowledgeBaseChunk.upload_id == Upload.id)
                        .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
                        .join(
                            AgentKnowledgeBase,
                            AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id,
                        )
                        .filter(
                            AgentKnowledgeBase.agent_id == str(agent_id),
                            AgentKnowledgeBase.agent_config_id == published_config_sq,
                            Upload.status == filters.get("status", "ready"),
                        )
                    )
                elif upload_id is not None:
                    q = q.filter(KnowledgeBaseChunk.upload_id == str(upload_id))

                rows = q.order_by(distance).limit(top_k).all()
        except Exception:
            # Currently silent — one of the biggest observability gaps this
            # method has. logger.exception preserves the traceback so the
            # actual SQL / dimension / connectivity issue is diagnosable.
            duration_ms = round((_time.monotonic() - t_start) * 1000)
            logger.exception(
                "[pgvector.query] failed query='{}' {} top_k={} provider={} "
                "model={} agent_id={} ingestion_run_id={} duration_ms={}",
                query_preview, vector_summary, top_k, provider, model,
                agent_id, ingestion_run_id, duration_ms,
            )
            raise

        duration_ms = round((_time.monotonic() - t_start) * 1000)
        chunk_ids = [str(r.chunk_id) for r in rows]
        run_ids = [str(r.run_id) for r in rows]
        scores = [float(r.distance) for r in rows]

        # ONE line per search — carries every field needed to debug retrieval
        # end-to-end without opening the DB: what was asked, which embedding
        # space the query used, which run served it, which chunks came back,
        # how similar they were, how long it took. Vector itself is only the
        # summary (dims + blake2b hash) so log volume stays bounded.
        logger.info(
            "[pgvector.query] query='{}' {} top_k={} provider={} model={} "
            "agent_id={} ingestion_run_id={} count={} chunk_ids={} "
            "ingestion_run_ids={} scores={} duration_ms={}",
            query_preview, vector_summary, top_k, provider, model,
            agent_id, ingestion_run_id, len(rows), chunk_ids,
            run_ids, format_scores(scores), duration_ms,
        )

        return [
            SearchResult(
                text=r.chunk_text,
                score=float(r.distance),
                id=str(r.chunk_id),
                metadata={
                    "upload_id": r.upload_id,
                    "chunk_index": r.chunk_index,
                    "chunk_metadata": r.chunk_metadata or {},
                    "ingestion_run_id": r.run_id,
                },
            )
            for r in rows
        ]

    def delete(self, *, filters: dict) -> int:
        filters = filters or {}
        upload_id = filters.get("upload_id")
        ingestion_run_id = filters.get("ingestion_run_id")
        org_id = filters.get("organization_id")
        if upload_id is None and ingestion_run_id is None:
            raise ValueError(
                "PgVectorStore.delete requires filters['upload_id'] or filters['ingestion_run_id']"
            )
        with self._db() as db:
            q = db.query(KnowledgeBaseChunk)
            # Tenant scoping (defense-in-depth): when the caller supplies an org,
            # scope the delete to it so an ``upload_id``/``ingestion_run_id`` from
            # another tenant can't wipe this org's chunks. Additive — unchanged
            # for callers that don't pass ``organization_id``.
            if org_id is not None:
                q = q.filter(KnowledgeBaseChunk.organization_id == org_id)
            if ingestion_run_id is not None:
                q = q.filter(KnowledgeBaseChunk.ingestion_run_id == ingestion_run_id)
            if upload_id is not None:
                q = q.filter(KnowledgeBaseChunk.upload_id == upload_id)
            n = q.delete(synchronize_session=False)
            if self._session is None:
                db.commit()
        logger.debug("[pgvector] deleted {} chunks (filters={})", n, filters)
        return n

    def count(self, *, filters: Optional[dict] = None) -> int:
        filters = filters or {}
        with self._db() as db:
            q = db.query(KnowledgeBaseChunk)
            if filters.get("upload_id") is not None:
                q = q.filter(KnowledgeBaseChunk.upload_id == filters["upload_id"])
            if filters.get("ingestion_run_id") is not None:
                q = q.filter(
                    KnowledgeBaseChunk.ingestion_run_id == filters["ingestion_run_id"]
                )
            if filters.get("organization_id") is not None:
                q = q.filter(KnowledgeBaseChunk.organization_id == filters["organization_id"])
            return q.count()
