import json
import re
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from turbopuffer import NotFoundError, Turbopuffer

from core.config import settings
from core.database.session import get_db_context
from core.services.rag.errors import VectorStoreUnavailableError
from core.services.rag.logging_utils import format_scores, summarize_vector, truncate_query_text
from core.services.rag.run_scope import runs_for_filters, scoped_runs
from core.services.rag.types import SearchResult, VectorRecord
from core.services.rag.vector_stores.base import VectorStore
from core.services.rag.vector_stores.chunk_rows import (
    chunk_rows_query,
    insert_chunk_rows,
    require_metadata,
)

NAMESPACE_PREFIX = "tone-kb"
NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
DISTANCE_METRIC = "cosine_distance"
REQUEST_TIMEOUT = 20.0
MAX_RETRIES = 2

SCHEMA = {
    "organization_id": {"type": "uuid", "filterable": True},
    "upload_id": {"type": "uuid", "filterable": True},
    "knowledge_base_id": {"type": "uuid", "filterable": True},
    "ingestion_run_id": {"type": "uuid", "filterable": True},
    "chunk_index": {"type": "uint", "filterable": False},
    "embedding_provider": {"type": "string", "filterable": True},
    "embedding_model": {"type": "string", "filterable": True},
    "chunk_text": {"type": "string", "filterable": False},
    "chunk_metadata": {"type": "string", "filterable": False},
}

RESULT_ATTRIBUTES = ["upload_id", "chunk_index", "ingestion_run_id", "chunk_text", "chunk_metadata"]

_clients: Dict[Tuple[str, str], Turbopuffer] = {}
_clients_lock = threading.Lock()


def shared_client(api_key: Optional[str], region: Optional[str]) -> Turbopuffer:
    if not api_key or not region:
        raise VectorStoreUnavailableError(
            "turbopuffer needs TURBOPUFFER_API_KEY and TURBOPUFFER_REGION configured"
        )
    key = (api_key, region)
    with _clients_lock:
        client = _clients.get(key)
        if client is None:
            client = Turbopuffer(
                api_key=api_key, region=region, timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES
            )
            _clients[key] = client
    return client


def _optional_uuid(value: Any) -> Optional[str]:
    return str(value) if value else None


class TurbopufferVectorStore(VectorStore):
    def __init__(
        self,
        *,
        namespace_prefix: str = NAMESPACE_PREFIX,
        region: Optional[str] = None,
        session=None,
        client: Optional[Turbopuffer] = None,
    ):
        if not NAMESPACE_PATTERN.match(namespace_prefix or ""):
            raise ValueError(f"Invalid turbopuffer namespace_prefix {namespace_prefix!r}")
        self._prefix = namespace_prefix
        self._session = session
        self._client = client or shared_client(
            settings.TURBOPUFFER_API_KEY, region or settings.TURBOPUFFER_REGION
        )

    @contextmanager
    def _db(self):
        if self._session is not None:
            yield self._session
        else:
            with get_db_context() as db:
                yield db

    def namespace(self, org_id: Any, dims: int) -> str:
        return f"{self._prefix}-{org_id}-{int(dims)}"

    def add(self, records: List[VectorRecord]) -> int:
        if not records:
            return 0
        first = records[0].metadata
        run_id = first.get("ingestion_run_id")
        namespace = self.namespace(
            require_metadata(first, "organization_id"),
            require_metadata(first, "embedding_dimensions"),
        )
        logger.debug(
            "[turbopuffer] add start run={} namespace={} records={}",
            run_id, namespace, len(records),
        )
        with self._db() as db:
            try:
                chunks = insert_chunk_rows(db, records)
                rows = [
                    {
                        "id": str(chunk.id),
                        "vector": record.embedding,
                        "organization_id": str(chunk.organization_id),
                        "upload_id": str(chunk.upload_id),
                        "knowledge_base_id": _optional_uuid(record.metadata.get("knowledge_base_id")),
                        "ingestion_run_id": str(chunk.ingestion_run_id),
                        "chunk_index": chunk.chunk_index,
                        "embedding_provider": record.metadata.get("embedding_provider"),
                        "embedding_model": record.metadata.get("embedding_model"),
                        "chunk_text": record.text,
                        "chunk_metadata": json.dumps(record.metadata.get("chunk_metadata") or {}),
                    }
                    for chunk, record in zip(chunks, records)
                ]
                self._client.namespace(namespace).write(
                    upsert_rows=rows, distance_metric=DISTANCE_METRIC, schema=SCHEMA
                )
                if self._session is None:
                    db.commit()
            except Exception:
                logger.exception(
                    "[turbopuffer] add failed run={} namespace={} records={}",
                    run_id, namespace, len(records),
                )
                if self._session is None:
                    try:
                        db.rollback()
                    except Exception:
                        logger.exception("[turbopuffer] rollback failed run={}", run_id)
                raise
        logger.info(
            "[turbopuffer] added run={} namespace={} chunks={}", run_id, namespace, len(rows)
        )
        return len(rows)

    def query(
        self,
        embedding: List[float],
        top_k: int = 3,
        *,
        filters: Optional[dict] = None,
        query_text: Optional[str] = None,
    ) -> List[SearchResult]:
        filters = dict(filters or {})
        filters.setdefault("embedding_dimensions", len(embedding))
        vector_summary = summarize_vector(embedding)
        query_preview = truncate_query_text(query_text)
        started = time.monotonic()
        try:
            with self._db() as db:
                runs = scoped_runs(db, filters)
            grouped: Dict[str, List[str]] = defaultdict(list)
            for run_id, org_id, dims in runs:
                grouped[self.namespace(org_id, dims)].append(str(run_id))
            results: List[SearchResult] = []
            for namespace, run_ids in grouped.items():
                results.extend(self._search(namespace, embedding, top_k, run_ids))
            results.sort(key=lambda r: r.score)
            results = results[:top_k]
        except Exception:
            logger.exception(
                "[turbopuffer.query] failed query='{}' {} top_k={} filters={} duration_ms={}",
                query_preview, vector_summary, top_k, filters,
                round((time.monotonic() - started) * 1000),
            )
            raise
        logger.info(
            "[turbopuffer.query] query='{}' {} top_k={} provider={} model={} agent_id={} "
            "namespaces={} count={} chunk_ids={} scores={} duration_ms={}",
            query_preview, vector_summary, top_k,
            filters.get("embedding_provider"), filters.get("embedding_model"),
            filters.get("agent_id"), list(grouped), len(results),
            [r.id for r in results], format_scores(r.score for r in results),
            round((time.monotonic() - started) * 1000),
        )
        return results

    def _search(
        self, namespace: str, embedding: List[float], top_k: int, run_ids: List[str]
    ) -> List[SearchResult]:
        try:
            response = self._client.namespace(namespace).query(
                rank_by=("vector", "ANN", embedding),
                top_k=top_k,
                filters=("ingestion_run_id", "In", run_ids),
                include_attributes=RESULT_ATTRIBUTES,
            )
        except NotFoundError:
            logger.warning("[turbopuffer.query] namespace {} does not exist yet", namespace)
            return []
        return [
            SearchResult(
                text=row["chunk_text"],
                score=float(row["$dist"]),
                id=str(row.id),
                metadata={
                    "upload_id": row["upload_id"],
                    "chunk_index": row["chunk_index"],
                    "chunk_metadata": json.loads(row["chunk_metadata"]) if row["chunk_metadata"] else {},
                    "ingestion_run_id": row["ingestion_run_id"],
                },
            )
            for row in (response.rows or [])
        ]

    def delete(self, *, filters: dict) -> int:
        filters = filters or {}
        if filters.get("upload_id") is None and filters.get("ingestion_run_id") is None:
            raise ValueError(
                "TurbopufferVectorStore.delete requires filters['upload_id'] or filters['ingestion_run_id']"
            )
        with self._db() as db:
            grouped: Dict[str, List[str]] = defaultdict(list)
            for run_id, org_id, dims in runs_for_filters(db, filters):
                grouped[self.namespace(org_id, dims)].append(str(run_id))
            for namespace, run_ids in grouped.items():
                try:
                    self._client.namespace(namespace).write(
                        delete_by_filter=("ingestion_run_id", "In", run_ids)
                    )
                except NotFoundError:
                    logger.debug("[turbopuffer] namespace {} already absent", namespace)
            n = chunk_rows_query(db, filters).delete(synchronize_session=False)
            if self._session is None:
                db.commit()
        logger.info(
            "[turbopuffer] deleted {} chunks namespaces={} filters={}", n, list(grouped), filters
        )
        return n

    def count(self, *, filters: Optional[dict] = None) -> int:
        with self._db() as db:
            return chunk_rows_query(db, filters or {}).count()
