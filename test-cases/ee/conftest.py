"""EE edition test fixtures."""

import pytest
from fastapi.testclient import TestClient

from main import app, api_v1
from ee.middleware.auth import (
    get_ee_jwt_claims,
    get_ee_current_user,
    require_ee_org_member,
    require_ee_admin_or_owner,
    require_ee_owner,
)
from core.middleware.auth import security
from core.database.session import get_db

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conftest import _fake_security, _override_auth


@pytest.fixture
def client_as_member(mock_db, member_claims):
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
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
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(admin_claims)
    api_v1.dependency_overrides[get_ee_current_user] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_ee_org_member] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_ee_owner] = _override_auth(admin_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_owner(mock_db, owner_claims):
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(owner_claims)
    api_v1.dependency_overrides[get_ee_current_user] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_ee_org_member] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_ee_owner] = _override_auth(owner_claims)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides.pop(get_ee_jwt_claims, None)
    api_v1.dependency_overrides.pop(get_ee_current_user, None)
    api_v1.dependency_overrides.pop(require_ee_org_member, None)
    api_v1.dependency_overrides.pop(require_ee_admin_or_owner, None)
    api_v1.dependency_overrides.pop(require_ee_owner, None)
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()
