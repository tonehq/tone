"""Shared fixtures for all API test cases."""

import pytest
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from main import app
from core.middleware.auth import JWTClaims, get_jwt_claims, require_org_member, require_admin_or_owner, security


def make_claims(
    user_id: int = 1,
    org_id: int = 1,
    role: str = "member",
    email: str = "test@example.com",
) -> JWTClaims:
    """Build a JWTClaims instance with sensible defaults."""
    now = int(time.time())
    return JWTClaims(
        user_id=user_id,
        org_id=org_id,
        role=role,
        email=email,
        iat=now,
        exp=now + 3600,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=Session)
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    db.delete.return_value = None
    return db


@pytest.fixture
def member_claims():
    """JWT claims for a regular org member."""
    return make_claims(role="member")


@pytest.fixture
def admin_claims():
    """JWT claims for an admin user."""
    return make_claims(role="admin")


@pytest.fixture
def owner_claims():
    """JWT claims for an owner user."""
    return make_claims(role="owner")


@pytest.fixture
def auth_headers():
    """Bearer token headers for authenticated requests."""
    return {"Authorization": "Bearer test-token"}


def _override_auth(claims: JWTClaims):
    """Return a dependency override function that returns *claims*."""
    def _override():
        return claims
    return _override


@pytest.fixture
def client_as_member(mock_db, member_claims):
    """TestClient authenticated as a regular org member."""
    from core.database.session import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_jwt_claims] = _override_auth(member_claims)
    app.dependency_overrides[require_org_member] = _override_auth(member_claims)
    app.dependency_overrides[require_admin_or_owner] = _override_auth(member_claims)

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(mock_db, admin_claims):
    """TestClient authenticated as an admin."""
    from core.database.session import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_jwt_claims] = _override_auth(admin_claims)
    app.dependency_overrides[require_org_member] = _override_auth(admin_claims)
    app.dependency_overrides[require_admin_or_owner] = _override_auth(admin_claims)

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    """TestClient with DB mocked but NO auth override — auth should reject."""
    from core.database.session import get_db

    app.dependency_overrides[get_db] = lambda: mock_db
    # Remove any leftover auth overrides
    app.dependency_overrides.pop(get_jwt_claims, None)
    app.dependency_overrides.pop(require_org_member, None)
    app.dependency_overrides.pop(require_admin_or_owner, None)

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
