"""ContactDatasourceService + router tests (Core edition) — real DB.

Covers (subtask B2):
- create (CSV only; non-csv rejected)
- ``ensure_csv_datasource`` idempotency (returns existing, creates when absent)
- org-scoping / IDOR on directory binding + delete
- list scoped to a directory
- admin-guard: member gets a real 403 on create/delete; member can list
"""

import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from core.api.v1 import contact_datasources as datasources_router
from core.database.session import get_db
from core.middleware.auth import JWTClaims, get_jwt_claims
from core.models.contact_directory import ContactDirectory
from core.models.datasource import Datasource
from core.services.contacts.contact_datasource_service import ContactDatasourceService
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


def _ds_svc(db):
    return ContactDatasourceService(db, user_id=REAL_USER_ID, org_id=uuid.UUID(str(ORG_ID)))


def _make_directory(db):
    svc = ContactDirectoryService(db, user_id=REAL_USER_ID, org_id=uuid.UUID(str(ORG_ID)))
    return svc.create_directory(name=f"Dir-{uuid.uuid4().hex[:6]}")


# --------------------------------------------------------------------- create

class TestCreate:
    def test_create_csv_datasource(self, db_session):
        directory = _make_directory(db_session)
        ds = _ds_svc(db_session).create_datasource(name="Extra CSV", directory_id=directory.id)
        assert ds.type == "csv"
        assert ds.directory_id == directory.id
        assert ds.organization_id == uuid.UUID(str(ORG_ID))

    def test_non_csv_rejected(self, db_session):
        with pytest.raises(HTTPException) as exc:
            _ds_svc(db_session).create_datasource(name="REST", type="rest")
        assert exc.value.status_code == 400

    def test_create_rejects_foreign_directory(self, db_session):
        foreign = ContactDirectory(organization_id=uuid.uuid4(), name="Foreign", is_active=True)
        db_session.add(foreign)
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            _ds_svc(db_session).create_datasource(name="X", directory_id=foreign.id)
        assert exc.value.status_code == 404


# ----------------------------------------------------------- ensure_csv_datasource

class TestEnsureCsv:
    def test_ensure_returns_existing(self, db_session):
        # create_directory already provisions one CSV datasource.
        directory = _make_directory(db_session)
        existing = db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id
        ).one()

        got = _ds_svc(db_session).ensure_csv_datasource(directory.id)
        assert got.id == existing.id
        # No duplicate created.
        assert db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id, Datasource.type == "csv"
        ).count() == 1

    def test_ensure_creates_when_absent(self, db_session):
        # A directory row without the auto-provisioned datasource.
        directory = ContactDirectory(
            organization_id=uuid.UUID(str(ORG_ID)), name=f"Bare-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db_session.add(directory)
        db_session.commit()

        assert db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id
        ).count() == 0

        got = _ds_svc(db_session).ensure_csv_datasource(directory.id)
        assert got.type == "csv"
        assert got.directory_id == directory.id
        assert db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id
        ).count() == 1

    def test_ensure_rejects_foreign_directory(self, db_session):
        foreign = ContactDirectory(organization_id=uuid.uuid4(), name="Foreign", is_active=True)
        db_session.add(foreign)
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            _ds_svc(db_session).ensure_csv_datasource(foreign.id)
        assert exc.value.status_code == 404


# ----------------------------------------------------------------- list + delete

class TestListDelete:
    def test_list_scoped_to_directory(self, db_session):
        directory = _make_directory(db_session)
        res = _ds_svc(db_session).list_datasources(directory_id=directory.id)
        assert res["total"] >= 1
        assert all(d["directory_id"] == str(directory.id) for d in res["data"])

    def test_delete_soft_deletes(self, db_session):
        directory = _make_directory(db_session)
        ds = db_session.query(Datasource).filter(
            Datasource.directory_id == directory.id
        ).first()
        _ds_svc(db_session).delete_datasource(ds.id)
        db_session.refresh(ds)
        assert ds.deleted_at is not None
        assert ds.is_active is False

    def test_delete_rejects_foreign(self, db_session):
        foreign = Datasource(
            organization_id=uuid.uuid4(), name="Foreign", type="csv", config={},
            is_active=True,
        )
        db_session.add(foreign)
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            _ds_svc(db_session).delete_datasource(foreign.id)
        assert exc.value.status_code == 404


# ----------------------------------------------------------------- admin guard

def _guarded_client(db_session, role: str):
    app = FastAPI()
    app.include_router(datasources_router.router, prefix="/api/v1/contact-datasources")

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
        r = client.post("/api/v1/contact-datasources", json={"name": "X"})
        assert r.status_code == 403

    def test_member_gets_403_on_delete(self, db_session):
        client = _guarded_client(db_session, role="member")
        r = client.delete(f"/api/v1/contact-datasources/{uuid.uuid4()}")
        assert r.status_code == 403

    def test_member_can_list(self, db_session):
        client = _guarded_client(db_session, role="member")
        r = client.post("/api/v1/contact-datasources/list", json={"page_no": 1, "page_size": 5})
        assert r.status_code == 200
