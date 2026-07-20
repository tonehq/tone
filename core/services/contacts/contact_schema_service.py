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

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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

    def _active_fields(self, schema_id) -> List[SchemaField]:
        return (
            self.query(SchemaField)
            .filter(
                SchemaField.schema_id == schema_id,
                SchemaField.is_active.is_(True),
                SchemaField.deleted_at.is_(None),
            )
            .order_by(SchemaField.display_order.asc(), SchemaField.created_at.asc())
            .all()
        )

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
