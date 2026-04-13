"""Integration test fixtures — uses REAL database and REAL API endpoints.

No mocks. No patched services. Tests hit the actual DB via TestClient.
Auth is handled by generating real JWT tokens using JWTManager.
"""

import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from shared.config import settings
from core.middleware.auth import JWTManager
from core.database.session import get_db

# Use the same DB as the app (from .env DATABASE_URL)
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped real database engine."""
    return engine


@pytest.fixture
def db_session(db_engine):
    """Per-test real database session with rollback for cleanup."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def real_client(db_session):
    """TestClient that uses real DB session (rolled back after each test)."""
    from main import app, api_v1

    def _get_test_db():
        yield db_session

    api_v1.dependency_overrides[get_db] = _get_test_db
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def jwt_manager():
    """Real JWTManager instance for creating valid tokens."""
    return JWTManager()


@pytest.fixture
def auth_token_member(jwt_manager):
    """Generate a real JWT token for a member user."""
    token = jwt_manager.create_access_token(
        user_id=1,
        email="test-member@example.com",
        org_id=settings.DEFAULT_ORG_ID,
        role="member",
    )
    return token


@pytest.fixture
def auth_token_admin(jwt_manager):
    """Generate a real JWT token for an admin user."""
    token = jwt_manager.create_access_token(
        user_id=2,
        email="test-admin@example.com",
        org_id=settings.DEFAULT_ORG_ID,
        role="admin",
    )
    return token


@pytest.fixture
def auth_token_owner(jwt_manager):
    """Generate a real JWT token for an owner user."""
    token = jwt_manager.create_access_token(
        user_id=3,
        email="test-owner@example.com",
        org_id=settings.DEFAULT_ORG_ID,
        role="owner",
    )
    return token


@pytest.fixture
def member_headers(auth_token_member):
    """Auth headers for a member user."""
    return {"Authorization": f"Bearer {auth_token_member}"}


@pytest.fixture
def admin_headers(auth_token_admin):
    """Auth headers for an admin user."""
    return {"Authorization": f"Bearer {auth_token_admin}"}


@pytest.fixture
def owner_headers(auth_token_owner):
    """Auth headers for an owner user."""
    return {"Authorization": f"Bearer {auth_token_owner}"}
