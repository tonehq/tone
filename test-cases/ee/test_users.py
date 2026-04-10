"""Tests for Users API endpoints (EE edition).

Source: ee/api/v1/users.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# ─── GET /api/v1/user/get_all_users_for_organization ───

class TestGetAllUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_users_for_organization"""

    def test_get_all_users_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_users_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code in (401, 403)

    def test_get_all_users_as_admin(self, client_as_admin):
        response = client_as_admin.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_users_as_owner(self, client_as_owner):
        response = client_as_owner.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_users_contains_at_least_one(self, client_as_member):
        """At least one user exists (the test user)."""
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 1

    def test_get_all_users_response_fields(self, client_as_member):
        """Verify user records contain expected fields."""
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        users = response.json()
        if len(users) > 0:
            user = users[0]
            assert "email" in user
            assert "role" in user

    def test_get_all_users_role_values(self, client_as_member):
        """Roles should be valid values."""
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        valid_roles = {"owner", "admin", "member", "viewer"}
        for user in response.json():
            if "role" in user and user["role"] is not None:
                assert user["role"] in valid_roles

    def test_get_all_users_email_format(self, client_as_member):
        """Emails should contain @."""
        response = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert response.status_code == 200
        for user in response.json():
            if "email" in user and user["email"] is not None:
                assert "@" in user["email"]


# ─── GET /api/v1/user/get_all_invited_users_for_organization ───

class TestGetAllInvitedUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_invited_users_for_organization"""

    def test_get_all_invited_users_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_invited_users_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code in (401, 403)

    def test_get_invited_users_as_admin(self, client_as_admin):
        response = client_as_admin.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_invited_users_as_owner(self, client_as_owner):
        response = client_as_owner.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_invited_users_role_values(self, client_as_member):
        """Invited user roles should be valid."""
        response = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        valid_roles = {"owner", "admin", "member", "viewer"}
        for user in response.json():
            if "role" in user and user["role"] is not None:
                assert user["role"] in valid_roles

    def test_invited_users_email_format(self, client_as_member):
        """Invited user emails should contain @."""
        response = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert response.status_code == 200
        for user in response.json():
            if "email" in user and user["email"] is not None:
                assert "@" in user["email"]
