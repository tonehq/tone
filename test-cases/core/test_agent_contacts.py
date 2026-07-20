"""AgentContactService tests (Core edition) — real DB, service-level.

Covers B6 ACs: directory-expansion assign, union with explicit contact_ids, dedupe of
already-assigned rows (idempotent), unassign, the unique ``(agent_id, contact_id)``
constraint, empty-directory assign is a no-op, and org IDOR (agent/contacts in another
org are invisible).

The router isn't mounted here (B7 owns wiring) and ``ContactService`` is owned by a
parallel agent, so these exercise ``AgentContactService`` directly against the DB session.
Directory-expansion assertions are skipped if ``ContactService`` isn't present yet.
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text

from core.models.agent import Agent
from core.models.agent_contact import AgentContact
from core.models.contact import Contact
from core.models.contact_directory import ContactDirectory
from core.services.contacts.agent_contact_service import AgentContactService
from shared.config import settings


def _first_row(query: str, default):
    conn = create_engine(settings.DATABASE_URL, pool_pre_ping=True).connect()
    try:
        row = conn.execute(text(query)).fetchone()
        return row[0] if row else default
    finally:
        conn.close()


ORG_ID = uuid.UUID(str(_first_row("SELECT id FROM organizations LIMIT 1", settings.DEFAULT_ORG_ID)))
OTHER_ORG_ID = uuid.uuid4()
REAL_USER_ID = _first_row("SELECT id FROM users LIMIT 1", None)


def _svc(db, org_id=ORG_ID):
    return AgentContactService(db, user_id=REAL_USER_ID, org_id=org_id)


def _make_agent(db, org_id=ORG_ID, agent_type="outbound"):
    agent = Agent(
        organization_id=org_id,
        name=f"agent-{uuid.uuid4().hex[:8]}",
        agent_type=agent_type,
        created_by_user_id=REAL_USER_ID,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _make_directory(db, org_id=ORG_ID):
    directory = ContactDirectory(
        organization_id=org_id,
        name=f"dir-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(directory)
    db.commit()
    db.refresh(directory)
    return directory


def _make_contact(db, directory_id, org_id=ORG_ID, phone="+14155550100", name="C"):
    contact = Contact(
        organization_id=org_id,
        directory_id=directory_id,
        external_id=f"ext-{uuid.uuid4().hex[:8]}",
        name=name,
        phone_number=phone,
        contact_metadata={},
        is_active=True,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def _has_contact_service() -> bool:
    try:
        import core.services.contacts.contact_service  # noqa: F401
        return True
    except Exception:
        return False


# --------------------------------------------------------------------- assign

class TestAssign:
    def test_assign_explicit_contact_ids(self, db_session):
        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id)
        c2 = _make_contact(db_session, directory.id)

        result = _svc(db_session).assign_contacts_to_agent(
            agent.id, contact_ids=[c1.id, c2.id]
        )
        assert result == {"assigned": 2, "skipped": 0}

        rows = (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .all()
        )
        assert {r.contact_id for r in rows} == {c1.id, c2.id}

    def test_assign_is_idempotent_dedupes_already_assigned(self, db_session):
        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id)
        c2 = _make_contact(db_session, directory.id)

        svc = _svc(db_session)
        first = svc.assign_contacts_to_agent(agent.id, contact_ids=[c1.id])
        assert first == {"assigned": 1, "skipped": 0}

        # c1 already assigned → skipped; c2 new → assigned.
        second = svc.assign_contacts_to_agent(agent.id, contact_ids=[c1.id, c2.id])
        assert second == {"assigned": 1, "skipped": 1}

        count = (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .count()
        )
        assert count == 2

    def test_assign_from_directory_expands_active_contacts(self, db_session):
        if not _has_contact_service():
            pytest.skip("ContactService (parallel agent) not present yet")
        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id)
        c2 = _make_contact(db_session, directory.id)

        result = _svc(db_session).assign_contacts_to_agent(
            agent.id, directory_ids=[directory.id]
        )
        assert result["assigned"] == 2

        rows = (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .all()
        )
        assert {r.contact_id for r in rows} == {c1.id, c2.id}

    def test_assign_unions_directory_and_explicit_ids_without_double_counting(
        self, db_session
    ):
        if not _has_contact_service():
            pytest.skip("ContactService (parallel agent) not present yet")
        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id)  # in directory
        other_dir = _make_directory(db_session)
        c2 = _make_contact(db_session, other_dir.id)  # explicit only

        # c1 appears in BOTH the directory expansion and the explicit list → counted once.
        result = _svc(db_session).assign_contacts_to_agent(
            agent.id, directory_ids=[directory.id], contact_ids=[c1.id, c2.id]
        )
        assert result["assigned"] == 2

        rows = (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .all()
        )
        assert {r.contact_id for r in rows} == {c1.id, c2.id}

    def test_assign_empty_directory_is_no_op(self, db_session):
        if not _has_contact_service():
            pytest.skip("ContactService (parallel agent) not present yet")
        agent = _make_agent(db_session)
        empty_dir = _make_directory(db_session)  # no contacts

        result = _svc(db_session).assign_contacts_to_agent(
            agent.id, directory_ids=[empty_dir.id]
        )
        assert result == {"assigned": 0, "skipped": 0}
        assert (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .count()
            == 0
        )

    def test_assign_nothing_is_no_op(self, db_session):
        agent = _make_agent(db_session)
        result = _svc(db_session).assign_contacts_to_agent(agent.id)
        assert result == {"assigned": 0, "skipped": 0}

    def test_unique_constraint_prevents_duplicate_rows(self, db_session):
        """Even a direct double-insert of the same (agent, contact) is rejected by the
        unique constraint — the idempotent assign path relies on it."""
        from sqlalchemy.exc import IntegrityError

        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id)

        db_session.add(
            AgentContact(organization_id=ORG_ID, agent_id=agent.id, contact_id=c1.id)
        )
        db_session.commit()

        db_session.add(
            AgentContact(organization_id=ORG_ID, agent_id=agent.id, contact_id=c1.id)
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


# --------------------------------------------------------------------- list

class TestList:
    def test_list_returns_assigned_contacts(self, db_session):
        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id, name="Alice")
        _make_contact(db_session, directory.id, name="Bob")  # not assigned

        svc = _svc(db_session)
        svc.assign_contacts_to_agent(agent.id, contact_ids=[c1.id])

        result = svc.list_agent_contacts(agent.id)
        assert result["total"] == 1
        assert result["data"][0]["id"] == str(c1.id)
        assert "assignment_id" in result["data"][0]


# --------------------------------------------------------------------- unassign

class TestUnassign:
    def test_unassign_removes_only_join_rows(self, db_session):
        agent = _make_agent(db_session)
        directory = _make_directory(db_session)
        c1 = _make_contact(db_session, directory.id)
        c2 = _make_contact(db_session, directory.id)

        svc = _svc(db_session)
        svc.assign_contacts_to_agent(agent.id, contact_ids=[c1.id, c2.id])

        result = svc.unassign_contacts_from_agent(agent.id, [c1.id])
        assert result == {"unassigned": 1}

        # Join row gone, but the contact itself is untouched.
        assert (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .count()
            == 1
        )
        assert db_session.query(Contact).filter(Contact.id == c1.id).first() is not None

    def test_unassign_empty_list_is_no_op(self, db_session):
        agent = _make_agent(db_session)
        result = _svc(db_session).unassign_contacts_from_agent(agent.id, [])
        assert result == {"unassigned": 0}


# --------------------------------------------------------------------- IDOR

class TestOrgIsolation:
    def test_assign_to_agent_in_other_org_raises_404(self, db_session):
        other_agent = _make_agent(db_session, org_id=OTHER_ORG_ID)
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).assign_contacts_to_agent(other_agent.id)
        assert exc.value.status_code == 404

    def test_contact_from_other_org_not_assigned(self, db_session):
        agent = _make_agent(db_session)
        other_dir = _make_directory(db_session, org_id=OTHER_ORG_ID)
        other_contact = _make_contact(db_session, other_dir.id, org_id=OTHER_ORG_ID)

        # Explicit id from another org is silently dropped (org-scoped Contact query).
        result = _svc(db_session).assign_contacts_to_agent(
            agent.id, contact_ids=[other_contact.id]
        )
        assert result["assigned"] == 0
        assert (
            db_session.query(AgentContact)
            .filter(AgentContact.agent_id == agent.id)
            .count()
            == 0
        )

    def test_list_for_agent_in_other_org_raises_404(self, db_session):
        other_agent = _make_agent(db_session, org_id=OTHER_ORG_ID)
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).list_agent_contacts(other_agent.id)
        assert exc.value.status_code == 404
