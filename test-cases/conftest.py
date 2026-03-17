"""Shared fixtures for all API test cases."""

import pytest
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from main import app, api_v1
from core.middleware.auth import JWTClaims, get_jwt_claims, require_org_member, require_admin_or_owner, security
from core.internal.capabilities import is_ee_enabled

try:
    from ee.middleware.auth import (
        get_ee_jwt_claims,
        get_ee_current_user,
        require_ee_org_member,
        require_ee_admin_or_owner,
        require_ee_owner,
    )
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False


def make_claims(
    user_id: int = 1,
    org_id: str = "550e8400-e29b-41d4-a716-446655440000",
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
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    db.delete.return_value = None
    db.count.return_value = 0
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


def _fake_security():
    """Bypass HTTPBearer so tests don't need an Authorization header."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def _override_auth(claims: JWTClaims):
    """Return a dependency override function that returns *claims*."""
    def _override():
        return claims
    return _override


@pytest.fixture
def client_as_member(mock_db, member_claims):
    """TestClient authenticated as a regular org member."""
    from core.database.session import get_db

    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(member_claims)

    if EE_AVAILABLE and is_ee_enabled():
        api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(member_claims)
        api_v1.dependency_overrides[get_ee_current_user] = _override_auth(member_claims)
        api_v1.dependency_overrides[require_ee_org_member] = _override_auth(member_claims)
        api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(member_claims)
        api_v1.dependency_overrides[require_ee_owner] = _override_auth(member_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(mock_db, admin_claims):
    """TestClient authenticated as an admin."""
    from core.database.session import get_db

    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(admin_claims)

    if EE_AVAILABLE and is_ee_enabled():
        api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(admin_claims)
        api_v1.dependency_overrides[get_ee_current_user] = _override_auth(admin_claims)
        api_v1.dependency_overrides[require_ee_org_member] = _override_auth(admin_claims)
        api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(admin_claims)
        api_v1.dependency_overrides[require_ee_owner] = _override_auth(admin_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    """TestClient with DB mocked but NO auth override — auth should reject."""
    from core.database.session import get_db

    api_v1.dependency_overrides[get_db] = lambda: mock_db
    # Remove any leftover auth overrides
    api_v1.dependency_overrides.pop(get_jwt_claims, None)
    api_v1.dependency_overrides.pop(require_org_member, None)
    api_v1.dependency_overrides.pop(require_admin_or_owner, None)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()
