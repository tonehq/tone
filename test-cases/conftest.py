"""Shared fixtures for all API test cases (Core and EE)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import time
from unittest.mock import MagicMock
from fastapi.security import HTTPAuthorizationCredentials

from core.middleware.auth import JWTClaims


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
    return make_claims(role="member")


@pytest.fixture
def admin_claims():
    return make_claims(role="admin")


@pytest.fixture
def owner_claims():
    return make_claims(role="owner")


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


def _fake_security():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def _override_auth(claims: JWTClaims):
    def _override():
        return claims
    return _override
