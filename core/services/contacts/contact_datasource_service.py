"""ContactDatasourceService — org-scoped CRUD over ``datasources`` (CSV-only at launch).

A directory auto-provisions exactly one CSV datasource on create; admins can add more
later. ``ensure_csv_datasource`` is the shared idempotent accessor used by the sync
pipeline to resolve (or lazily create) a directory's CSV datasource without duplicating.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from loguru import logger

from core.models.datasource import Datasource
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination


class ContactDatasourceService(BaseService):
    """Manage the datasources that feed contacts into directories (CSV type only)."""

    def create_datasource(
        self,
        *,
        name: str,
        directory_id: Optional[UUID] = None,
        type: str = "csv",
        config: Optional[Dict[str, Any]] = None,
    ) -> Datasource:
        """Create a datasource (CSV only at launch). ``directory_id`` may be null for a
        future org-level (REST) datasource."""
        if type != "csv":
            raise HTTPException(status_code=400, detail="Only 'csv' datasources are supported.")
        if directory_id is not None:
            # Validate the directory is org-owned before binding to it (no IDOR).
            from core.models.contact_directory import ContactDirectory

            self.get_or_404(ContactDirectory, directory_id, name="Directory")

        datasource = Datasource(
            organization_id=self.org_id,
            directory_id=directory_id,
            name=name,
            type=type,
            config=config or {},
            created_by_user_id=self.user_id,
            is_active=True,
        )
        self.db.add(datasource)
        self.db.commit()
        self.db.refresh(datasource)
        logger.info(
            "[contact-datasource] created id={} name={} directory_id={}",
            datasource.id, name, directory_id,
        )
        return datasource

    def ensure_csv_datasource(self, directory_id: UUID) -> Datasource:
        """Return the directory's existing CSV datasource, or create one if absent.

        Idempotent — safe to call from the sync pipeline on every run. Validates the
        directory is org-owned first (no IDOR). Does NOT re-create when one already
        exists (returns the first active CSV datasource bound to the directory).

        Does NOT commit — the new row is flushed so it gets an id, but the caller owns
        the transaction (so directory-create and sync-create stay atomic).
        """
        from core.models.contact_directory import ContactDirectory

        self.get_or_404(ContactDirectory, directory_id, name="Directory")

        existing = (
            self.query(Datasource)
            .filter(
                Datasource.directory_id == directory_id,
                Datasource.type == "csv",
                Datasource.deleted_at.is_(None),
            )
            .order_by(Datasource.created_at.asc())
            .first()
        )
        if existing is not None:
            return existing

        datasource = Datasource(
            organization_id=self.org_id,
            directory_id=directory_id,
            name="CSV Import",
            type="csv",
            config={},
            created_by_user_id=self.user_id,
            is_active=True,
        )
        self.db.add(datasource)
        self.db.flush()  # assign the id without committing — the caller owns the txn
        logger.info(
            "[contact-datasource] auto-provisioned CSV datasource id={} directory_id={}",
            datasource.id, directory_id,
        )
        return datasource

    def list_datasources(
        self,
        *,
        directory_id: Optional[UUID] = None,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """List org datasources (optionally scoped to one directory), paginated."""
        query = self.query(Datasource).filter(Datasource.deleted_at.is_(None))
        if directory_id is not None:
            query = query.filter(Datasource.directory_id == directory_id)

        rows, total = apply_search_sort_pagination(
            query,
            search=search,
            search_fields=[Datasource.name],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "name": Datasource.name,
                "created_at": Datasource.created_at,
                "updated_at": Datasource.updated_at,
            },
            page_no=page_no,
            page_size=page_size,
        )
        return {
            "data": [row.to_dict() for row in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def delete_datasource(self, datasource_id: UUID) -> None:
        """Soft-delete a datasource (org-scoped)."""
        from datetime import datetime, timezone

        datasource = self.get_or_404(Datasource, datasource_id, name="Datasource")
        datasource.deleted_at = datetime.now(timezone.utc)
        datasource.is_active = False
        self.db.commit()
        logger.info("[contact-datasource] deleted id={}", datasource_id)
