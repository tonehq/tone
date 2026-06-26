"""Core edition test fixtures — uses REAL database and REAL API endpoints.

No mocks. No patched services. Tests hit the actual DB via TestClient.
Auth is handled by generating real JWT tokens using JWTManager.
DB session uses transaction rollback for cleanup after each test.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.config import settings
from main import app, api_v1
from core.database.session import get_db
from core.middleware.auth import JWTManager


# Use the same DB as the app (from .env DATABASE_URL)
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

jwt_mgr = JWTManager()


def _get_real_org_id():
    """Fetch a real organization ID from the DB for tests."""
    from sqlalchemy import text
    conn = engine.connect()
    try:
        row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        return str(row[0]) if row else settings.DEFAULT_ORG_ID
    finally:
        conn.close()


def _get_real_user_id():
    """Fetch a real user ID from the DB for tests."""
    from sqlalchemy import text
    conn = engine.connect()
    try:
        row = conn.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
        return row[0] if row else 1
    finally:
        conn.close()


ORG_ID = _get_real_org_id()
REAL_USER_ID = _get_real_user_id()


@pytest.fixture
def db_session():
    """Per-test real database session with rollback for cleanup."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _make_real_client(db_session, token=None):
    """Build a TestClient with real DB and optional auth token."""
    def _get_test_db():
        yield db_session

    api_v1.dependency_overrides[get_db] = _get_test_db
    client = TestClient(app)
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
        client.headers["tenant_id"] = ORG_ID
    return client


# Use real user IDs that exist in the database
MEMBER_USER_ID = REAL_USER_ID
ADMIN_USER_ID = REAL_USER_ID
OWNER_USER_ID = REAL_USER_ID


@pytest.fixture
def member_token():
    return jwt_mgr.create_access_token(
        user_id=MEMBER_USER_ID, email="member@test.com", org_id=ORG_ID, role="member",
    )


@pytest.fixture
def admin_token():
    return jwt_mgr.create_access_token(
        user_id=ADMIN_USER_ID, email="admin@test.com", org_id=ORG_ID, role="admin",
    )


@pytest.fixture
def owner_token():
    return jwt_mgr.create_access_token(
        user_id=OWNER_USER_ID, email="owner@test.com", org_id=ORG_ID, role="owner",
    )


@pytest.fixture
def client_as_member(db_session, member_token):
    client = _make_real_client(db_session, member_token)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(db_session, admin_token):
    client = _make_real_client(db_session, admin_token)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_owner(db_session, owner_token):
    client = _make_real_client(db_session, owner_token)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(db_session):
    client = _make_real_client(db_session, token=None)
    yield client
    api_v1.dependency_overrides.clear()
