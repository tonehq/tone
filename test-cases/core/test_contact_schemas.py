"""Contact schema + field tests (org-level ``ContactSchema`` / ``SchemaField``) — real DB.

Ported from the old ``test_contact_fields.py`` (which targeted the removed flat
``contact_field_definitions`` table). Keeps the equivalent coverage against the new
schema-scoped model — bad type rejected, enum requires options, unsupported validator
rejected, mandatory enforcement, unmanaged keys allowed, disabling a field stops
enforcement — and adds schema-service specifics: referenced-by warning, delete-default
blocked, and the admin-guard (member 403).

Enforcement is asserted against the shared reusable validator composed from a schema's
fields (``contact_metadata_validation``), which is the exact code the contact-create and
sync paths reuse — ``ContactService`` itself is directory-scoped and owned by B4, so we
validate the schema/field layer here.
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text

from core.services.contacts.contact_metadata_validation import (
    make_contact_metadata_validator,
    validate_contact_metadata,
)
from core.services.contacts.contact_schema_service import ContactSchemaService
from shared.config import settings


def _org_id():
    conn = create_engine(settings.DATABASE_URL, pool_pre_ping=True).connect()
    try:
        row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        return uuid.UUID(str(row[0])) if row else uuid.UUID(settings.DEFAULT_ORG_ID)
    finally:
        conn.close()


ORG_ID = _org_id()


def _svc(db):
    return ContactSchemaService(db, user_id=None, org_id=ORG_ID)


def _sname():
    return f"schema_{uuid.uuid4().hex[:8]}"


def _fname():
    return f"field_{uuid.uuid4().hex[:8]}"


def _new_schema(svc):
    return svc.create_schema(name=_sname())


def _validate(fields, metadata):
    """Compose the reusable validator from a schema's fields and return errors."""
    managed, validator = make_contact_metadata_validator(fields)
    return validate_contact_metadata(metadata, managed, validator)


# ---------------------------------------------------------------------------
# Schema CRUD
# ---------------------------------------------------------------------------

class TestSchemaCrud:
    def test_create_and_list(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        listed = svc.list_schemas(page_size=100)["data"]
        assert any(s["id"] == str(schema.id) for s in listed)

    def test_get_detail_includes_fields_and_referenced_by(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        svc.create_schema_field(schema.id, field_name=_fname(), type="string")
        detail = svc.get_schema_detail(schema.id)
        assert len(detail["fields"]) == 1
        assert detail["referenced_by"] == {"directories": 0, "syncs": 0}

    def test_get_missing_schema_404(self, db_session):
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).get_schema(uuid.uuid4())
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Field CRUD + guardrails (ported from test_contact_fields.py)
# ---------------------------------------------------------------------------

class TestFieldCrud:
    def test_create_and_list_field(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        svc.create_schema_field(schema.id, field_name=name, type="string", is_mandatory=True)
        detail = svc.get_schema_detail(schema.id)
        assert any(f["field_name"] == name for f in detail["fields"])

    def test_duplicate_field_conflicts(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        svc.create_schema_field(schema.id, field_name=name, type="string")
        with pytest.raises(HTTPException) as exc:
            svc.create_schema_field(schema.id, field_name=name, type="string")
        assert exc.value.status_code == 409

    def test_recreate_after_delete_revives_not_500(self, db_session):
        # The (schema_id, field_name) unique constraint counts soft-deleted rows, so
        # re-adding a previously-removed field must revive it, not violate the constraint.
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        f = svc.create_schema_field(schema.id, field_name=name, type="string")
        svc.delete_schema_field(f.id)  # soft-delete
        revived = svc.create_schema_field(
            schema.id, field_name=name, type="integer", is_mandatory=True
        )
        assert revived.type == "integer" and revived.is_mandatory is True
        assert revived.deleted_at is None and revived.is_active is True
        rows = [f for f in svc.get_schema_detail(schema.id)["fields"] if f["field_name"] == name]
        assert len(rows) == 1

    def test_bad_type_rejected(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        with pytest.raises(HTTPException):
            svc.create_schema_field(schema.id, field_name=_fname(), type="datetime")

    def test_unsupported_validator_rejected(self, db_session):
        # minimum is a number validator; illegal on a string field.
        svc = _svc(db_session)
        schema = _new_schema(svc)
        with pytest.raises(HTTPException):
            svc.create_schema_field(
                schema.id, field_name=_fname(), type="string", validators={"minimum": 3}
            )

    def test_invalid_pattern_validator_rejected(self, db_session):
        # A malformed regex must be rejected at field-create (400), not accepted and
        # later crashed with a 500 when jsonschema compiles it at contact-write time.
        svc = _svc(db_session)
        schema = _new_schema(svc)
        with pytest.raises(HTTPException) as exc:
            svc.create_schema_field(
                schema.id, field_name=_fname(), type="string", validators={"pattern": "["}
            )
        assert exc.value.status_code == 400

    def test_valid_pattern_validator_accepted(self, db_session):
        # A well-formed regex is accepted and enforced by the composed validator.
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        f = svc.create_schema_field(
            schema.id, field_name=name, type="string", validators={"pattern": "^[0-9]+$"}
        )
        assert f.validators == {"pattern": "^[0-9]+$"}
        assert _validate(svc._active_fields(schema.id), {name: "123"}) == []
        assert _validate(svc._active_fields(schema.id), {name: "abc"})

    def test_enum_requires_options(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        with pytest.raises(HTTPException):
            svc.create_schema_field(schema.id, field_name=_fname(), type="enum")

    def test_enum_with_options_ok(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        f = svc.create_schema_field(
            schema.id,
            field_name=_fname(),
            type="enum",
            options=[{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
        )
        assert f.type == "enum"


# ---------------------------------------------------------------------------
# JSON-Schema composition + enforcement (via reusable validator)
# ---------------------------------------------------------------------------

class TestEnforcement:
    def test_mandatory_missing_rejected(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        svc.create_schema_field(schema.id, field_name=name, type="string", is_mandatory=True)
        errors = _validate(svc._active_fields(schema.id), {})
        assert errors  # missing required field flagged

    def test_validator_violation_rejected(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        svc.create_schema_field(
            schema.id, field_name=name, type="string", validators={"maxLength": 3}
        )
        errors = _validate(svc._active_fields(schema.id), {name: "toolong"})
        assert errors

    def test_valid_metadata_accepted(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        svc.create_schema_field(
            schema.id, field_name=name, type="string", is_mandatory=True,
            validators={"maxLength": 10},
        )
        errors = _validate(svc._active_fields(schema.id), {name: "ok"})
        assert errors == []

    def test_unmanaged_extra_keys_allowed(self, db_session):
        # No field for 'company' → it flows through untouched.
        svc = _svc(db_session)
        schema = _new_schema(svc)
        svc.create_schema_field(schema.id, field_name=_fname(), type="string")
        errors = _validate(svc._active_fields(schema.id), {"company": "Acme"})
        assert errors == []

    def test_disabling_field_stops_enforcement(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        name = _fname()
        f = svc.create_schema_field(
            schema.id, field_name=name, type="string", is_mandatory=True
        )
        svc.delete_schema_field(f.id)  # soft-disable
        # Mandatory no longer enforced → empty metadata validates clean.
        errors = _validate(svc._active_fields(schema.id), {})
        assert errors == []


# ---------------------------------------------------------------------------
# Referenced-by warning + delete-default blocked
# ---------------------------------------------------------------------------

class TestSchemaReferences:
    def _make_directory(self, db_session, default_schema_id=None):
        from core.models.contact_directory import ContactDirectory

        directory = ContactDirectory(
            organization_id=ORG_ID,
            name=f"dir_{uuid.uuid4().hex[:8]}",
            default_schema_id=default_schema_id,
            is_active=True,
        )
        db_session.add(directory)
        db_session.commit()
        db_session.refresh(directory)
        return directory

    def test_referenced_by_counts_directories(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        self._make_directory(db_session, default_schema_id=schema.id)
        result = svc.update_schema(schema.id, description="edited")
        assert result["referenced_by"]["directories"] == 1

    def test_referenced_by_counts_syncs(self, db_session):
        from core.models.contact_sync import ContactSync

        svc = _svc(db_session)
        schema = _new_schema(svc)
        sync = ContactSync(
            organization_id=ORG_ID, schema_id=schema.id, status="completed",
        )
        db_session.add(sync)
        db_session.commit()
        result = svc.update_schema(schema.id, name=_sname())
        assert result["referenced_by"]["syncs"] == 1

    def test_delete_default_schema_blocked(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        self._make_directory(db_session, default_schema_id=schema.id)
        with pytest.raises(HTTPException) as exc:
            svc.delete_schema(schema.id)
        assert exc.value.status_code == 409

    def test_delete_unreferenced_schema_ok(self, db_session):
        svc = _svc(db_session)
        schema = _new_schema(svc)
        result = svc.delete_schema(schema.id)
        assert result["ok"] is True
        # Soft-deleted → no longer listed.
        listed = svc.list_schemas(page_size=100)["data"]
        assert all(s["id"] != str(schema.id) for s in listed)


# ---------------------------------------------------------------------------
# Admin guard (member 403) — via the real router
# ---------------------------------------------------------------------------

class TestAdminGuard:
    def test_member_cannot_create_schema(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/contact-schemas", json={"name": _sname()}
        )
        assert resp.status_code == 403

    def test_admin_can_create_schema(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/contact-schemas", json={"name": _sname()}
        )
        assert resp.status_code == 201

    def test_member_can_list_schemas(self, client_as_member):
        resp = client_as_member.post("/api/v1/contact-schemas/list", json={})
        assert resp.status_code == 200

    def test_member_cannot_delete_schema(self, client_as_admin, client_as_member):
        created = client_as_admin.post(
            "/api/v1/contact-schemas", json={"name": _sname()}
        ).json()
        resp = client_as_member.delete(f"/api/v1/contact-schemas/{created['id']}")
        assert resp.status_code == 403
