"""Ingestion configs — CRUD for named, reusable ingestion pipeline recipes.

Transport-agnostic per project backend standards: every method takes plain
args + the session inherited from ``BaseService`` and returns ORM objects or
plain dicts. Business-rule failures raise typed exceptions from
``core.services.ingestion_errors`` — never ``HTTPException``. The router
layer converts them to HTTP responses.

The service is the single source of truth for:
- validation of parser / tokeniser / embedding_provider / vector_store slugs
  against the live RAG registries (via ``ensure_rag_recipe``) so a config
  that survives creation is guaranteed to instantiate at run time,
- org-scoped fetches used by BOTH the CRUD router AND
  ``IngestionRunService.resolve_run_config`` (snapshot-from-config path).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.models.ingestion_config import IngestionConfig
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.ingestion_errors import (
    IngestionConfigNameConflictError,
    IngestionConfigNotFoundError,
    IngestionValidationError,
    is_unique_violation,
)
from core.services.rag.component_registry import ensure_rag_recipe


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

    @classmethod
    def _validate_embedding_dimensions(
        cls, dims: Optional[int], *, positive_msg: Optional[str] = None,
    ) -> None:
        """embedding_dimensions must be a positive integer and one of the
        supported dedicated columns on ``knowledge_base_chunk_embeddings``.
        Kept as one method so create + update share the invalid-dims text,
        but the "positive integer" message differs by call site
        (``create_config`` used lowercase ``embedding_dimensions``; the
        historic ``update_config`` said "Embedding dimensions" with a
        capital E) — preserved byte-for-byte via ``positive_msg`` so any
        FE code that string-matches keeps working."""
        if dims is None or dims <= 0:
            raise IngestionValidationError(
                positive_msg or "embedding_dimensions must be a positive integer."
            )
        if dims not in cls._ALLOWED_EMBEDDING_DIMENSIONS:
            raise IngestionValidationError(
                "Invalid embedding dimensions. Allowed: "
                f"{', '.join(str(d) for d in sorted(cls._ALLOWED_EMBEDDING_DIMENSIONS))}."
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

    def _get_config_or_404(self, config_id: Any) -> IngestionConfig:
        """Local get-or-404 that raises the typed
        :class:`IngestionConfigNotFoundError` (not FastAPI's HTTPException).
        Kept private so the router-facing get_config path stays a thin alias."""
        row = (
            self.query(IngestionConfig)
            .filter(
                IngestionConfig.id == config_id,
                IngestionConfig.deleted_at.is_(None),
            )
            .first()
        )
        if row is None:
            raise IngestionConfigNotFoundError("Ingestion config not found.")
        return row

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
            raise IngestionValidationError("Name is required.")
        self._validate_embedding_dimensions(embedding_dimensions)
        ensure_rag_recipe(
            parser=parser,
            tokeniser=tokeniser,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )
        if self._name_taken(name.strip()):
            raise IngestionConfigNameConflictError(
                f"An ingestion config named {name!r} already exists."
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
            if is_unique_violation(exc):
                # Race: two concurrent creates on the same (org, name). Log
                # at info — this is expected under contention.
                logger.info(
                    "[ingestion-config] create race on (org, name)=({}, {}) — "
                    "converted to 400", self.org_id, name,
                )
                raise IngestionConfigNameConflictError(
                    f"An ingestion config named {name!r} already exists."
                ) from exc
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
        row = self._get_config_or_404(config_id)

        # Slug re-validation applies only to changed enum fields.
        ensure_rag_recipe(
            parser=partial_fields.get("parser"),
            tokeniser=partial_fields.get("tokeniser"),
            embedding_provider=partial_fields.get("embedding_provider"),
            vector_store=partial_fields.get("vector_store"),
        )

        if "embedding_dimensions" in partial_fields:
            self._validate_embedding_dimensions(
                partial_fields["embedding_dimensions"],
                positive_msg="Embedding dimensions must be a positive integer.",
            )

        if "name" in partial_fields:
            new_name = (partial_fields["name"] or "").strip()
            if not new_name:
                raise IngestionValidationError("Name cannot be blank.")
            if new_name != row.name and self._name_taken(new_name, exclude_id=row.id):
                raise IngestionConfigNameConflictError(
                    f"An ingestion config named {new_name!r} already exists."
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
            if is_unique_violation(exc):
                logger.info(
                    "[ingestion-config] update race on (org, name) for config={} — "
                    "converted to 400", config_id,
                )
                raise IngestionConfigNameConflictError(
                    "Name conflict updating ingestion config."
                ) from exc
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
        return self._get_config_or_404(config_id)

    def delete_config(self, config_id: Any) -> IngestionConfig:
        """Soft-delete. The FK on ``ingestion_pipeline_runs.ingestion_config_id``
        is ``SET NULL`` at the DB level, but soft-delete keeps the row so audit
        lookups from historical runs still resolve — list/select queries filter
        it out. Returns the soft-deleted row so the router can shape the
        response via ``config_response``."""
        row = self._get_config_or_404(config_id)
        row.deleted_at = datetime.now(timezone.utc)
        row.is_active = False
        self.db.commit()
        logger.info("[ingestion-config] soft-deleted id={}", config_id)
        return row

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
