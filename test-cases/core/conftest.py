"""Core edition test fixtures."""

import pytest
from fastapi.testclient import TestClient

from main import app, api_v1
from core.middleware.auth import get_jwt_claims, require_org_member, require_admin_or_owner, require_owner, security
from core.database.session import get_db

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conftest import _fake_security, _override_auth


@pytest.fixture
def client_as_member(mock_db, member_claims):
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(member_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(mock_db, admin_claims):
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(admin_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_owner(mock_db, owner_claims):
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(owner_claims)
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
