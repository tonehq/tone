"""Org-level contact-schema + field CRUD (``ContactSchemaService``).

Replaces the old flat ``ContactFieldDefinitionService``. A ``ContactSchema`` is an
ORG-LEVEL, reusable contact-shape template that owns a set of ``SchemaField`` rows; it
carries no ``directory_id`` — a directory *references* one via
``contact_directories.default_schema_id`` and a sync may pick any org schema. This
service therefore serves both directories and syncs from one place.

Guards live on the router (writes = admin/owner, reads = member); every method is
org-scoped through ``BaseService.query`` (no IDOR). Field validation reuses the shared
``contact_metadata_validation`` helpers rather than duplicating any JSON-Schema logic.

Reference-safety rules (edit/delete of a shared schema):
- On edit/delete we surface a ``referenced_by`` count (directories whose
  ``default_schema_id`` points here + syncs whose ``schema_id`` points here) so callers
  can warn the user that the change is shared.
- Deleting a schema that is any directory's ``default_schema_id`` is BLOCKED (409) — the
  caller must repoint those directories first, so we never leave a dangling default.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from loguru import logger

from core.models.contact_directory import ContactDirectory
from core.models.contact_schema import ContactSchema
from core.models.contact_sync import ContactSync
from core.models.schema_field import SchemaField
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination
from core.services.contacts.contact_metadata_validation import (
    build_contact_field_json_schema,
)

# Field ``type`` values we accept — anything else is rejected up front so a malformed
# JSON Schema can never be composed.
_ALLOWED_FIELD_TYPES = {"string", "number", "integer", "boolean", "enum"}
# Validator keys accepted per underlying primitive (mirrors contact_metadata_validation).
_STRING_VALIDATORS = {"minLength", "maxLength", "pattern"}
_NUMBER_VALIDATORS = {"minimum", "maximum"}


class ContactSchemaService(BaseService):
    """CRUD for org-level ``ContactSchema`` templates and their ``SchemaField`` rows."""

    # --------------------------------------------------------------- schema CRUD

    def create_schema(
        self,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> ContactSchema:
        """Create an empty org-level schema. Fields are added via ``create_schema_field``."""
        clean = (name or "").strip()
        if not clean:
            raise HTTPException(status_code=400, detail="Schema name is required.")
        schema = ContactSchema(
            organization_id=self.org_id,
            name=clean,
            description=(description or None),
            is_active=is_active,
            created_by_user_id=self.user_id,
        )
        self.db.add(schema)
        self.db.commit()
        self.db.refresh(schema)
        logger.info("[contact-schema] created schema id={} name={}", schema.id, clean)
        return schema

    def list_schemas(
        self,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Paginated list of the org's active (non-soft-deleted) schemas."""
        q = self.query(ContactSchema).filter(ContactSchema.deleted_at.is_(None))
        rows, total = apply_search_sort_pagination(
            q,
            search=search,
            search_fields=[ContactSchema.name, ContactSchema.description],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "name": ContactSchema.name,
                "created_at": ContactSchema.created_at,
                "updated_at": ContactSchema.updated_at,
            },
            page_no=page_no,
            page_size=page_size,
        )
        return {
            "data": [s.to_dict() for s in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def get_schema(self, schema_id) -> ContactSchema:
        """Fetch one org-scoped schema or 404."""
        return self.get_or_404(ContactSchema, schema_id, name="Schema")

    def get_schema_detail(self, schema_id) -> Dict[str, Any]:
        """Schema dict enriched with its active fields and a ``referenced_by`` count."""
        schema = self.get_schema(schema_id)
        data = schema.to_dict()
        data["fields"] = [f.to_dict() for f in self._active_fields(schema_id)]
        data["referenced_by"] = self._referenced_by(schema_id)
        return data

    def update_schema(
        self,
        schema_id,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update schema attributes. Returns the schema dict plus ``referenced_by`` so
        the caller can warn that the edit is shared across N directories/syncs."""
        schema = self.get_schema(schema_id)
        if name is not None:
            clean = name.strip()
            if not clean:
                raise HTTPException(status_code=400, detail="Schema name is required.")
            schema.name = clean
        if description is not None:
            schema.description = description or None
        if is_active is not None:
            schema.is_active = is_active
        self.db.commit()
        self.db.refresh(schema)
        referenced_by = self._referenced_by(schema_id)
        logger.info(
            "[contact-schema] updated schema id={} referenced_by={}",
            schema_id,
            referenced_by,
        )
        out = schema.to_dict()
        out["referenced_by"] = referenced_by
        return out

    def delete_schema(self, schema_id) -> Dict[str, Any]:
        """Soft-delete a schema (and its fields). Blocked (409) while any directory uses
        it as ``default_schema_id`` — the caller must repoint those first so we never
        leave a dangling default."""
        schema = self.get_schema(schema_id)
        referenced_by = self._referenced_by(schema_id)
        if referenced_by["directories"] > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Schema is the default for {referenced_by['directories']} "
                    "directory(ies). Repoint them to another schema before deleting."
                ),
            )
        now = datetime.now(timezone.utc)
        schema.deleted_at = now
        schema.is_active = False
        # Soft-delete the schema's fields too so a re-created schema starts clean.
        self.query(SchemaField).filter(
            SchemaField.schema_id == schema_id,
            SchemaField.deleted_at.is_(None),
        ).update(
            {SchemaField.deleted_at: now, SchemaField.is_active: False},
            synchronize_session=False,
        )
        self.db.commit()
        logger.info(
            "[contact-schema] deleted schema id={} referenced_by_syncs={}",
            schema_id,
            referenced_by["syncs"],
        )
        return {"ok": True, "referenced_by": referenced_by}

    # ---------------------------------------------------------------- field CRUD

    def create_schema_field(
        self,
        schema_id,
        field_name: str,
        type: str = "string",
        label: Optional[str] = None,
        format: Optional[str] = None,
        is_mandatory: bool = False,
        validators: Optional[Dict[str, Any]] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        source_key: Optional[str] = None,
        display_order: int = 0,
        field_metadata: Optional[Dict[str, Any]] = None,
    ) -> SchemaField:
        """Add a field to a schema. Validates type/validator/enum guardrails, then
        composes the JSON Schema once to prove the field is well-formed before commit.

        The ``(schema_id, field_name)`` unique constraint counts soft-deleted rows, so a
        previously removed field name is REVIVED (re-activated + overwritten) rather than
        raising a constraint violation.
        """
        schema = self.get_schema(schema_id)  # org-scope + existence check
        name = (field_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="field_name is required.")
        self._validate_field_shape(type, validators, options)

        existing = (
            self.db.query(SchemaField)
            .filter(SchemaField.schema_id == schema.id, SchemaField.field_name == name)
            .first()
        )
        if existing is not None and existing.deleted_at is None:
            raise HTTPException(
                status_code=409,
                detail=f"Field '{name}' already exists in this schema.",
            )

        target = existing if existing is not None else SchemaField(
            organization_id=self.org_id,
            schema_id=schema.id,
            field_name=name,
        )
        target.type = type
        target.label = label
        target.format = format
        target.is_mandatory = is_mandatory
        target.validators = validators or {}
        target.options = options
        target.source_key = source_key
        target.display_order = display_order
        target.field_metadata = field_metadata or {}
        target.is_active = True
        target.deleted_at = None
        if existing is None:
            self.db.add(target)

        # Compose the full schema once — surfaces any JSON-Schema issue before commit.
        self._assert_composes(schema.id, replacement=target)
        self.db.commit()
        self.db.refresh(target)
        logger.info(
            "[contact-schema] created field schema_id={} field={} type={}",
            schema.id,
            name,
            type,
        )
        return target

    def update_schema_field(self, field_id, **changes: Any) -> SchemaField:
        """Update a field's attributes. Re-validates the resulting type/validator/enum
        combination and re-composes the schema before committing."""
        field = self.get_or_404(SchemaField, field_id, name="Field")
        # Resolve the post-update shape for validation.
        new_type = changes.get("type", field.type)
        new_validators = changes.get("validators", field.validators)
        new_options = changes.get("options", field.options)
        self._validate_field_shape(new_type, new_validators, new_options)

        allowed = {
            "label",
            "type",
            "format",
            "is_mandatory",
            "validators",
            "options",
            "source_key",
            "display_order",
            "is_active",
            "field_metadata",
        }
        for key, value in changes.items():
            if key in allowed:
                setattr(field, key, value)
        if changes.get("is_active") is True:
            field.deleted_at = None

        self._assert_composes(field.schema_id, replacement=field)
        self.db.commit()
        self.db.refresh(field)
        logger.info("[contact-schema] updated field id={}", field_id)
        return field

    # ----------------------------------------------------------- sample files

    # Base dial columns always present in a sample import file.
    _SAMPLE_BASE_COLUMNS = ("name", "phone_number")

    def _active_fields(self, schema_id) -> List[SchemaField]:
        """The schema's ACTIVE, non-deleted fields (org-scoped, ordered) — the ONE loader
        reused by the sample builder and the schedule-column resolver."""
        schema = self.get_schema(schema_id)  # org-scope + 404
        return (
            self.query(SchemaField)
            .filter(
                SchemaField.schema_id == schema.id,
                SchemaField.deleted_at.is_(None),
                SchemaField.is_active.is_(True),
            )
            .order_by(SchemaField.display_order.asc())
            .all()
        )

    def apply_scheduled_at_from_column(
        self, records, schema_id, column
    ) -> List[Tuple[Any, str]]:
        """Set each record's ``metadata['scheduled_at']`` from the named source ``column``
        (the per-row call time in an uploaded file), parsed with the matching schema field's
        date/datetime FORMAT and TIMEZONE (field tz → org scheduling tz → UTC), so the
        schedule column and the stored metadata resolve to the SAME instant. Mutates the
        usable ``records`` in place.

        Returns a list of ``(record, reason)`` for rows whose cell was PRESENT but unusable —
        unparseable, or a time in the past — so the file scheduler drops them to ``invalid``
        instead of dialing them (rather than the generic "past → dial ASAP" fallback). An
        EMPTY cell (or a blank ``column``) is left untouched: that row falls back to the
        request-level schedule time. The outbound scheduler reads ``metadata['scheduled_at']``.
        """
        from core.services.contact_ingestion.row_mapping import parse_datetime_value

        col = (column or "").strip().lower()
        if not col:
            return []

        # FORMAT comes from the schema field mapped to this column (matched by source_key or
        # field_name) so a non-ISO format like DD/MM/YYYY parses. TIMEZONE is the field's own
        # source tz when set, else the org's default scheduling tz, else UTC — keeping the
        # schedule column consistent with how that same field is stored as contact metadata.
        fmt = field_tz = None
        if schema_id:
            for field in self._active_fields(schema_id):
                names = {
                    (field.source_key or "").strip().lower(),
                    (field.field_name or "").strip().lower(),
                }
                if col in names and getattr(field, "format", None) in ("date", "datetime"):
                    cfg = getattr(field, "field_metadata", None) or {}
                    fmt = cfg.get("datetime_format")
                    field_tz = cfg.get("timezone")
                    break
        tz = field_tz or self._org_scheduling_timezone()

        now = datetime.now(timezone.utc)
        errors: List[Tuple[Any, str]] = []
        for record in records:
            raw_val = (record.metadata or {}).get(col)
            if raw_val is None or not str(raw_val).strip():
                continue  # empty cell → fall back to the request-level schedule time
            iso = parse_datetime_value(str(raw_val), fmt=fmt, tz=tz)
            if not iso:
                errors.append(
                    (record, f"Unparseable schedule time '{raw_val}' in column '{col}'.")
                )
                continue
            # Allow a 60s grace so a just-now time isn't rejected as "past".
            if datetime.fromisoformat(iso) <= now - timedelta(seconds=60):
                errors.append((record, f"Scheduled time '{raw_val}' is in the past."))
                continue
            record.metadata["scheduled_at"] = iso
        return errors

    def _org_scheduling_timezone(self) -> str:
        """The org's default scheduling timezone (IANA), via the single ``org_settings``
        resolver — the fallback source tz for a schedule column whose schema field carries
        no timezone of its own."""
        from core.models.organization import Organization
        from core.services.org_settings import get_scheduling_timezone

        org = (
            self.db.query(Organization)
            .filter(Organization.id == self.org_id)
            .first()
        )
        return get_scheduling_timezone(org.settings if org else None)

    def build_sample_file(self, schema_id, fmt: str = "csv") -> Tuple[str, str, bytes]:
        """Generate a schema-shaped sample import file SERVER-SIDE (CSV or ``.xlsx``).

        Columns = the base dial columns + each active field's external ``source_key`` (or
        ``field_name``), with mandatory columns marked with a trailing ``*``; one example
        row illustrates the expected shape. The example content (incl. any placeholder
        values) is produced here, not in the client. Returns
        ``(filename, media_type, content_bytes)``.
        """
        schema = self.get_schema(schema_id)
        headers, example = self._sample_columns(self._active_fields(schema_id))
        # Collapse whitespace to '-', then drop any char outside [a-z0-9-] so an odd schema
        # name (e.g. containing a double-quote) can't corrupt the quoted Content-Disposition
        # filename parameter.
        slug = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", (schema.name or "schema").strip()).lower()) or "schema"
        if (fmt or "csv").lower() == "xlsx":
            return (
                f"sample-{slug}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                self._sample_xlsx_bytes(headers, example),
            )
        return f"sample-{slug}.csv", "text/csv; charset=utf-8", self._sample_csv_bytes(headers, example)

    # A fixed sample instant so example date/time cells are deterministic.
    _SAMPLE_INSTANT = datetime(2026, 1, 31, 14, 30, 0)

    @classmethod
    def _sample_columns(cls, fields) -> Tuple[List[str], List[str]]:
        """Header row + one example row for a schema's sample file (shared by CSV/xlsx).

        Date/time fields render an example value in the field's CONFIGURED format (the
        strptime string in ``field_metadata.datetime_format``, or ISO when none) so the
        sample shows exactly the shape the importer expects."""
        headers: List[str] = list(cls._SAMPLE_BASE_COLUMNS)
        seen = set(cls._SAMPLE_BASE_COLUMNS)
        field_by_col: Dict[str, Any] = {}
        for f in fields:
            key = (f.source_key or f.field_name or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            headers.append(f"{key}*" if f.is_mandatory else key)
            field_by_col[key] = f
        example: List[str] = []
        for h in headers:
            col = h.rstrip("*")
            if col == "name":
                example.append("John Doe")
            elif col == "phone_number":
                example.append("+14155550123")
            else:
                example.append(cls._sample_value_for_field(field_by_col.get(col)))
        return headers, example

    @classmethod
    def _sample_value_for_field(cls, field) -> str:
        """Example cell value for a schema field. A date/datetime field renders the fixed
        sample instant in its configured format (``field_metadata.datetime_format``) — or
        ISO when unset; every other field is left blank."""
        fmt_kind = getattr(field, "format", None) if field is not None else None
        if fmt_kind not in ("date", "datetime"):
            return ""
        meta = (getattr(field, "field_metadata", None) or {}) if field is not None else {}
        strptime_fmt = meta.get("datetime_format")
        if strptime_fmt:
            try:
                return cls._SAMPLE_INSTANT.strftime(strptime_fmt)
            except (ValueError, TypeError):
                pass
        # No configured format → ISO (date-only for `date`, full for `datetime`).
        return (
            cls._SAMPLE_INSTANT.date().isoformat()
            if fmt_kind == "date"
            else cls._SAMPLE_INSTANT.isoformat()
        )

    @staticmethod
    def _sample_csv_bytes(headers: List[str], example: List[str]) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerow(example)
        return buf.getvalue().encode("utf-8")

    @staticmethod
    def _sample_xlsx_bytes(headers: List[str], example: List[str]) -> bytes:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Contacts"
        ws.append(headers)
        ws.append(example)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def delete_schema_field(self, field_id) -> Dict[str, Any]:
        """Soft-delete (disable) a field. Existing contacts keep their metadata and are
        NOT retro-validated; the field simply stops being enforced going forward."""
        field = self.get_or_404(SchemaField, field_id, name="Field")
        field.deleted_at = datetime.now(timezone.utc)
        field.is_active = False
        self.db.commit()
        logger.info(
            "[contact-schema] deleted field id={} schema_id={}", field_id, field.schema_id
        )
        return {"ok": True}

    # ------------------------------------------------------------------ helpers

    def _referenced_by(self, schema_id) -> Dict[str, int]:
        """Count how many directories default to this schema and how many syncs use it."""
        directories = (
            self.query(ContactDirectory)
            .filter(
                ContactDirectory.default_schema_id == schema_id,
                ContactDirectory.deleted_at.is_(None),
            )
            .count()
        )
        syncs = (
            self.query(ContactSync).filter(ContactSync.schema_id == schema_id).count()
        )
        return {"directories": int(directories), "syncs": int(syncs)}

    def _validate_field_shape(
        self,
        type: str,
        validators: Optional[Dict[str, Any]],
        options: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Reject bad ``type``, validators illegal for the type, or an enum without
        options — before anything is composed or written."""
        if type not in _ALLOWED_FIELD_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported field type '{type}'.",
            )
        if type == "enum" and not options:
            raise HTTPException(
                status_code=400,
                detail="Enum fields require a non-empty 'options' list.",
            )
        if validators:
            if type in {"string", "enum"}:
                permitted = _STRING_VALIDATORS
            else:  # number / integer / boolean
                permitted = _NUMBER_VALIDATORS
            illegal = set(validators) - permitted
            if illegal:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Validator(s) {sorted(illegal)} are not supported for a "
                        f"'{type}' field."
                    ),
                )
            # A ``pattern`` value is only compiled lazily by jsonschema at contact
            # write time, so validate it here — otherwise a bad regex is accepted and
            # later crashes every create/update against this schema with a 500.
            pattern = validators.get("pattern")
            if pattern is not None:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid 'pattern' validator: {exc}",
                    ) from exc

    def _assert_composes(self, schema_id, replacement: SchemaField) -> None:
        """Compose the schema (active fields, with ``replacement`` swapped in) into a
        JSON Schema to prove it is well-formed. Reuses the shared builder so the exact
        validation shape matches enforcement at contact create/sync time."""
        fields = [
            f for f in self._active_fields(schema_id) if f.id != replacement.id
        ]
        if replacement.is_active and replacement.deleted_at is None:
            fields.append(replacement)
        try:
            build_contact_field_json_schema(fields)
        except Exception:
            logger.exception(
                "[contact-schema] failed to compose JSON schema schema_id={}", schema_id
            )
            raise HTTPException(
                status_code=400,
                detail="Field configuration produces an invalid schema.",
            )
