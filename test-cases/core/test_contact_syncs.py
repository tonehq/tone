"""ContactSyncService tests (Core edition) — real DB, R2 download monkeypatched.

Exercises the unified sync executor ``run_contact_sync`` directly (the Procrastinate
worker just loads the sync and calls it), covering:
- partial failure: valid rows land with ``sync_id``, invalid rows recorded in
  ``row_errors`` and skipped; counts correct; status ``completed``.
- auto-assign: an ``agent_id`` on the sync inserts ``agent_contacts`` for imported rows.
- hard failure: a file whose rows all fail validation → status ``failed``, nothing lands.
- idempotent redelivery: re-running a terminal sync is a no-op.
- C-3: a directory hard-deleted (soft-deleted) mid-run aborts cleanly as
  ``failed`` (error="directory deleted") without upserting.

The R2 blob download is monkeypatched to return canned CSV bytes so these stay hermetic.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

from core.models.agent import Agent
from core.models.agent_contact import AgentContact
from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.models.contact_schema import ContactSchema
from core.models.contact_sync import ContactSync
from core.models.datasource import Datasource
from core.models.schema_field import SchemaField
from core.models.upload import Upload
from core.services.contacts.contact_sync_service import ContactSyncService
from shared.config import settings


def _first_row(query: str, default):
    conn = create_engine(settings.DATABASE_URL, pool_pre_ping=True).connect()
    try:
        row = conn.execute(text(query)).fetchone()
        return row[0] if row else default
    finally:
        conn.close()


ORG_ID = str(_first_row("SELECT id FROM organizations LIMIT 1", settings.DEFAULT_ORG_ID))
REAL_USER_ID = _first_row("SELECT id FROM users LIMIT 1", 1)


def _svc(db):
    return ContactSyncService(db, user_id=REAL_USER_ID, org_id=uuid.UUID(str(ORG_ID)))


# --------------------------------------------------------------------- fixtures


def _make_schema(db, *, field_name="priority", mandatory=True, source_key=None):
    """Org schema with reserved name/phone/external_id fields + one mandatory metadata
    field, so a row missing that field fails validation (drives partial/hard failure)."""
    schema = ContactSchema(
        organization_id=uuid.UUID(str(ORG_ID)),
        name=f"Schema {uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)

    fields = [
        ("name", "string", False),
        ("phone_number", "string", False),
        ("external_id", "string", False),
        (field_name, "string", mandatory),
    ]
    for fname, ftype, is_mand in fields:
        db.add(
            SchemaField(
                organization_id=uuid.UUID(str(ORG_ID)),
                schema_id=schema.id,
                field_name=fname,
                type=ftype,
                is_mandatory=is_mand,
                source_key=source_key if fname == field_name else None,
                is_active=True,
            )
        )
    db.commit()
    return schema


def _make_directory(db, *, default_schema_id=None):
    directory = ContactDirectory(
        organization_id=uuid.UUID(str(ORG_ID)),
        name=f"Dir {uuid.uuid4().hex[:6]}",
        default_schema_id=default_schema_id,
        is_active=True,
    )
    db.add(directory)
    db.commit()
    db.refresh(directory)
    return directory


def _make_datasource(db, directory_id):
    ds = Datasource(
        organization_id=uuid.UUID(str(ORG_ID)),
        directory_id=directory_id,
        name="CSV Import",
        type="csv",
        config={},
        is_active=True,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def _make_upload(db):
    up = Upload(
        organization_id=uuid.UUID(str(ORG_ID)),
        container_name="bucket",
        file_path=f"contacts/{ORG_ID}/{uuid.uuid4()}/f.csv",
        file_name="f.csv",
        file_type="text/csv",
        size_bytes=10,
        purpose="contact_import",
        status="ready",
        meta_data={},
    )
    db.add(up)
    db.commit()
    db.refresh(up)
    return up


def _make_agent(db):
    agent = Agent(
        organization_id=uuid.UUID(str(ORG_ID)),
        name=f"Agent {uuid.uuid4().hex[:6]}",
        agent_type="outbound",
        created_by_user_id=REAL_USER_ID,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _make_sync(db, *, directory, schema, upload, datasource, agent_id=None):
    sync = ContactSync(
        organization_id=uuid.UUID(str(ORG_ID)),
        directory_id=directory.id,
        datasource_id=datasource.id,
        schema_id=schema.id,
        upload_id=upload.id,
        agent_id=agent_id,
        status="pending",
        counts={},
        row_errors=[],
        created_by_user_id=REAL_USER_ID,
    )
    db.add(sync)
    db.commit()
    db.refresh(sync)
    return sync


def _patch_download(monkeypatch, csv_text: str):
    """Make R2 download return the given CSV bytes (hermetic)."""
    from core.services import r2_storage_service

    def _fake_download(self, object_key):
        return csv_text.encode("utf-8")

    monkeypatch.setattr(
        r2_storage_service.R2StorageService, "download_file", _fake_download
    )


# ------------------------------------------------------------------- scenarios


class TestPartialFailure:
    def test_valid_rows_land_with_sync_id_invalid_recorded(self, db_session, monkeypatch):
        schema = _make_schema(db_session)  # 'priority' mandatory
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)
        upload = _make_upload(db_session)
        sync = _make_sync(
            db_session, directory=directory, schema=schema, upload=upload, datasource=datasource
        )

        # Row 1 valid (has priority); row 2 invalid (missing mandatory priority).
        _patch_download(
            monkeypatch,
            "external_id,name,phone_number,priority\n"
            "c1,Alice,+14155550123,high\n"
            "c2,Bob,+14155550124,\n",
        )

        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)

        assert sync.status == "completed"
        assert sync.counts["created"] == 1
        assert sync.counts["failed"] == 1
        assert len(sync.row_errors) >= 1

        contacts = (
            db_session.query(Contact)
            .filter(Contact.directory_id == directory.id, Contact.deleted_at.is_(None))
            .all()
        )
        assert len(contacts) == 1
        assert contacts[0].external_id == "c1"
        assert contacts[0].sync_id == sync.id

    def test_metadata_only_schema_keeps_base_identity_partial(self, db_session, monkeypatch):
        # The schema maps ONLY a mandatory metadata field (city); name/phone/external_id
        # are NOT schema fields. The base identity (external_id synthesized from phone)
        # must survive, so the valid row imports and the empty-city row is skipped —
        # a partial success, NOT an all-rows-failed hard failure.
        schema = _make_schema(db_session, field_name="city")  # 'city' mandatory
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)
        upload = _make_upload(db_session)
        sync = _make_sync(
            db_session, directory=directory, schema=schema, upload=upload, datasource=datasource
        )
        # No external_id column — it must be synthesized from the phone number.
        _patch_download(
            monkeypatch,
            "name,phone_number,city\n"
            "John Doe,+919789483349,Erode\n"
            "Testing,+911234567890,\n",
        )

        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)

        assert sync.status == "completed"
        assert sync.counts["created"] == 1
        assert sync.counts["failed"] == 1

        contacts = (
            db_session.query(Contact)
            .filter(Contact.directory_id == directory.id, Contact.deleted_at.is_(None))
            .all()
        )
        assert len(contacts) == 1
        assert contacts[0].name == "John Doe"
        assert contacts[0].external_id == "+919789483349"  # synthesized from phone
        assert (contacts[0].contact_metadata or {}).get("city") == "Erode"

        # The error report identifies WHICH row failed (name/phone), not just an index.
        assert len(sync.row_errors) >= 1
        err = sync.row_errors[0]
        assert err["name"] == "Testing"
        assert err["phone_number"] == "+911234567890"
        assert "city" in err["message"].lower()


class TestAutoAssign:
    def test_agent_id_inserts_agent_contacts(self, db_session, monkeypatch):
        schema = _make_schema(db_session)
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)
        upload = _make_upload(db_session)
        agent = _make_agent(db_session)
        sync = _make_sync(
            db_session,
            directory=directory,
            schema=schema,
            upload=upload,
            datasource=datasource,
            agent_id=agent.id,
        )

        _patch_download(
            monkeypatch,
            "external_id,name,phone_number,priority\n"
            "c1,Alice,+14155550123,high\n"
            "c2,Bob,+14155550124,low\n",
        )

        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)

        assert sync.status == "completed"
        assert sync.counts["created"] == 2

        assignments = (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .all()
        )
        assert len(assignments) == 2


class TestHardFailure:
    def test_all_rows_invalid_marks_failed_nothing_imported(self, db_session, monkeypatch):
        schema = _make_schema(db_session)  # 'priority' mandatory
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)
        upload = _make_upload(db_session)
        sync = _make_sync(
            db_session, directory=directory, schema=schema, upload=upload, datasource=datasource
        )

        # Both rows miss the mandatory priority.
        _patch_download(
            monkeypatch,
            "external_id,name,phone_number,priority\n"
            "c1,Alice,+14155550123,\n"
            "c2,Bob,+14155550124,\n",
        )

        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)

        assert sync.status == "failed"
        assert sync.error
        assert sync.counts.get("created", 0) == 0
        contacts = (
            db_session.query(Contact)
            .filter(Contact.directory_id == directory.id)
            .all()
        )
        assert contacts == []


class TestIdempotentRedelivery:
    def test_rerun_of_terminal_sync_is_noop(self, db_session, monkeypatch):
        schema = _make_schema(db_session)
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)
        upload = _make_upload(db_session)
        sync = _make_sync(
            db_session, directory=directory, schema=schema, upload=upload, datasource=datasource
        )

        _patch_download(
            monkeypatch,
            "external_id,name,phone_number,priority\nc1,Alice,+14155550123,high\n",
        )

        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)
        assert sync.status == "completed"
        first_counts = dict(sync.counts)

        # Re-running the same completed sync must NOT re-import or change counts.
        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)
        assert sync.counts == first_counts
        contacts = (
            db_session.query(Contact)
            .filter(Contact.directory_id == directory.id, Contact.deleted_at.is_(None))
            .count()
        )
        assert contacts == 1

    def test_reimport_same_external_id_upserts(self, db_session, monkeypatch):
        """A second sync of the same external_id updates rather than duplicates."""
        schema = _make_schema(db_session)
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)

        for name in ("Alice", "Alice Updated"):
            upload = _make_upload(db_session)
            sync = _make_sync(
                db_session, directory=directory, schema=schema, upload=upload, datasource=datasource
            )
            _patch_download(
                monkeypatch,
                f"external_id,name,phone_number,priority\nc1,{name},+14155550123,high\n",
            )
            _svc(db_session).run_contact_sync(sync)

        contacts = (
            db_session.query(Contact)
            .filter(Contact.directory_id == directory.id, Contact.deleted_at.is_(None))
            .all()
        )
        assert len(contacts) == 1
        assert contacts[0].name == "Alice Updated"


class TestDirectoryDeletedMidSync:
    def test_directory_soft_deleted_before_run_aborts_cleanly(self, db_session, monkeypatch):
        schema = _make_schema(db_session)
        directory = _make_directory(db_session, default_schema_id=schema.id)
        datasource = _make_datasource(db_session, directory.id)
        upload = _make_upload(db_session)
        sync = _make_sync(
            db_session, directory=directory, schema=schema, upload=upload, datasource=datasource
        )

        _patch_download(
            monkeypatch,
            "external_id,name,phone_number,priority\nc1,Alice,+14155550123,high\n",
        )

        # C-3: simulate the directory being hard-deleted (soft-deleted / torn down) after
        # the sync was enqueued but before the worker runs it.
        directory.deleted_at = datetime.now(timezone.utc)
        directory.is_active = False
        db_session.commit()

        _svc(db_session).run_contact_sync(sync)
        db_session.refresh(sync)

        assert sync.status == "failed"
        assert sync.error == "directory deleted"
        # Nothing upserted against the RESTRICT FK.
        contacts = (
            db_session.query(Contact)
            .filter(Contact.directory_id == directory.id)
            .all()
        )
        assert contacts == []
