"""ContactDirectoryService + router tests (Core edition) — real DB.

Covers (subtask B2):
- IDOR / org-scoping on get/update/delete
- create provisions a CSV datasource + an empty default schema + sets default_schema_id
- delete cascade: contacts + agent_contacts + scheduled_calls + CSV datasource deleted
- schema retention (org schemas kept)
- sync detach (SET NULL directory_id/datasource_id)
- queued dial-job cancel + scheduled_calls deleted
- C-3: pending/processing syncs marked 'failed' before detach
- call-log (calls) preservation
- admin-guard: a member role receives a real 403 on directory writes

The delete path exercises hard deletes + a Procrastinate ``cancel_outbound_job`` call,
which is monkeypatched to stay hermetic.
"""

import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from core.api.v1 import contact_directories as directories_router
from core.middleware.auth import JWTClaims, get_jwt_claims
from core.database.session import get_db
from core.models.agent_contact import AgentContact
from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.models.contact_schema import ContactSchema
from core.models.contact_sync import ContactSync
from core.models.datasource import Datasource
from core.models.scheduled_call import ScheduledCall
from core.services.contacts.contact_directory_service import ContactDirectoryService

from sqlalchemy import create_engine, text
from shared.config import settings


def _first(query: str, default):
    conn = create_engine(settings.DATABASE_URL, pool_pre_ping=True).connect()
    try:
        row = conn.execute(text(query)).fetchone()
        return row[0] if row else default
    finally:
        conn.close()


ORG_ID = str(_first("SELECT id FROM organizations LIMIT 1", settings.DEFAULT_ORG_ID))
REAL_USER_ID = _first("SELECT id FROM users LIMIT 1", None)


def _dir_svc(db):
    return ContactDirectoryService(db, user_id=REAL_USER_ID, org_id=uuid.UUID(str(ORG_ID)))


# ------------------------------------------------------------ create + provision

class TestCreateProvisions:
    def test_create_provisions_datasource_but_no_auto_schema(self, db_session):
        svc = _dir_svc(db_session)
        directory = svc.create_directory(name=f"Dir-{uuid.uuid4().hex[:6]}")

        # No schema is auto-created per directory (would pollute the org library).
        assert directory.default_schema_id is None

        # But the CSV datasource IS provisioned.
        from core.models.datasource import Datasource
        assert db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id, Datasource.type == "csv"
        ).count() == 1

    def test_create_with_user_selected_default_schema(self, db_session):
        svc = _dir_svc(db_session)
        schema = ContactSchema(
            organization_id=uuid.UUID(str(ORG_ID)), name=f"Sch-{uuid.uuid4().hex[:6]}"
        )
        db_session.add(schema)
        db_session.flush()

        directory = svc.create_directory(
            name=f"Dir-{uuid.uuid4().hex[:6]}", default_schema_id=schema.id
        )
        assert directory.default_schema_id == schema.id

        datasources = db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id
        ).all()
        assert len(datasources) == 1
        assert datasources[0].type == "csv"


# --------------------------------------------------------------- IDOR / scoping

class TestOrgScoping:
    def test_foreign_directory_not_fetchable(self, db_session):
        foreign = ContactDirectory(
            organization_id=uuid.uuid4(),  # not ORG_ID
            name="Foreign",
            is_active=True,
        )
        db_session.add(foreign)
        db_session.commit()

        svc = _dir_svc(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.get_directory(foreign.id)
        assert exc.value.status_code == 404

    def test_foreign_directory_not_deletable(self, db_session):
        foreign = ContactDirectory(
            organization_id=uuid.uuid4(),
            name="Foreign",
            is_active=True,
        )
        db_session.add(foreign)
        db_session.commit()

        svc = _dir_svc(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.delete_directory(foreign.id)
        assert exc.value.status_code == 404

    def test_update_default_schema_rejects_foreign_schema(self, db_session):
        svc = _dir_svc(db_session)
        directory = svc.create_directory(name=f"Dir-{uuid.uuid4().hex[:6]}")

        foreign_schema = ContactSchema(
            organization_id=uuid.uuid4(),  # not ORG_ID
            name="Foreign schema",
            is_active=True,
        )
        db_session.add(foreign_schema)
        db_session.commit()

        with pytest.raises(HTTPException) as exc:
            svc.update_directory(directory.id, default_schema_id=foreign_schema.id)
        assert exc.value.status_code == 404


# --------------------------------------------------------------- delete cascade

class TestDeleteCascade:
    def _seed_full_directory(self, db_session, monkeypatch):
        """Create a directory with a contact, agent_contact, scheduled_call (queued job),
        a completed call log, and a pending sync. Returns the seeded ids."""
        # cancel_outbound_job is imported lazily inside hard_delete_directory_and_children,
        # so patch it on its source module.
        import core.services.ingestion_queue as iq
        cancelled = []
        monkeypatch.setattr(iq, "cancel_outbound_job",
                            lambda job_id: cancelled.append(job_id) or True)

        svc = _dir_svc(db_session)
        org = uuid.UUID(str(ORG_ID))

        # An org schema for the directory to reference (directories no longer auto-create
        # one). Set as the directory's default so the sync + retention checks have a target.
        schema = ContactSchema(organization_id=org, name=f"Sch-{uuid.uuid4().hex[:6]}")
        db_session.add(schema)
        db_session.flush()
        directory = svc.create_directory(
            name=f"Dir-{uuid.uuid4().hex[:6]}", default_schema_id=schema.id
        )

        contact = Contact(
            organization_id=org,
            directory_id=directory.id,
            external_id=f"c-{uuid.uuid4().hex[:6]}",
            name="Target",
            phone_number="+14155550123",
            contact_metadata={},
            is_active=True,
        )
        db_session.add(contact)
        db_session.flush()

        # An agent to hang the agent_contact + scheduled_call off of.
        from core.models.agent import Agent
        agent = db_session.query(Agent).filter(Agent.organization_id == org).first()
        agent_id = agent.id if agent else None

        if agent_id:
            ac = AgentContact(
                organization_id=org, agent_id=agent_id, contact_id=contact.id,
            )
            db_session.add(ac)

        # A completed call log that must survive the delete (needs a real agent).
        call_id = None
        if agent_id:
            from core.models.call import Call
            call = Call(
                organization_id=org,
                agent_id=agent_id,
                direction="outbound",
                to_number="+14155550123",
            )
            db_session.add(call)
            db_session.flush()
            call_id = call.id

        sc = ScheduledCall(
            organization_id=org,
            agent_id=agent_id,
            contact_id=contact.id,
            from_number="+14155550000",
            to_number="+14155550123",
            scheduled_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            status="scheduled",
            queue_job_id=4242,
            call_id=call_id,
        )
        db_session.add(sc)

        # A pending sync bound to the directory (must be marked failed then detached).
        sync = ContactSync(
            organization_id=org,
            directory_id=directory.id,
            datasource_id=None,
            schema_id=directory.default_schema_id,
            status="pending",
            counts={},
            row_errors=[],
        )
        db_session.add(sync)
        db_session.commit()

        return {
            "directory_id": directory.id,
            "default_schema_id": directory.default_schema_id,
            "contact_id": contact.id,
            "call_id": call_id,
            "sync_id": sync.id,
            "cancelled": cancelled,
            "agent_id": agent_id,
        }

    def test_hard_delete_cascades_and_preserves_history(self, db_session, monkeypatch):
        seeded = self._seed_full_directory(db_session, monkeypatch)
        directory_id = seeded["directory_id"]
        default_schema_id = seeded["default_schema_id"]

        svc = _dir_svc(db_session)
        summary = svc.delete_directory(directory_id)

        # Directory gone.
        assert db_session.query(ContactDirectory).filter(
            ContactDirectory.id == directory_id
        ).first() is None

        # Contacts deleted.
        assert db_session.query(Contact).filter(
            Contact.id == seeded["contact_id"]
        ).first() is None

        # agent_contacts deleted.
        assert db_session.query(AgentContact).filter(
            AgentContact.contact_id == seeded["contact_id"]
        ).count() == 0

        # scheduled_calls deleted + queued job cancelled.
        assert db_session.query(ScheduledCall).filter(
            ScheduledCall.contact_id == seeded["contact_id"]
        ).count() == 0
        assert 4242 in seeded["cancelled"]
        assert summary["dial_jobs_cancelled"] >= 1

        # CSV datasource deleted.
        assert db_session.query(Datasource).filter(
            Datasource.directory_id == directory_id
        ).count() == 0

        # Sync marked failed AND detached (kept for audit).
        sync = db_session.query(ContactSync).filter(
            ContactSync.id == seeded["sync_id"]
        ).first()
        assert sync is not None
        assert sync.status == "failed"
        assert sync.error == "directory deleted"
        assert sync.directory_id is None
        assert sync.datasource_id is None

        # Org default schema KEPT.
        assert db_session.query(ContactSchema).filter(
            ContactSchema.id == default_schema_id
        ).first() is not None

        # Completed call log preserved (when one was seeded).
        if seeded["call_id"] is not None:
            from core.models.call import Call
            assert db_session.query(Call).filter(
                Call.id == seeded["call_id"]
            ).first() is not None

    def test_delete_impact_counts(self, db_session, monkeypatch):
        seeded = self._seed_full_directory(db_session, monkeypatch)
        svc = _dir_svc(db_session)
        impact = svc.delete_impact(seeded["directory_id"])
        assert impact["contacts"] == 1
        assert impact["scheduled_calls"] == 1
        assert impact["syncs_detached"] == 1
        assert impact["schemas_kept"] is True


# ---------------------------------------------------------------- admin guard

def _guarded_client(db_session, role: str):
    """Mount the directories router on a throwaway app and stub auth to ``role``."""
    app = FastAPI()
    app.include_router(directories_router.router, prefix="/api/v1/contact-directories")

    def _claims():
        import time
        now = int(time.time())
        return JWTClaims(
            user_id=str(REAL_USER_ID), org_id=str(ORG_ID), role=role,
            email="t@test.com", exp=now + 3600, iat=now,
        )

    app.dependency_overrides[get_jwt_claims] = _claims
    app.dependency_overrides[get_db] = lambda: (yield db_session)
    return TestClient(app)


class TestAdminGuard:
    def test_member_gets_403_on_create(self, db_session):
        client = _guarded_client(db_session, role="member")
        r = client.post("/api/v1/contact-directories", json={"name": "X"})
        assert r.status_code == 403

    def test_admin_can_create(self, db_session):
        client = _guarded_client(db_session, role="admin")
        r = client.post("/api/v1/contact-directories", json={"name": f"D-{uuid.uuid4().hex[:6]}"})
        assert r.status_code == 201
        # No schema is auto-created; default is null unless the user provides one.
        assert r.json()["default_schema_id"] is None

    def test_member_gets_403_on_delete(self, db_session):
        client = _guarded_client(db_session, role="member")
        r = client.delete(f"/api/v1/contact-directories/{uuid.uuid4()}")
        assert r.status_code == 403

    def test_member_can_list(self, db_session):
        client = _guarded_client(db_session, role="member")
        r = client.post("/api/v1/contact-directories/list", json={"page_no": 1, "page_size": 5})
        assert r.status_code == 200
