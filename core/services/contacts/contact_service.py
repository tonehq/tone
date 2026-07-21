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
from core.services.contact_ingestion.base import ParsedContact
from core.services.contact_ingestion.pipeline import RecordParser, parsed_contact_to_row
from core.services.contact_ingestion.validation import (
    CompositeValidator,
    RequiredIdentityValidator,
    SchemaMetadataValidator,
)
from core.services.contacts.contact_metadata_validation import (
    make_contact_metadata_validator,
    normalize_contact_metadata_dates,
    validate_contact_metadata,
)
from core.services.contacts.contact_upsert import upsert_contact


class ContactService(BaseService):
    """Directory-scoped CRUD for ``Contact`` rows."""

    # --------------------------------------------------------------- directory

    def _get_directory(self, directory_id: UUID) -> ContactDirectory:
        """Fetch an org-owned directory or 404 (shared IDOR guard for every
        directory-scoped operation)."""
        return self.get_or_404(ContactDirectory, directory_id, name="Directory")

    def _schema_fields(self, directory: ContactDirectory) -> List[SchemaField]:
        """The directory's default-schema ACTIVE, non-deleted fields (``[]`` if no default
        schema). The single source both the framework validator and ``_metadata_validator``
        build from."""
        if not directory.default_schema_id:
            return []
        return (
            self.query(SchemaField)
            .filter(
                SchemaField.schema_id == directory.default_schema_id,
                SchemaField.deleted_at.is_(None),
                SchemaField.is_active.is_(True),
            )
            .all()
        )

    def _metadata_validator(self, directory: ContactDirectory):
        """Build the ``(managed_keys, validator)`` pair from the directory's default schema,
        or ``(set(), None)`` when there is none (so contacts still work before any schema is
        attached). Used by ``update_contact``."""
        return make_contact_metadata_validator(self._schema_fields(directory))

    @staticmethod
    def _row_to_parsed(row: Dict[str, Any]) -> ParsedContact:
        """Convert a Contact-Create API row into the common :class:`ParsedContact` model —
        the same model every data source produces — so the API can be fed straight into the
        shared validate/loop (skipping the parse step). Synthesizes a stable ``external_id``
        (explicit → phone → ``manual-<uuid>``) exactly as before."""
        name = (row.get("name") or "").strip() or None
        phone_number = (row.get("phone_number") or "").strip() or None
        external_id = (row.get("external_id") or "").strip() or (phone_number or "") or f"manual-{uuid4().hex[:16]}"
        return ParsedContact(
            external_id=external_id,
            name=name,
            phone_number=phone_number,
            metadata=row.get("contact_metadata") or {},
        )

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

        The Contact-Create API SKIPS the parse step (its rows are already structured) but
        runs them through the SAME loop + validators as file-upload / sync flows: convert
        each row to the common ``ParsedContact`` model, run the shared ``RecordParser`` loop
        with a ``CompositeValidator`` (identity + the directory's schema), then upsert the
        valid records. No per-request row cap — imports are unbounded.
        """
        directory = self._get_directory(directory_id)
        if not rows:
            raise HTTPException(status_code=400, detail="Provide at least one contact.")

        schema_fields = self._schema_fields(directory)

        # Normalize date/datetime metadata to a UTC ISO string up-front (same stored shape as
        # the sync path). A row with an unparseable date is collected as failed and never
        # created; the rest flow through the shared validate/loop below. `prepared` keeps each
        # kept row's ORIGINAL index so pipeline errors map back to the caller's row numbers.
        failed: List[Dict[str, Any]] = []
        prepared: List[Any] = []
        for i, row in enumerate(rows):
            metadata, date_errors = normalize_contact_metadata_dates(
                row.get("contact_metadata"), schema_fields
            )
            if date_errors:
                failed.append({"index": i, "errors": date_errors})
                continue
            prepared.append((i, {**row, "contact_metadata": metadata}))

        # Same validate/loop as every other data source — the ONLY difference is Parse is
        # skipped here (the API hands us structured records, not a raw blob).
        validator = CompositeValidator(
            [RequiredIdentityValidator(), SchemaMetadataValidator(schema_fields)]
        )
        parsed = RecordParser(validator).process(
            self._row_to_parsed(row) for _i, row in prepared
        )

        # Pipeline indices are positions within `prepared`; map them back to original rows.
        for bad in parsed.invalid:
            failed.append({"index": prepared[bad["index"]][0], "errors": bad["errors"]})
        failed.sort(key=lambda f: f["index"])

        created_by_ext: Dict[str, Contact] = {}
        for record in parsed.valid:
            contact, _action = upsert_contact(
                self.db,
                directory_id,
                parsed_contact_to_row(record),
                organization_id=self.org_id,
                created_by_user_id=self.user_id,
            )
            created_by_ext[record.external_id] = contact

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
            schema_fields = self._schema_fields(directory)
            managed, validator = make_contact_metadata_validator(schema_fields)
            # Normalize date/datetime fields to a UTC ISO string (same stored shape as the
            # CSV sync path). Manual entry sends an ISO instant from the DateTimePicker; an
            # unparseable value is rejected here rather than silently dropped.
            contact_metadata, date_errors = normalize_contact_metadata_dates(
                contact_metadata, schema_fields
            )
            errors = date_errors + validate_contact_metadata(contact_metadata, managed, validator)
            if errors:
                raise HTTPException(status_code=400, detail="; ".join(errors))
            # The edit form only submits keys managed by the directory's default schema, so
            # replacing the whole column would silently wipe metadata owned by another
            # schema or by since-removed fields. Preserve existing UNMANAGED keys and overlay
            # the submitted (managed) ones — a managed key omitted from the payload is still
            # cleared, so editing/clearing a schema field keeps working.
            existing = contact.contact_metadata or {}
            preserved = {k: v for k, v in existing.items() if k not in managed}
            contact.contact_metadata = {**preserved, **contact_metadata}
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
