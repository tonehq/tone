from typing import Any, List

from loguru import logger

from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.services.rag.errors import EmbeddingCompatibilityError
from core.services.rag.types import VectorRecord


def require_metadata(metadata: dict, key: str) -> Any:
    value = metadata.get(key)
    if value is None:
        raise ValueError(f"record.metadata missing required key {key!r}")
    return value


def insert_chunk_rows(db, records: List[VectorRecord]) -> List[KnowledgeBaseChunk]:
    rows = []
    for record in records:
        dims = int(require_metadata(record.metadata, "embedding_dimensions"))
        if dims != len(record.embedding):
            logger.error(
                "[vector-store] dimension mismatch run={} metadata_dims={} vector_dims={}",
                record.metadata.get("ingestion_run_id"), dims, len(record.embedding),
            )
            raise EmbeddingCompatibilityError(
                f"Embedding dimension mismatch: metadata says {dims} but vector is "
                f"{len(record.embedding)}-D"
            )
        rows.append(
            KnowledgeBaseChunk(
                organization_id=require_metadata(record.metadata, "organization_id"),
                upload_id=require_metadata(record.metadata, "upload_id"),
                ingestion_run_id=require_metadata(record.metadata, "ingestion_run_id"),
                chunk_index=int(require_metadata(record.metadata, "chunk_index")),
                chunk_text=record.text,
                chunk_metadata=record.metadata.get("chunk_metadata"),
            )
        )
    db.add_all(rows)
    db.flush()
    return rows


def chunk_rows_query(db, filters: dict):
    q = db.query(KnowledgeBaseChunk)
    if filters.get("organization_id") is not None:
        q = q.filter(KnowledgeBaseChunk.organization_id == filters["organization_id"])
    if filters.get("ingestion_run_id") is not None:
        q = q.filter(KnowledgeBaseChunk.ingestion_run_id == filters["ingestion_run_id"])
    if filters.get("upload_id") is not None:
        q = q.filter(KnowledgeBaseChunk.upload_id == filters["upload_id"])
    return q
