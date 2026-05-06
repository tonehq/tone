"""Core edition test fixtures."""

import pytest
from fastapi.testclient import TestClient

from main import app, api_v1
from core.middleware.auth import get_jwt_claims, require_org_member, require_admin_or_owner, require_owner, security
from core.database.session import get_db

# EE auth dependencies (loaded when EE is enabled)
try:
    from ee.middleware.auth import (
        get_ee_jwt_claims, require_ee_org_member, require_ee_admin_or_owner,
    )
    _EE_AUTH_AVAILABLE = True
except ImportError:
    _EE_AUTH_AVAILABLE = False

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import time
from unittest.mock import MagicMock
from fastapi.security import HTTPAuthorizationCredentials
from core.middleware.auth import JWTClaims


def make_claims(user_id=1, org_id="550e8400-e29b-41d4-a716-446655440000", role="member", email="test@example.com"):
    now = int(time.time())
    return JWTClaims(user_id=user_id, org_id=org_id, role=role, email=email, iat=now, exp=now + 3600)


def _fake_security():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def _override_auth(claims):
    def _override():
        return claims
    return _override


@pytest.fixture
def mock_db():
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
    return make_claims(role="member")


@pytest.fixture
def admin_claims():
    return make_claims(role="admin")


@pytest.fixture
def owner_claims():
    return make_claims(role="owner")


def _apply_auth_overrides(mock_db, claims):
    """Override both Core and EE auth dependencies."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(claims)
    if _EE_AUTH_AVAILABLE:
        api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(claims)
        api_v1.dependency_overrides[require_ee_org_member] = _override_auth(claims)
        api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(claims)


@pytest.fixture
def client_as_member(mock_db, member_claims):
    _apply_auth_overrides(mock_db, member_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(mock_db, admin_claims):
    _apply_auth_overrides(mock_db, admin_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_owner(mock_db, owner_claims):
    _apply_auth_overrides(mock_db, owner_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides.pop(get_jwt_claims, None)
    api_v1.dependency_overrides.pop(require_org_member, None)
    api_v1.dependency_overrides.pop(require_admin_or_owner, None)
    api_v1.dependency_overrides.pop(require_owner, None)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()
