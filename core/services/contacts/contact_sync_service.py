"""ContactSyncService — the datasource-driven import pipeline into a directory.

A ``ContactSync`` is one run of: resolve the directory's CSV datasource → store the
uploaded file in R2 (as an ``Upload`` row, ``purpose="contact_import"``) → insert a
pending ``ContactSync`` → enqueue a Procrastinate job. The worker then executes
``run_contact_sync``:

    load sync → mark processing → get source → per row: map + validate
      → valid rows upsert (partial success; invalid rows collected in ``row_errors`` and
        SKIPPED) → optional agent auto-assign → write counts + status.

Everything is org-scoped via ``BaseService.query`` (no IDOR). The run is **idempotent**
on redelivery: ``upsert_contact`` keys on ``(directory_id, external_id)`` and a completed
sync short-circuits, so a re-delivered job converges to the same result rather than
duplicating contacts.

Reuse map: ``select_source_for_upload`` (uploaded blob → CSV/``.xlsx`` parser by magic
bytes) / ``get_contact_source`` (datasource → parser), ``map_source_row_to_contact``
(schema mapping), ``make_contact_metadata_validator`` / ``validate_contact_metadata``
(per-row validation), ``upsert_contact`` (the single directory-scoped write-site),
``ContactDatasourceService.ensure_csv_datasource`` (pinned), ``AgentContactService.
assign_contacts_to_agent`` (pinned auto-assign).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from loguru import logger

from core.models.contact_directory import ContactDirectory
from core.models.contact_sync import ContactSync
from core.models.datasource import Datasource
from core.models.schema_field import SchemaField
from core.models.upload import Upload
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.contact_ingestion import get_contact_source, select_source_for_upload
from core.services.contact_ingestion.contact_mapping import map_source_row_to_contact
from core.services.contacts.contact_metadata_validation import (
    make_contact_metadata_validator,
    validate_contact_metadata,
)
from core.services.contacts.contact_upsert import upsert_contact
from core.services.r2_storage_service import R2StorageService
from shared.config import settings

_LOG_TAG = "[contact-sync]"


class ContactSyncService(BaseService):
    """Create and run datasource-driven contact syncs into a directory."""

    # Cap a single sync so one huge file can't create unbounded rows in one job.
    MAX_SYNC_ROWS = 50_000

    # ------------------------------------------------------------------ create

    def create_contact_sync(
        self,
        directory_id: UUID,
        schema_id: UUID,
        agent_id: Optional[UUID] = None,
        file=None,
    ) -> ContactSync:
        """Resolve the directory's CSV datasource, store the upload, insert a pending
        ``ContactSync`` and enqueue its Procrastinate job.

        Args:
            directory_id: the org-owned directory to import into.
            schema_id: the org-level ``ContactSchema`` whose fields drive the mapping.
            agent_id: optional agent to auto-assign the imported contacts to on success.
            file: a ``fastapi.UploadFile``-like object (``.file``, ``.filename``,
                ``.content_type``) carrying the CSV to import.

        The upload is stored in R2 with its own ``Upload`` row; on any failure after the
        blob lands, the orphan blob is best-effort deleted so R2 is not littered.
        """
        directory = self.get_or_404(ContactDirectory, directory_id, name="Directory")
        # Validate the schema is an org-owned, live schema (no IDOR / dangling ref).
        from core.models.contact_schema import ContactSchema

        self.get_or_404(ContactSchema, schema_id, name="Schema")
        if agent_id is not None:
            from core.models.agent import Agent

            self.get_or_404(Agent, agent_id, name="Agent")

        # Resolve (or lazily create) the directory's CSV datasource via the pinned
        # ContactDatasourceService interface.
        from core.services.contacts.contact_datasource_service import ContactDatasourceService

        datasource = ContactDatasourceService(
            self.db, user_id=self.user_id, org_id=self.org_id
        ).ensure_csv_datasource(directory_id)

        upload = self._store_contact_upload(file) if file is not None else None

        try:
            sync = ContactSync(
                organization_id=self.org_id,
                directory_id=directory.id,
                datasource_id=datasource.id,
                schema_id=schema_id,
                upload_id=upload.id if upload is not None else None,
                agent_id=agent_id,
                status="pending",
                counts={},
                row_errors=[],
                created_by_user_id=self.user_id,
            )
            self.db.add(sync)
            self.db.commit()
            self.db.refresh(sync)
        except Exception:
            logger.exception(
                f"{_LOG_TAG} failed to create sync directory_id={directory_id}"
            )
            self.db.rollback()
            raise

        from core.services.ingestion_queue import enqueue_contact_sync_sync

        try:
            enqueue_contact_sync_sync(sync.id, self.org_id)
        except Exception:
            logger.exception(
                f"{_LOG_TAG} failed to enqueue sync sync_id={sync.id}; marking failed"
            )
            sync.status = "failed"
            sync.error = "Failed to enqueue import job."
            self.db.commit()
            raise

        logger.info(
            f"{_LOG_TAG} created sync_id={sync.id} directory_id={directory_id} "
            f"schema_id={schema_id} agent_id={agent_id} upload_id="
            f"{upload.id if upload else None}"
        )
        return sync

    def _store_contact_upload(self, file) -> Upload:
        """Stream an uploaded CSV to R2 and create its ``Upload`` row.

        Stored under a ``contacts/`` prefix and tagged ``purpose="contact_import"``.
        Implemented here (not on the deleted ``ContactService.create_upload``) so the
        sync flow owns its file storage. On a DB failure after the blob lands, the orphan
        blob is best-effort deleted.
        """
        fileobj = file.file
        fileobj.seek(0, 2)
        size_bytes = fileobj.tell()
        fileobj.seek(0)
        if not size_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        file_name = getattr(file, "filename", None) or "contacts.csv"
        content_type = getattr(file, "content_type", None) or "text/csv"

        org_id = self.org_id
        object_key = f"contacts/{org_id}/{uuid4()}/{file_name}"
        r2 = R2StorageService()
        r2.upload_fileobj(fileobj, object_key, content_type=content_type)

        try:
            upload = Upload(
                organization_id=org_id,
                container_name=settings.R2_BUCKET_NAME,
                file_path=object_key,
                file_name=file_name,
                file_type=content_type,
                size_bytes=size_bytes,
                purpose="contact_import",
                status="ready",
                meta_data={},
                created_by_user_id=self.user_id,
                is_active=True,
            )
            self.db.add(upload)
            self.db.commit()
            self.db.refresh(upload)
            return upload
        except Exception:
            logger.exception(
                f"{_LOG_TAG} upload DB write failed; cleaning up R2 blob key={object_key}"
            )
            self.db.rollback()
            try:
                r2.delete_file(object_key)
            except Exception:
                logger.exception(
                    f"{_LOG_TAG} best-effort R2 cleanup failed key={object_key}"
                )
            raise

    # --------------------------------------------------------------------- run

    def run_contact_sync(self, sync: ContactSync) -> ContactSync:
        """Execute a sync: source → per-row map+validate → upsert valid rows → optional
        auto-assign → write counts + status.

        Partial success: invalid rows are collected into ``row_errors`` and skipped; the
        run still completes (status ``completed``). Hard failures (missing datasource,
        unreadable file, all-rows-invalid) set status ``failed`` with ``error`` and import
        nothing. Idempotent — a run already in a terminal state is a no-op on redelivery.

        C-3: inside the run, the directory is re-checked (still exists / not soft-deleted)
        before upserting; if it was hard-deleted mid-run the sync aborts cleanly as
        ``failed`` (error="directory deleted") without upserting against the RESTRICT FK.
        """
        # Redelivery / already-run guard: never re-import a terminal sync.
        if sync.status in ("completed", "failed"):
            logger.info(
                f"{_LOG_TAG} sync_id={sync.id} already {sync.status}; skipping re-run"
            )
            return sync

        sync.status = "processing"
        self.db.commit()
        logger.info(f"{_LOG_TAG} sync_id={sync.id} processing")

        # C-3: re-check the directory still exists (not soft-deleted / torn down) before
        # doing any work. If it was hard-deleted mid-run, abort cleanly without upserting.
        directory = None
        if sync.directory_id is not None:
            directory = (
                self.query(ContactDirectory)
                .filter(
                    ContactDirectory.id == sync.directory_id,
                    ContactDirectory.deleted_at.is_(None),
                )
                .first()
            )
        if directory is None:
            logger.warning(
                f"{_LOG_TAG} sync_id={sync.id} directory gone mid-run; aborting"
            )
            return self._fail(sync, "directory deleted")

        try:
            datasource, schema_fields, blob = self._load_run_inputs(sync)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"{_LOG_TAG} sync_id={sync.id} failed loading inputs")
            return self._fail(sync, str(exc)[:500])

        created = 0
        updated = 0
        skipped = 0
        failed = 0
        row_errors: List[Dict[str, Any]] = []
        imported_contact_ids: List[UUID] = []
        parsed_any = False

        try:
            managed, validator = make_contact_metadata_validator(schema_fields)
            source = self._resolve_source(datasource, blob)
            for i, parsed in enumerate(source.parse(blob)):
                parsed_any = True
                if i >= self.MAX_SYNC_ROWS:
                    row_errors.append(
                        {"row": i, "field": None, "message": f"Import truncated at {self.MAX_SYNC_ROWS} rows."}
                    )
                    logger.warning(
                        f"{_LOG_TAG} sync_id={sync.id} truncated at {self.MAX_SYNC_ROWS} rows"
                    )
                    break

                raw = self._parsed_to_raw(parsed)
                mapped = map_source_row_to_contact(raw, schema_fields) if schema_fields else self._identity_map(parsed)

                # The schema maps metadata (and MAY override name/phone/external_id); the
                # base contact identity always comes from the parsed source row. Backfill
                # anything the schema didn't explicitly map, so a schema that only defines
                # extra fields (e.g. city) never drops the synthesized external_id/name/phone.
                mapped["external_id"] = mapped.get("external_id") or parsed.external_id
                mapped["name"] = mapped.get("name") or parsed.name
                mapped["phone_number"] = mapped.get("phone_number") or parsed.phone_number

                # The per-row schedule override lives in parsed metadata, but
                # map_source_row_to_contact keeps only schema-mapped keys — so carry
                # scheduled_at over explicitly (the outbound dialer reads
                # contact_metadata["scheduled_at"]). A schema-mapped value wins.
                parsed_scheduled_at = (parsed.metadata or {}).get("scheduled_at")
                if parsed_scheduled_at:
                    meta = mapped.setdefault("contact_metadata", {})
                    meta.setdefault("scheduled_at", parsed_scheduled_at)

                # Each error entry carries the row's identity (name/phone) so the report
                # shows WHICH contact failed, not just a row number.
                def _err(field, message):
                    return {
                        "row": i,
                        "field": field,
                        "message": message,
                        "name": mapped.get("name"),
                        "phone_number": mapped.get("phone_number"),
                    }

                if not mapped.get("external_id"):
                    skipped += 1
                    row_errors.append(_err("external_id", "Row has no resolvable external_id."))
                    continue

                errors = validate_contact_metadata(mapped.get("contact_metadata"), managed, validator)
                if errors:
                    # A row that fails metadata validation is a genuine failure (distinct from
                    # `skipped`, which is a structural no-op like an unresolvable external_id).
                    failed += 1
                    for msg in errors:
                        row_errors.append(_err(None, msg))
                    continue

                contact, action = upsert_contact(
                    self.db,
                    sync.directory_id,
                    mapped,
                    organization_id=self.org_id,
                    sync_id=sync.id,
                    created_by_user_id=sync.created_by_user_id,
                )
                self.db.flush()
                imported_contact_ids.append(contact.id)
                if action == "created":
                    created += 1
                else:
                    updated += 1

            self.db.commit()
        except Exception as exc:
            logger.exception(f"{_LOG_TAG} sync_id={sync.id} parse/upsert failed")
            self.db.rollback()
            return self._fail(sync, str(exc)[:500])

        # A file that parsed to zero usable rows (all invalid, or empty) is a hard failure.
        if created == 0 and updated == 0:
            reason = (
                "All rows failed validation." if (parsed_any or row_errors)
                else "No importable rows found in the file."
            )
            failed_sync = self._fail(sync, reason)
            failed_sync.counts = {"created": 0, "updated": 0, "skipped": skipped, "failed": failed}
            failed_sync.row_errors = row_errors
            self.db.commit()
            logger.info(
                f"{_LOG_TAG} sync_id={sync.id} failed (no rows imported) failed={failed}"
            )
            return failed_sync

        # Optional auto-assign of the imported contacts to an agent (idempotent).
        if sync.agent_id is not None and imported_contact_ids:
            try:
                from core.services.contacts.agent_contact_service import AgentContactService

                AgentContactService(
                    self.db, user_id=self.user_id, org_id=self.org_id
                ).assign_contacts_to_agent(sync.agent_id, contact_ids=imported_contact_ids)
            except Exception:
                logger.exception(
                    f"{_LOG_TAG} sync_id={sync.id} auto-assign to agent_id="
                    f"{sync.agent_id} failed"
                )
                # Auto-assign is a best-effort side effect; the import itself succeeded, so
                # don't roll the whole sync back — surface it and continue to completed.

        sync.status = "completed"
        sync.counts = {"created": created, "updated": updated, "skipped": skipped, "failed": failed}
        sync.row_errors = row_errors
        sync.error = None
        self.db.commit()
        self.db.refresh(sync)
        logger.info(
            f"{_LOG_TAG} sync_id={sync.id} completed counts={sync.counts} "
            f"assigned={len(imported_contact_ids) if sync.agent_id else 0}"
        )
        return sync

    # ---------------------------------------------------------------- run helpers

    def _load_run_inputs(self, sync: ContactSync):
        """Resolve the datasource, active schema fields, and downloaded file blob for a
        sync. Raises on a hard failure so ``run_contact_sync`` can mark it ``failed``."""
        if sync.datasource_id is None:
            raise ValueError("Sync has no datasource.")
        datasource = (
            self.query(Datasource)
            .filter(Datasource.id == sync.datasource_id)
            .first()
        )
        if datasource is None:
            raise ValueError("Datasource not found.")

        schema_fields = (
            self.query(SchemaField)
            .filter(
                SchemaField.schema_id == sync.schema_id,
                SchemaField.deleted_at.is_(None),
                SchemaField.is_active.is_(True),
            )
            .all()
        )

        if sync.upload_id is None:
            raise ValueError("Sync has no uploaded file.")
        upload = (
            self.query(Upload).filter(Upload.id == sync.upload_id).first()
        )
        if upload is None or not upload.file_path:
            raise ValueError("Sync upload not found.")
        blob = R2StorageService().download_file(upload.file_path)
        return datasource, schema_fields, blob

    @staticmethod
    def _resolve_source(datasource, blob: bytes):
        """Pick the parser for a sync's blob.

        Uploaded-file datasources (``csv`` type) sniff the blob's magic bytes so a user can
        upload a real CSV **or** an ``.xlsx`` interchangeably (and legacy ``.xls`` fails with
        a friendly message). Non-upload datasource types (``rest``, …) keep dispatching on
        ``datasource.type`` via ``get_contact_source``.
        """
        ds_type = (getattr(datasource, "type", None) or "csv").strip().lower()
        if ds_type == "csv":
            return select_source_for_upload(blob)
        return get_contact_source(datasource)

    @staticmethod
    def _parsed_to_raw(parsed) -> Dict[str, Any]:
        """Flatten a ``ParsedContact`` into a raw ``header -> value`` dict for the schema
        mapper (reserved fields promoted, metadata columns merged)."""
        raw: Dict[str, Any] = dict(parsed.metadata or {})
        if parsed.name is not None:
            raw["name"] = parsed.name
        if parsed.phone_number is not None:
            raw["phone_number"] = parsed.phone_number
        if parsed.external_id is not None:
            raw["external_id"] = parsed.external_id
        return raw

    @staticmethod
    def _identity_map(parsed) -> Dict[str, Any]:
        """Fallback mapping when the schema has no fields — take the source as-is."""
        return {
            "name": parsed.name,
            "phone_number": parsed.phone_number,
            "external_id": parsed.external_id,
            "contact_metadata": dict(parsed.metadata or {}),
        }

    def _fail(self, sync: ContactSync, error: str) -> ContactSync:
        """Mark a sync ``failed`` with an error message and commit."""
        sync.status = "failed"
        sync.error = error
        self.db.commit()
        self.db.refresh(sync)
        return sync

    # -------------------------------------------------------------------- read

    def get_contact_sync(self, sync_id: UUID) -> ContactSync:
        """Fetch an org-owned sync or 404."""
        sync = self.query(ContactSync).filter(ContactSync.id == sync_id).first()
        if sync is None:
            raise HTTPException(status_code=404, detail="Contact sync not found.")
        return sync

    def list_contact_syncs(
        self,
        *,
        directory_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page_no: int = 1,
        page_size: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """List org syncs (optionally scoped to one directory and/or status), paginated."""
        query = self.query(ContactSync)
        if directory_id is not None:
            query = query.filter(ContactSync.directory_id == directory_id)
        if status:
            query = query.filter(ContactSync.status == status)
        rows, total = apply_search_sort_pagination(
            query,
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "created_at": ContactSync.created_at,
                "updated_at": ContactSync.updated_at,
                "status": ContactSync.status,
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

