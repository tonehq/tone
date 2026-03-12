"""Tests for Users API endpoints.

Source: core/api/v1/users.py
"""

import pytest
from unittest.mock import patch, MagicMock


# ─── GET /api/v1/user/get_all_users_for_organization ───

class TestGetAllUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_users_for_organization"""

    @patch("core.api.v1.users.AuthService")
    def test_get_all_users_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_users_for_organization.return_value = [
            {"id": 1, "email": "user1@example.com"},
            {"id": 2, "email": "user2@example.com"},
        ]
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.users.AuthService")
    def test_get_all_users_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_users_for_organization.return_value = []
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_users_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/user/get_all_invited_users_for_organization ───

class TestGetAllInvitedUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_invited_users_for_organization"""

    @patch("core.api.v1.users.AuthService")
    def test_get_all_invited_users_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_invited_users_for_organization.return_value = [
            {"id": 1, "email": "invited@example.com", "status": "pending"}
        ]
        response = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.users.AuthService")
    def test_get_all_invited_users_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_invited_users_for_organization.return_value = []
        response = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_invited_users_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code in (401, 403)
