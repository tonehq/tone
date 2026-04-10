"""Tests for Users API endpoints (Core edition).

Source: core/api/v1/users.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_users():
    return [
        {"id": 1, "email": "alice@example.com", "username": "alice", "role": "member"},
        {"id": 2, "email": "bob@example.com", "username": "bob", "role": "admin"},
    ]


@pytest.fixture
def sample_invited_users():
    return [
        {"id": 3, "email": "charlie@example.com", "status": "invited"},
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/user/get_all_users_for_organization
# ---------------------------------------------------------------------------

class TestGetAllUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_users_for_organization"""

    @patch("core.api.v1.users.AuthService")
    def test_success(self, mock_service_cls, client_as_member, sample_users):
        mock_service_cls.return_value.get_all_users_for_organization.return_value = sample_users
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("core.api.v1.users.AuthService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_users_for_organization.return_value = []
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.users.AuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_users_for_organization.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/user/get_all_invited_users_for_organization
# ---------------------------------------------------------------------------

class TestGetAllInvitedUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_invited_users_for_organization"""

    @patch("core.api.v1.users.AuthService")
    def test_success(self, mock_service_cls, client_as_member, sample_invited_users):
        mock_service_cls.return_value.get_all_invited_users_for_organization.return_value = (
            sample_invited_users
        )
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("core.api.v1.users.AuthService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_invited_users_for_organization.return_value = []
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.users.AuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_invited_users_for_organization.side_effect = (
            Exception("DB error")
        )
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 500
