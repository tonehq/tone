"""ContactDirectoryService — CRUD over ``contact_directories`` plus the atomic
create-time provisioning of a directory's CSV datasource. Schemas are org-level and
reusable, so none is auto-created per directory; a directory's ``default_schema_id`` is
optional and user-selected.

Reuses the shared foundations: ``apply_search_sort_pagination`` (list),
``BaseService.get_or_404`` (fetch), ``ContactDatasourceService.ensure_csv_datasource``
(CSV provisioning), and ``directory_delete.*`` (impact summary + hard delete).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func

from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.models.contact_schema import ContactSchema
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.contacts.contact_datasource_service import ContactDatasourceService
from core.services.contacts.directory_delete import (
    hard_delete_directory_and_children,
    summarize_directory_deletion,
)


class ContactDirectoryService(BaseService):
    """Manage contact directories (the container that owns contacts + a CSV datasource)."""

    # The org's default landing directory — where ad-hoc contacts (e.g. numbers typed into
    # the Schedule modal) are created + assigned. Resolved by name to match the frontend,
    # which defaults the sync/upload target to a directory named "Global".
    DEFAULT_DIRECTORY_NAME = "Global"

    def get_or_create_default_directory(self) -> ContactDirectory:
        """Return the org's default "Global" directory, creating it (with its CSV
        datasource) if absent. Idempotent, org-scoped — the ONE way any flow lands ad-hoc
        contacts in a shared directory without re-implementing the resolve-or-provision."""
        existing = (
            self.query(ContactDirectory)
            .filter(
                func.lower(ContactDirectory.name) == self.DEFAULT_DIRECTORY_NAME.lower(),
                ContactDirectory.deleted_at.is_(None),
            )
            .order_by(ContactDirectory.created_at.asc())
            .first()
        )
        if existing is not None:
            return existing
        logger.info("[contact-directory] provisioning default '%s' directory", self.DEFAULT_DIRECTORY_NAME)
        return self.create_directory(name=self.DEFAULT_DIRECTORY_NAME, description="Default contacts directory")

    def create_directory(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        default_schema_id: Optional[UUID] = None,
    ) -> ContactDirectory:
        """Create a directory and provision its CSV datasource. Single transaction.

        Schemas are org-level and reusable, so a directory does NOT get an auto-created
        schema — that would pollute the shared library with one throwaway schema per
        directory. ``default_schema_id`` is optional: when the caller passes one (chosen
        by the user), it is validated org-owned and set; otherwise the directory has no
        default schema until the user assigns one (manual add / sync still work — they
        just skip field validation while no schema is set).
        """
        directory = ContactDirectory(
            organization_id=self.org_id,
            name=name,
            description=description,
            created_by_user_id=self.user_id,
            is_active=True,
        )
        if default_schema_id is not None:
            # Validate the schema belongs to this org (no IDOR / cross-org reference).
            self.get_or_404(ContactSchema, default_schema_id, name="Schema")
            directory.default_schema_id = default_schema_id

        self.db.add(directory)
        self.db.flush()  # assign directory.id without committing yet

        self.create_default_datasource(directory)

        self.db.commit()
        self.db.refresh(directory)
        logger.info(
            "[contact-directory] created id={} name={} default_schema_id={}",
            directory.id, name, directory.default_schema_id,
        )
        return directory

    def create_default_datasource(self, directory: ContactDirectory) -> None:
        """Provision one CSV datasource for ``directory`` (idempotent). Does NOT commit —
        the caller owns the transaction. No schema is created here (schemas are org-level
        and user-managed via the schema library)."""
        datasource_service = ContactDatasourceService(
            self.db, user_id=self.user_id, org_id=self.org_id
        )
        datasource_service.ensure_csv_datasource(directory.id)
        self.db.flush()

    def list_directories(
        self,
        *,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """List org directories (paginated), each enriched with its ``contact_count``."""
        query = self.query(ContactDirectory).filter(ContactDirectory.deleted_at.is_(None))
        rows, total = apply_search_sort_pagination(
            query,
            search=search,
            search_fields=[ContactDirectory.name],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "name": ContactDirectory.name,
                "created_at": ContactDirectory.created_at,
                "updated_at": ContactDirectory.updated_at,
            },
            page_no=page_no,
            page_size=page_size,
        )

        dir_ids = [d.id for d in rows]
        counts_by_dir: Dict[Any, int] = {}
        if dir_ids:
            count_rows = (
                self.db.query(Contact.directory_id, func.count(Contact.id))
                .filter(
                    Contact.organization_id == self.org_id,
                    Contact.directory_id.in_(dir_ids),
                    Contact.deleted_at.is_(None),
                )
                .group_by(Contact.directory_id)
                .all()
            )
            counts_by_dir = {dir_id: cnt for dir_id, cnt in count_rows}

        data = []
        for directory in rows:
            item = directory.to_dict()
            item["contact_count"] = counts_by_dir.get(directory.id, 0)
            data.append(item)

        return {
            "data": data,
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def get_directory(self, directory_id: UUID) -> ContactDirectory:
        """Fetch a single org-owned directory or raise 404."""
        return self.get_or_404(ContactDirectory, directory_id, name="Directory")

    def update_directory(
        self,
        directory_id: UUID,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        default_schema_id: Optional[UUID] = None,
    ) -> ContactDirectory:
        """Update a directory. ``default_schema_id`` may be re-pointed to any org schema
        (validated org-owned first — never allow pointing at another org's schema)."""
        directory = self.get_or_404(ContactDirectory, directory_id, name="Directory")

        if name is not None:
            directory.name = name
        if description is not None:
            directory.description = description
        if is_active is not None:
            directory.is_active = is_active
        if default_schema_id is not None:
            # Validate the schema belongs to this org (no IDOR / cross-org reference).
            self.get_or_404(ContactSchema, default_schema_id, name="Schema")
            directory.default_schema_id = default_schema_id

        directory.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(directory)
        logger.info("[contact-directory] updated id={}", directory_id)
        return directory

    def delete_impact(self, directory_id: UUID) -> Dict[str, Any]:
        """Summarize the blast radius of deleting ``directory_id`` (for the confirm
        modal). Reuses ``summarize_directory_deletion``."""
        return summarize_directory_deletion(self.db, self.org_id, directory_id)

    def delete_directory(self, directory_id: UUID) -> Dict[str, Any]:
        """Hard-delete the directory and its owned children (FK-safe, single txn).
        Reuses ``hard_delete_directory_and_children``."""
        return hard_delete_directory_and_children(self.db, self.org_id, directory_id)
