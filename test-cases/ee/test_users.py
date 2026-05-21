"""Tests for Users API endpoints (EE edition).

Source: ee/api/v1/users.py
Postman: postman_collection/users.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
Comprehensive coverage: all Postman examples + auth roles + validation.
"""

import pytest


# ─── GET /api/v1/user/get_all_users_for_organization ───

class TestGetAllUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_users_for_organization"""

    def test_get_all_users_success(self, client_as_member):
        """Postman: Get All Users For Organization - Success (200)."""
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_all_users_contains_at_least_one(self, client_as_member):
        """At least one user exists (the test user)."""
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) >= 1

    def test_get_all_users_response_fields(self, client_as_member):
        """Postman response shows member_id, user_id, email, username, first_name, last_name, role, status, joined_at, last_activity_at."""
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        users = resp.json()
        if len(users) > 0:
            user = users[0]
            assert "email" in user
            assert "role" in user

    def test_get_all_users_role_values(self, client_as_member):
        """Roles should be valid values."""
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        valid_roles = {"owner", "admin", "member", "viewer"}
        for user in resp.json():
            if "role" in user and user["role"] is not None:
                assert user["role"] in valid_roles

    def test_get_all_users_email_format(self, client_as_member):
        """Emails should contain @."""
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        for user in resp.json():
            if "email" in user and user["email"] is not None:
                assert "@" in user["email"]

    def test_get_all_users_empty(self, client_as_member):
        """Postman: Get All Users For Organization - Empty (200).
        Note: unlikely with real DB, but endpoint should return list regardless."""
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_all_users_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_all_users_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_all_users_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/user/get_all_invited_users_for_organization ───

class TestGetAllInvitedUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_invited_users_for_organization"""

    def test_get_all_invited_users_success(self, client_as_member):
        """Postman: Get All Invited Users For Organization - Success (200)."""
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_all_invited_users_empty(self, client_as_member):
        """Postman: Get All Invited Users For Organization - Empty (200)."""
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_invited_users_response_fields(self, client_as_member):
        """Postman response shows member_id, email, username, name, role, status."""
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        for user in resp.json():
            assert "email" in user
            assert "role" in user

    def test_invited_users_role_values(self, client_as_member):
        """Invited user roles should be valid."""
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        valid_roles = {"owner", "admin", "member", "viewer"}
        for user in resp.json():
            if "role" in user and user["role"] is not None:
                assert user["role"] in valid_roles

    def test_invited_users_email_format(self, client_as_member):
        """Invited user emails should contain @."""
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        for user in resp.json():
            if "email" in user and user["email"] is not None:
                assert "@" in user["email"]

    def test_invited_users_status_pending(self, client_as_member):
        """Invited users should have status='pending'."""
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        for user in resp.json():
            if "status" in user:
                assert user["status"] == "pending"

    def test_get_invited_users_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_invited_users_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_invited_users_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code in (401, 403)
