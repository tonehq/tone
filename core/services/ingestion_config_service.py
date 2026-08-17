"""Ingestion configs — CRUD for named, reusable ingestion pipeline recipes.

Transport-agnostic per project backend standards: every method takes plain
args + the session inherited from ``BaseService`` and returns ORM objects or
plain dicts. Never raises HTTP-specific concepts other than ``HTTPException``
for the same validation surface already used elsewhere (name uniqueness,
unknown slugs, org-scoped 404).

The service is the single source of truth for:
- validation of parser / tokeniser / embedding_provider / vector_store slugs
  against the live RAG registries (so a config that survives creation is
  guaranteed to instantiate at run time),
- org-scoped fetches used by BOTH the CRUD router AND
  ``IngestionRunService.resolve_run_config`` (snapshot-from-config path).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.models.ingestion_config import IngestionConfig
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.rag.embedder_factory import EMBEDDERS
from core.services.rag.factory import VECTOR_STORES
from core.services.rag.parser_factory import PARSERS
from core.services.rag.tokeniser_factory import TOKENISERS


def _is_unique_violation(exc: IntegrityError) -> bool:
    """True when the IntegrityError was raised by a Postgres unique-constraint
    violation (SQLSTATE ``23505``). Other IntegrityErrors (NOT NULL, CHECK,
    FK) must NOT be mapped to a friendly 'name already exists' 400 — they
    signal real bugs and should surface a 500 after logger.exception."""
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None)
    return pgcode == "23505"


class IngestionConfigService(BaseService):

    _LIST_SORT_MAP = {
        "created_at": IngestionConfig.created_at,
        "updated_at": IngestionConfig.updated_at,
        "name": IngestionConfig.name,
    }

    # embedding_dimensions must match a real
    # knowledge_base_chunk_embeddings.embedding_<dim> column, otherwise the
    # chunk-write step fails at ingest time. Kept in sync with
    # core/models/knowledge_base_chunk_embedding.py.
    _ALLOWED_EMBEDDING_DIMENSIONS: frozenset[int] = frozenset({1024, 1536, 3072})

    # Only these attributes are writable via update_config. Explicit allowlist
    # blocks a future/misuse caller from mutating organization_id, id,
    # deleted_at, created_at via partial_fields (defense-in-depth beyond the
    # Pydantic UpdateIngestionConfigRequest).
    _UPDATABLE_FIELDS: frozenset[str] = frozenset({
        "name",
        "description",
        "parser",
        "parser_config",
        "tokeniser",
        "tokeniser_config",
        "embedding_provider",
        "embedding_model",
        "embedding_dimensions",
        "embedding_version",
        "embedding_config",
        "vector_store",
        "vector_store_ref",
        "is_active",
    })

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _validate_slugs(
        *,
        parser: Optional[str] = None,
        tokeniser: Optional[str] = None,
        embedding_provider: Optional[str] = None,
        vector_store: Optional[str] = None,
    ) -> None:
        """Fail-fast on obvious mis-typed slugs so a bad recipe never makes it
        into the DB. Enforced at write time regardless of the caller (backend
        validation per project rules)."""
        if parser is not None and parser not in PARSERS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown parser {parser!r}. Available: {sorted(PARSERS)}"
                ),
            )
        if tokeniser is not None and tokeniser not in TOKENISERS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown tokeniser {tokeniser!r}. Available: {sorted(TOKENISERS)}"
                ),
            )
        if embedding_provider is not None and embedding_provider not in EMBEDDERS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown embedding provider {embedding_provider!r}. "
                    f"Available: {sorted(EMBEDDERS)}"
                ),
            )
        if vector_store is not None and vector_store not in VECTOR_STORES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unknown vector store {vector_store!r}. "
                    f"Available: {sorted(VECTOR_STORES)}"
                ),
            )

    def _name_taken(self, name: str, *, exclude_id: Optional[Any] = None) -> bool:
        q = (
            self.query(IngestionConfig)
            .filter(
                IngestionConfig.name == name,
                IngestionConfig.deleted_at.is_(None),
            )
        )
        if exclude_id is not None:
            q = q.filter(IngestionConfig.id != exclude_id)
        return q.first() is not None

    # ── CRUD ────────────────────────────────────────────────────────────

    def create_config(
        self,
        *,
        name: str,
        parser: str,
        tokeniser: str,
        embedding_provider: str,
        embedding_model: str,
        embedding_dimensions: int,
        vector_store: str,
        description: Optional[str] = None,
        parser_config: Optional[dict] = None,
        tokeniser_config: Optional[dict] = None,
        embedding_version: Optional[str] = None,
        embedding_config: Optional[dict] = None,
        vector_store_ref: Optional[dict] = None,
        is_active: bool = True,
    ) -> IngestionConfig:
        if not name or not name.strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="name is required.",
            )
        if embedding_dimensions is None or embedding_dimensions <= 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="embedding_dimensions must be a positive integer.",
            )
        if embedding_dimensions not in self._ALLOWED_EMBEDDING_DIMENSIONS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"embedding_dimensions {embedding_dimensions} is not supported. "
                    f"Allowed: {sorted(self._ALLOWED_EMBEDDING_DIMENSIONS)}. "
                    "Add a knowledge_base_chunk_embeddings.embedding_<dim> column + "
                    "HNSW index to enable a new value."
                ),
            )
        self._validate_slugs(
            parser=parser,
            tokeniser=tokeniser,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )
        if self._name_taken(name.strip()):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"An ingestion config named {name!r} already exists.",
            )

        row = IngestionConfig(
            organization_id=self.org_id,
            name=name.strip(),
            description=description,
            parser=parser,
            parser_config=parser_config,
            tokeniser=tokeniser,
            tokeniser_config=tokeniser_config,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            embedding_version=embedding_version,
            embedding_config=embedding_config,
            vector_store=vector_store,
            vector_store_ref=vector_store_ref,
            is_active=is_active,
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if _is_unique_violation(exc):
                # Race: two concurrent creates on the same (org, name). Log
                # at info — this is expected under contention.
                logger.info(
                    "[ingestion-config] create race on (org, name)=({}, {}) — "
                    "converted to 400", self.org_id, name,
                )
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"An ingestion config named {name!r} already exists.",
                )
            # Any other constraint violation is a real bug — log full
            # traceback + re-raise so operators can diagnose (project rule:
            # every except captures via logger.exception).
            logger.exception(
                "[ingestion-config] unexpected IntegrityError creating config "
                "org={} name={}", self.org_id, name,
            )
            raise
        self.db.refresh(row)
        logger.info(
            "[ingestion-config] created id={} name={} parser={} tokeniser={} "
            "provider={} model={} dims={} store={}",
            row.id, row.name, row.parser, row.tokeniser,
            row.embedding_provider, row.embedding_model,
            row.embedding_dimensions, row.vector_store,
        )
        return row

    def update_config(self, config_id: Any, **partial_fields) -> IngestionConfig:
        row = self.get_or_404(
            IngestionConfig, config_id, name="Ingestion config"
        )

        # Slug re-validation applies only to changed enum fields.
        self._validate_slugs(
            parser=partial_fields.get("parser"),
            tokeniser=partial_fields.get("tokeniser"),
            embedding_provider=partial_fields.get("embedding_provider"),
            vector_store=partial_fields.get("vector_store"),
        )

        if "embedding_dimensions" in partial_fields:
            dims = partial_fields["embedding_dimensions"]
            if dims is None or dims <= 0:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="embedding_dimensions must be a positive integer.",
                )
            if dims not in self._ALLOWED_EMBEDDING_DIMENSIONS:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"embedding_dimensions {dims} is not supported. "
                        f"Allowed: {sorted(self._ALLOWED_EMBEDDING_DIMENSIONS)}."
                    ),
                )

        if "name" in partial_fields:
            new_name = (partial_fields["name"] or "").strip()
            if not new_name:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="name cannot be blank.",
                )
            if new_name != row.name and self._name_taken(new_name, exclude_id=row.id):
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"An ingestion config named {new_name!r} already exists.",
                )
            partial_fields["name"] = new_name

        # Allowlist: any key outside _UPDATABLE_FIELDS is silently dropped
        # rather than blindly setattr'd — defense-in-depth so a future caller
        # can't move a config across tenants by passing organization_id, or
        # resurrect a soft-deleted row by clearing deleted_at.
        rejected = [k for k in partial_fields if k not in self._UPDATABLE_FIELDS]
        if rejected:
            logger.warning(
                "[ingestion-config] update_config dropping non-writable fields {} "
                "on config={}",
                rejected, config_id,
            )
        for key, value in partial_fields.items():
            if key in self._UPDATABLE_FIELDS:
                setattr(row, key, value)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if _is_unique_violation(exc):
                logger.info(
                    "[ingestion-config] update race on (org, name) for config={} — "
                    "converted to 400", config_id,
                )
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Name conflict updating ingestion config.",
                )
            logger.exception(
                "[ingestion-config] unexpected IntegrityError updating config={}",
                config_id,
            )
            raise
        self.db.refresh(row)
        logger.info(
            "[ingestion-config] updated id={} fields={}",
            row.id, sorted(partial_fields.keys()),
        )
        return row

    def get_config(self, config_id: Any) -> IngestionConfig:
        """Org-scoped, excludes soft-deleted. Used by the CRUD endpoint AND
        by ``IngestionRunService.resolve_run_config`` (snapshot path)."""
        return self.get_or_404(
            IngestionConfig, config_id, name="Ingestion config"
        )

    def delete_config(self, config_id: Any) -> dict:
        """Soft-delete. The FK on ``ingestion_pipeline_runs.ingestion_config_id``
        is ``SET NULL`` at the DB level, but soft-delete keeps the row so audit
        lookups from historical runs still resolve — list/select queries filter
        it out."""
        row = self.get_or_404(
            IngestionConfig, config_id, name="Ingestion config"
        )
        row.deleted_at = datetime.now(timezone.utc)
        row.is_active = False
        self.db.commit()
        logger.info("[ingestion-config] soft-deleted id={}", config_id)
        return {"id": str(row.id), "deleted": True}

    def list_configs(
        self,
        *,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        is_active_only: bool = False,
    ) -> dict:
        base = (
            self.query(IngestionConfig)
            .filter(IngestionConfig.deleted_at.is_(None))
        )
        if is_active_only:
            base = base.filter(IngestionConfig.is_active.is_(True))

        rows, total = apply_search_sort_pagination(
            base,
            search=search,
            search_fields=[
                IngestionConfig.name,
                IngestionConfig.parser,
                IngestionConfig.tokeniser,
                IngestionConfig.embedding_provider,
                IngestionConfig.embedding_model,
                IngestionConfig.vector_store,
            ],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map=self._LIST_SORT_MAP,
            page_no=page_no,
            page_size=page_size,
        )
        return {
            "data": [self.config_response(r) for r in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def config_response(self, config: IngestionConfig) -> dict:
        """The single response formatter (per project API convention)."""
        return config.to_dict()
