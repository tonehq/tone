"""Directory-scoped contact service — CRUD + bulk partial multi-add.

Every contact belongs to exactly one ``ContactDirectory``; all reads/writes are both
org-scoped (via ``self.query``) AND directory-scoped so a caller can never touch another
organization's — or another directory's — contacts (no IDOR).

Metadata is validated against the *directory's default schema* (a reusable org-level
``ContactSchema``) using the shared validator in ``contact_metadata_validation``; the
write itself goes through the shared ``upsert_contact`` helper so the
``(directory_id, external_id)`` uniqueness rule and ``sync_id`` handling live in one place.

Upload/import (CSV → R2 → Procrastinate) and schema/field CRUD are intentionally NOT here:
importing moved to the sync service and schema CRUD moved to the schema service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from loguru import logger

from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.models.schema_field import SchemaField
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.contacts.contact_metadata_validation import (
    make_contact_metadata_validator,
    validate_contact_metadata,
)
from core.services.contacts.contact_upsert import upsert_contact


class ContactService(BaseService):
    """Directory-scoped CRUD for ``Contact`` rows."""

    # Cap a single multi-add so one request can't create unbounded rows in one commit.
    MAX_CREATE_ROWS = 1_000

    # --------------------------------------------------------------- directory

    def _get_directory(self, directory_id: UUID) -> ContactDirectory:
        """Fetch an org-owned directory or 404 (shared IDOR guard for every
        directory-scoped operation)."""
        return self.get_or_404(ContactDirectory, directory_id, name="Directory")

    def _metadata_validator(self, directory: ContactDirectory):
        """Build the ``(managed_keys, validator)`` pair from the directory's default
        schema, or ``(set(), None)`` when the directory has no default schema (so
        contacts still work before any schema is attached).

        Only the schema's ACTIVE, non-deleted fields are used.
        """
        if not directory.default_schema_id:
            return set(), None
        fields = (
            self.query(SchemaField)
            .filter(
                SchemaField.schema_id == directory.default_schema_id,
                SchemaField.deleted_at.is_(None),
                SchemaField.is_active.is_(True),
            )
            .all()
        )
        return make_contact_metadata_validator(fields)

    # -------------------------------------------------------------------- read

    def list_contacts(
        self,
        directory_id: UUID,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """List the active contacts in ``directory_id`` (org- + directory-scoped)."""
        self._get_directory(directory_id)
        q = self.query(Contact).filter(
            Contact.directory_id == directory_id,
            Contact.deleted_at.is_(None),
        )
        rows, total = apply_search_sort_pagination(
            q,
            search=search,
            search_fields=[Contact.name, Contact.external_id, Contact.phone_number],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "created_at": Contact.created_at,
                "name": Contact.name,
                "updated_at": Contact.updated_at,
                "phone_number": Contact.phone_number,
            },
            page_no=page_no,
            page_size=page_size,
        )
        return {
            "data": [c.to_dict() for c in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def get_contact(self, contact_id: UUID) -> Contact:
        """Fetch a single org-owned, non-deleted contact or 404."""
        return self.get_or_404(Contact, contact_id, name="Contact")

    # ------------------------------------------------------------------- write

    def create_contacts(
        self, directory_id: UUID, rows: List[Dict[str, Any]], *, agent_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Bulk-create contacts in ``directory_id`` with PARTIAL success.

        Each row is validated against the directory's default schema; valid rows are
        saved (upsert on ``(directory_id, external_id)``) and invalid rows are collected.
        A duplicate ``external_id`` within the same directory upserts the existing row
        (counted as created output) rather than failing.

        When ``agent_id`` is given, the freshly-created contacts are ALSO assigned to that
        agent (Agent Contacts flow) via ``AgentContactService`` — kept here so the router
        stays thin and create+assign is one reusable service call. The response then also
        carries ``"assigned"``.

        Returns ``{"created": [contact_dict, ...], "failed": [{"index", "errors"}, ...]}``
        (plus ``"assigned"`` when ``agent_id`` was provided). Valid rows commit even when
        some rows fail (all-or-nothing is NOT used).
        """
        directory = self._get_directory(directory_id)
        if not rows:
            raise HTTPException(status_code=400, detail="Provide at least one contact.")
        if len(rows) > self.MAX_CREATE_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"Too many contacts in one request (max {self.MAX_CREATE_ROWS}).",
            )

        managed, validator = self._metadata_validator(directory)

        created_by_ext: Dict[str, Contact] = {}
        failed: List[Dict[str, Any]] = []

        for index, row in enumerate(rows):
            metadata = row.get("contact_metadata") or {}
            errors = validate_contact_metadata(metadata, managed, validator)
            if errors:
                failed.append({"index": index, "errors": errors})
                continue

            name = (row.get("name") or "").strip() or None
            phone_number = (row.get("phone_number") or "").strip() or None
            # A contact must carry at least one identifying value — never create a
            # fully-empty row (name + phone both blank).
            if not name and not phone_number:
                failed.append(
                    {"index": index, "errors": ["A contact needs at least a name or phone number."]}
                )
                continue
            external_id = (
                (row.get("external_id") or "").strip()
                or (phone_number or "")
                or f"manual-{uuid4().hex[:16]}"
            )
            parsed = {
                "external_id": external_id,
                "name": name,
                "phone_number": phone_number,
                "contact_metadata": metadata,
            }
            contact, _action = upsert_contact(
                self.db,
                directory_id,
                parsed,
                organization_id=self.org_id,
                created_by_user_id=self.user_id,
            )
            created_by_ext[external_id] = contact

        created = list(created_by_ext.values())

        if created:
            try:
                self.db.commit()
                for c in created:
                    self.db.refresh(c)
            except Exception:
                logger.exception(
                    "[contacts] multi-add commit failed directory_id={}", directory_id
                )
                self.db.rollback()
                raise

        logger.info(
            "[contacts] multi-add directory_id={} created={} failed={}",
            directory_id,
            len(created),
            len(failed),
        )
        result: Dict[str, Any] = {"created": [c.to_dict() for c in created], "failed": failed}

        # Optionally assign the freshly-created contacts to an agent (Agent Contacts flow).
        # Done in the service so the router stays thin and create+assign is one call.
        if agent_id and created:
            try:
                assignment = self._assign_created_contacts_to_agent(agent_id, [c.id for c in created])
                result["assigned"] = assignment.get("assigned", 0)
            except Exception:
                logger.exception(
                    "[contacts] created contacts but agent-assign failed agent_id={} directory_id={}",
                    agent_id, directory_id,
                )
                result["assigned"] = 0
                result["assign_failed"] = True

        return result

    def _assign_created_contacts_to_agent(
        self, agent_id: UUID, contact_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Assign the given contacts to ``agent_id`` (idempotent), reusing
        ``AgentContactService.assign_contacts_to_agent``. Imported locally to avoid a
        service-layer import cycle."""
        from core.services.contacts.agent_contact_service import AgentContactService

        assignment = AgentContactService(
            self.db, user_id=self.user_id, org_id=self.org_id
        ).assign_contacts_to_agent(agent_id, contact_ids=contact_ids)
        logger.info(
            "[contacts] created contacts assigned to agent agent_id={} assigned={}",
            agent_id,
            assignment.get("assigned"),
        )
        return assignment

    def update_contact(
        self,
        contact_id: UUID,
        name: Optional[str] = None,
        phone_number: Optional[str] = None,
        contact_metadata: Optional[Dict[str, Any]] = None,
    ) -> Contact:
        """Update a single org-owned contact; validates metadata against its directory's
        default schema when metadata is provided."""
        contact = self.get_contact(contact_id)
        if contact_metadata is not None:
            directory = self._get_directory(contact.directory_id)
            managed, validator = self._metadata_validator(directory)
            errors = validate_contact_metadata(contact_metadata, managed, validator)
            if errors:
                raise HTTPException(status_code=400, detail="; ".join(errors))
            contact.contact_metadata = contact_metadata
        # Preserve the create-time invariant: a contact must keep at least one of
        # name / phone_number, otherwise it becomes an identity-less, un-dialable row.
        # Validate the resulting identity BEFORE mutating so a rejected update leaves
        # the row untouched.
        new_name = (name or None) if name is not None else contact.name
        new_phone = (phone_number or None) if phone_number is not None else contact.phone_number
        if not new_name and not new_phone:
            raise HTTPException(
                status_code=400,
                detail="A contact needs at least a name or phone number.",
            )
        if name is not None:
            contact.name = new_name
        if phone_number is not None:
            contact.phone_number = new_phone
        try:
            self.db.commit()
            self.db.refresh(contact)
        except Exception:
            logger.exception("[contacts] update failed contact_id={}", contact_id)
            self.db.rollback()
            raise
        return contact

    def delete_contact(self, contact_id: UUID) -> None:
        """Soft-delete a single org-owned contact."""
        contact = self.get_contact(contact_id)
        contact.deleted_at = datetime.now(timezone.utc)
        contact.is_active = False
        try:
            self.db.commit()
        except Exception:
            logger.exception("[contacts] delete failed contact_id={}", contact_id)
            self.db.rollback()
            raise

    def bulk_delete_contacts(
        self, directory_id: UUID, ids: List[UUID]
    ) -> Dict[str, Any]:
        """Soft-delete many contacts within ``directory_id`` (org- + directory-scoped)."""
        self._get_directory(directory_id)
        now = datetime.now(timezone.utc)
        try:
            deleted = (
                self.query(Contact)
                .filter(
                    Contact.directory_id == directory_id,
                    Contact.id.in_(ids),
                    Contact.deleted_at.is_(None),
                )
                .update(
                    {Contact.deleted_at: now, Contact.is_active: False},
                    synchronize_session=False,
                )
            )
            self.db.commit()
        except Exception:
            logger.exception(
                "[contacts] bulk delete failed directory_id={}", directory_id
            )
            self.db.rollback()
            raise
        logger.info(
            "[contacts] bulk delete directory_id={} deleted={}", directory_id, int(deleted)
        )
        return {"deleted": int(deleted)}

    # ------------------------------------------------------------- shared helper

    def list_contact_ids_in_directories(
        self, directory_ids: List[UUID]
    ) -> List[UUID]:
        """Return the active (non-deleted) contact ids across ``directory_ids``.

        REUSABLE shared helper — used to expand a whole-directory selection into its
        contacts (e.g. agent assignment) without materialising full rows. Org-scoped, so
        a directory id from another org contributes nothing. Returns ``[]`` for an empty
        input.
        """
        if not directory_ids:
            return []
        rows = (
            self.query(Contact)
            .filter(
                Contact.directory_id.in_(directory_ids),
                Contact.deleted_at.is_(None),
            )
            .with_entities(Contact.id)
            .all()
        )
        return [r[0] for r in rows]
