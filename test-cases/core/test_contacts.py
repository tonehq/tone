"""Directory-scoped contacts tests (Core edition) — real DB, real endpoints.

Covers: contact API auth, directory-scoped list/create/update/delete, org + directory
IDOR (a contact in another org / another directory never surfaces), partial multi-add
(one invalid row → ``{created, failed}``), and ``(directory_id, external_id)``
uniqueness (re-adding the same external_id upserts rather than duplicating).

Every fixture provisions a ``ContactDirectory`` first because ``contacts.directory_id``
is now REQUIRED (RESTRICT). Metadata validation is exercised via a directory whose
default schema has one mandatory field.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from core.api.v1 import contacts as contacts_router
from core.database.session import get_db
from core.middleware.auth import JWTManager
from core.models.agent import Agent
from core.models.agent_contact import AgentContact
from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.models.contact_schema import ContactSchema
from core.models.schema_field import SchemaField
from core.services.contacts.contact_service import ContactService
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
    return ContactService(db, user_id=REAL_USER_ID, org_id=uuid.UUID(str(ORG_ID)))


# The contacts router is directory-scoped and mounted PREFIX-LESS by Phase C
# (``/contact-directories/...`` + ``/contact/schedule-calls``). To exercise those exact
# URLs independently of main.py wiring (owned by another subtask), mount the router on a
# fresh app at prefix "" and point it at the test DB session.
def _router_client(db_session, role="member"):
    app = FastAPI()
    app.include_router(contacts_router.router, prefix="/api/v1")

    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    client = TestClient(app)
    if role is not None:
        token = JWTManager().create_access_token(
            user_id=REAL_USER_ID, email=f"{role}@test.com", org_id=ORG_ID, role=role,
        )
        client.headers["Authorization"] = f"Bearer {token}"
        client.headers["tenant_id"] = ORG_ID
    return client


def _make_directory(db, *, org_id=None, default_schema_id=None, name=None):
    """Create a ContactDirectory row directly (RESTRICT FK requires one to exist)."""
    directory = ContactDirectory(
        organization_id=uuid.UUID(str(org_id or ORG_ID)),
        name=name or f"Dir {uuid.uuid4().hex[:6]}",
        default_schema_id=default_schema_id,
        is_active=True,
    )
    db.add(directory)
    db.commit()
    db.refresh(directory)
    return directory


def _make_agent(db, *, org_id=None):
    """Create an Agent row directly (for create-with-agent_id assignment tests)."""
    agent = Agent(
        organization_id=uuid.UUID(str(org_id or ORG_ID)),
        name=f"agent-{uuid.uuid4().hex[:8]}",
        agent_type="outbound",
        created_by_user_id=REAL_USER_ID,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _make_schema_with_mandatory_field(db, field_name="priority"):
    """Create an org schema with one mandatory string field, return the schema."""
    schema = ContactSchema(
        organization_id=uuid.UUID(str(ORG_ID)),
        name=f"Schema {uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    field = SchemaField(
        organization_id=uuid.UUID(str(ORG_ID)),
        schema_id=schema.id,
        field_name=field_name,
        type="string",
        is_mandatory=True,
        is_active=True,
    )
    db.add(field)
    db.commit()
    return schema


# --------------------------------------------------------------------- API auth

class TestContactApiAuth:
    def test_list_requires_auth(self, db_session):
        directory = _make_directory(db_session)
        client = _router_client(db_session, role=None)
        r = client.post(f"/api/v1/contact-directories/{directory.id}/contacts/list", json={})
        assert r.status_code in (401, 403)

    def test_member_can_list(self, db_session):
        directory = _make_directory(db_session)
        client = _router_client(db_session)
        r = client.post(
            f"/api/v1/contact-directories/{directory.id}/contacts/list",
            json={"page_no": 1, "page_size": 10},
        )
        assert r.status_code == 200
        assert "data" in r.json()

    def test_create_returns_created_failed_shape(self, db_session):
        directory = _make_directory(db_session)
        client = _router_client(db_session)
        ext = f"api-{uuid.uuid4().hex[:8]}"
        r = client.post(
            f"/api/v1/contact-directories/{directory.id}/contacts",
            json={"contact": {"name": "API", "phone_number": "+14155550199", "external_id": ext}},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["failed"] == []
        assert len(body["created"]) == 1
        assert body["created"][0]["external_id"] == ext
        assert body["created"][0]["directory_id"] == str(directory.id)


# -------------------------------------------------- create + agent assignment

class TestCreateWithAgentAssignment:
    def test_create_with_agent_id_assigns_created_contacts(self, db_session):
        # Creating contacts WITH agent_id inserts agent_contacts for the created rows.
        directory = _make_directory(db_session)
        agent = _make_agent(db_session)
        client = _router_client(db_session)
        ext = f"assign-{uuid.uuid4().hex[:8]}"
        r = client.post(
            f"/api/v1/contact-directories/{directory.id}/contacts",
            json={
                "contact": {"name": "Assigned", "phone_number": "+14155550140", "external_id": ext},
                "agent_id": str(agent.id),
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert len(body["created"]) == 1
        assert body.get("assigned") == 1
        created_id = uuid.UUID(body["created"][0]["id"])

        rows = (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .all()
        )
        assert {row.contact_id for row in rows} == {created_id}

    def test_create_without_agent_id_does_not_assign(self, db_session):
        # Creating contacts WITHOUT agent_id must NOT create any agent_contacts.
        directory = _make_directory(db_session)
        agent = _make_agent(db_session)
        client = _router_client(db_session)
        ext = f"noassign-{uuid.uuid4().hex[:8]}"
        r = client.post(
            f"/api/v1/contact-directories/{directory.id}/contacts",
            json={"contact": {"name": "Unassigned", "phone_number": "+14155550141", "external_id": ext}},
        )
        assert r.status_code == 201
        assert "assigned" not in r.json()
        assert (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .count()
            == 0
        )


# ---------------------------------------------------------------------- IDOR

class TestContactOrgScoping:
    def test_foreign_org_contact_not_listed_or_fetchable(self, db_session):
        # A contact belonging to a DIFFERENT org must never surface for ORG_ID.
        foreign_org = uuid.uuid4()
        foreign_dir = _make_directory(db_session, org_id=foreign_org)
        foreign = Contact(
            organization_id=foreign_org,
            directory_id=foreign_dir.id,
            external_id=f"foreign-{uuid.uuid4().hex[:8]}",
            name="Foreign",
            phone_number="+14155550111",
            contact_metadata={},
            is_active=True,
        )
        db_session.add(foreign)
        db_session.commit()

        # PATCH on a foreign contact id → 404 (org scoped).
        client = _router_client(db_session)
        r = client.patch(f"/api/v1/contacts/{foreign.id}", json={"name": "x"})
        assert r.status_code == 404

    def test_directory_scoping_isolates_contacts(self, db_session):
        # A contact in directory A must not appear when listing directory B.
        svc = _svc(db_session)
        dir_a = _make_directory(db_session)
        dir_b = _make_directory(db_session)
        res = svc.create_contacts(dir_a.id, [{"name": "OnlyA", "external_id": f"a-{uuid.uuid4().hex[:6]}"}])
        contact_id = res["created"][0]["id"]

        listed_b = svc.list_contacts(dir_b.id, page_size=100)
        assert all(row["id"] != contact_id for row in listed_b["data"])

        listed_a = svc.list_contacts(dir_a.id, page_size=100)
        assert any(row["id"] == contact_id for row in listed_a["data"])


# ----------------------------------------------------------------- CRUD service

class TestContactServiceCrud:
    def test_create_search_delete(self, db_session):
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        res = svc.create_contacts(
            directory.id,
            [{"name": "Zoe", "phone_number": "+14155550123", "external_id": f"z-{uuid.uuid4().hex[:6]}"}],
        )
        contact_id = res["created"][0]["id"]
        found = svc.list_contacts(directory.id, search="Zoe")
        assert any(row["id"] == contact_id for row in found["data"])
        svc.delete_contact(uuid.UUID(contact_id))
        with pytest.raises(HTTPException):
            svc.get_contact(uuid.UUID(contact_id))

    def test_bulk_delete_directory_scoped(self, db_session):
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        res = svc.create_contacts(
            directory.id,
            [
                {"name": "A", "external_id": f"a-{uuid.uuid4().hex[:6]}"},
                {"name": "B", "external_id": f"b-{uuid.uuid4().hex[:6]}"},
            ],
        )
        ids = [uuid.UUID(c["id"]) for c in res["created"]]
        out = svc.bulk_delete_contacts(directory.id, ids)
        assert out["deleted"] == 2

    def test_missing_directory_404(self, db_session):
        svc = _svc(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.list_contacts(uuid.uuid4())
        assert exc.value.status_code == 404


# ------------------------------------------------ update identity invariant

class TestUpdateContactInvariant:
    def test_update_cannot_clear_only_identity(self, db_session):
        # Clearing the name of a phone-less contact would leave an identity-less,
        # un-dialable row — rejected (400), matching the create-time invariant. The
        # row must be left untouched.
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        res = svc.create_contacts(
            directory.id,
            [{"name": "OnlyName", "external_id": f"only-{uuid.uuid4().hex[:6]}"}],
        )
        cid = uuid.UUID(res["created"][0]["id"])
        with pytest.raises(HTTPException) as exc:
            svc.update_contact(cid, name="")
        assert exc.value.status_code == 400
        # Rejected update leaves the row unchanged.
        assert svc.get_contact(cid).name == "OnlyName"

    def test_update_clearing_name_keeps_contact_with_phone(self, db_session):
        # Clearing name is allowed while a phone number remains (identity preserved).
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        res = svc.create_contacts(
            directory.id,
            [{"name": "Named", "phone_number": "+14155550170",
              "external_id": f"keep-{uuid.uuid4().hex[:6]}"}],
        )
        cid = uuid.UUID(res["created"][0]["id"])
        updated = svc.update_contact(cid, name="")
        assert updated.name is None
        assert updated.phone_number == "+14155550170"

    def test_api_patch_clearing_only_identity_returns_400(self, db_session):
        directory = _make_directory(db_session)
        client = _router_client(db_session)
        ext = f"api-only-{uuid.uuid4().hex[:8]}"
        created = client.post(
            f"/api/v1/contact-directories/{directory.id}/contacts",
            json={"contact": {"name": "OnlyName", "external_id": ext}},
        ).json()
        contact_id = created["created"][0]["id"]
        r = client.patch(f"/api/v1/contacts/{contact_id}", json={"name": ""})
        assert r.status_code == 400


# ----------------------------------------------------- partial multi-add

class TestPartialMultiAdd:
    def test_one_invalid_row_partial(self, db_session):
        # Directory with a schema requiring a mandatory "priority" field.
        schema = _make_schema_with_mandatory_field(db_session, field_name="priority")
        directory = _make_directory(db_session, default_schema_id=schema.id)
        svc = _svc(db_session)
        res = svc.create_contacts(
            directory.id,
            [
                {"name": "Valid", "external_id": f"v-{uuid.uuid4().hex[:6]}",
                 "contact_metadata": {"priority": "high"}},
                {"name": "Invalid", "external_id": f"i-{uuid.uuid4().hex[:6]}",
                 "contact_metadata": {}},  # missing mandatory field
            ],
        )
        assert len(res["created"]) == 1
        assert res["created"][0]["name"] == "Valid"
        assert len(res["failed"]) == 1
        assert res["failed"][0]["index"] == 1
        assert res["failed"][0]["errors"]

    def test_empty_rows_rejected(self, db_session):
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.create_contacts(directory.id, [])
        assert exc.value.status_code == 400

    def test_all_empty_contact_rejected(self, db_session):
        # A row with neither name nor phone must not create an empty contact.
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        res = svc.create_contacts(
            directory.id,
            [{"name": None, "phone_number": None, "contact_metadata": {}}],
        )
        assert res["created"] == []
        assert len(res["failed"]) == 1
        assert res["failed"][0]["index"] == 0
        assert res["failed"][0]["errors"]


# ----------------------------------------------------- uniqueness (dir, external_id)

class TestUniqueness:
    def test_same_external_id_upserts_within_directory(self, db_session):
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        ext = f"dup-{uuid.uuid4().hex[:6]}"
        first = svc.create_contacts(directory.id, [{"name": "First", "external_id": ext}])
        first_id = first["created"][0]["id"]
        second = svc.create_contacts(directory.id, [{"name": "Second", "external_id": ext}])
        # Upsert: same row id, updated name — not a duplicate.
        assert second["created"][0]["id"] == first_id
        assert second["created"][0]["name"] == "Second"
        listed = svc.list_contacts(directory.id, search=ext, page_size=100)
        assert sum(1 for r in listed["data"] if r["external_id"] == ext) == 1

    def test_same_external_id_distinct_across_directories(self, db_session):
        svc = _svc(db_session)
        dir_a = _make_directory(db_session)
        dir_b = _make_directory(db_session)
        ext = f"shared-{uuid.uuid4().hex[:6]}"
        a = svc.create_contacts(dir_a.id, [{"name": "A", "external_id": ext}])
        b = svc.create_contacts(dir_b.id, [{"name": "B", "external_id": ext}])
        # Same external_id in two directories → two distinct contacts.
        assert a["created"][0]["id"] != b["created"][0]["id"]


# ------------------------------------------------- list_contact_ids_in_directories

class TestListContactIdsInDirectories:
    def test_returns_active_ids_across_directories(self, db_session):
        svc = _svc(db_session)
        dir_a = _make_directory(db_session)
        dir_b = _make_directory(db_session)
        a = svc.create_contacts(dir_a.id, [{"name": "A", "external_id": f"a-{uuid.uuid4().hex[:6]}"}])
        b = svc.create_contacts(dir_b.id, [{"name": "B", "external_id": f"b-{uuid.uuid4().hex[:6]}"}])
        ids = svc.list_contact_ids_in_directories([dir_a.id, dir_b.id])
        ids_str = {str(i) for i in ids}
        assert a["created"][0]["id"] in ids_str
        assert b["created"][0]["id"] in ids_str

    def test_empty_input_returns_empty(self, db_session):
        svc = _svc(db_session)
        assert svc.list_contact_ids_in_directories([]) == []

    def test_excludes_deleted(self, db_session):
        svc = _svc(db_session)
        directory = _make_directory(db_session)
        res = svc.create_contacts(directory.id, [{"name": "Gone", "external_id": f"g-{uuid.uuid4().hex[:6]}"}])
        cid = res["created"][0]["id"]
        svc.delete_contact(uuid.UUID(cid))
        ids = {str(i) for i in svc.list_contact_ids_in_directories([directory.id])}
        assert cid not in ids
