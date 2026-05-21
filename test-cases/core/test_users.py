"""Tests for Users API endpoints (Core edition).

Source: core/api/v1/users.py
Postman collection: postman_collection/users.postman_collection.json
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
        {
            "member_id": 1,
            "user_id": 1,
            "email": "owner@example.com",
            "username": "owner",
            "first_name": "John",
            "last_name": "Doe",
            "role": "owner",
            "status": "active",
            "joined_at": 1710201600,
            "last_activity_at": 1710288000,
        },
        {
            "member_id": 2,
            "user_id": 2,
            "email": "admin@example.com",
            "username": "admin1",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "admin",
            "status": "active",
            "joined_at": 1710288000,
            "last_activity_at": 1710374400,
        },
        {
            "member_id": 3,
            "user_id": 3,
            "email": "member@example.com",
            "username": "member1",
            "first_name": "Alice",
            "last_name": "Johnson",
            "role": "member",
            "status": "active",
            "joined_at": 1710374400,
            "last_activity_at": 1710460800,
        },
        {
            "member_id": 4,
            "user_id": 4,
            "email": "viewer@example.com",
            "username": "viewer1",
            "first_name": "Bob",
            "last_name": "Williams",
            "role": "viewer",
            "status": "active",
            "joined_at": 1710460800,
            "last_activity_at": None,
        },
    ]


@pytest.fixture
def sample_invited_users():
    return [
        {
            "member_id": 5,
            "email": "invited_admin@example.com",
            "username": "Sarah Admin",
            "name": "Sarah Admin",
            "role": "admin",
            "status": "pending",
        },
        {
            "member_id": 6,
            "email": "invited_member@example.com",
            "username": "Tom Member",
            "name": "Tom Member",
            "role": "member",
            "status": "pending",
        },
        {
            "member_id": 7,
            "email": "invited_viewer@example.com",
            "username": "Lisa Viewer",
            "name": "Lisa Viewer",
            "role": "viewer",
            "status": "pending",
        },
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/user/get_all_users_for_organization
# ---------------------------------------------------------------------------

class TestGetAllUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_users_for_organization"""

    @patch("ee.api.v1.users.AuthService")
    def test_get_all_users_success(self, mock_service_cls, client_as_member, sample_users):
        """Postman: Get All Users For Organization - Success (200)"""
        mock_service_cls.return_value.get_all_users_for_organization.return_value = sample_users
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        assert data[0]["role"] == "owner"
        assert data[1]["role"] == "admin"
        assert data[2]["role"] == "member"
        assert data[3]["role"] == "viewer"

    @patch("ee.api.v1.users.AuthService")
    def test_get_all_users_empty(self, mock_service_cls, client_as_member):
        """Postman: Get All Users For Organization - Empty (200)"""
        mock_service_cls.return_value.get_all_users_for_organization.return_value = []
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_all_users_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.users.AuthService")
    def test_get_all_users_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_users_for_organization.side_effect = Exception(
            "DB error"
        )
        resp = client_as_member.get("/api/v1/user/get_all_users_for_organization")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/user/get_all_invited_users_for_organization
# ---------------------------------------------------------------------------

class TestGetAllInvitedUsersForOrganization:
    """Tests for GET /api/v1/user/get_all_invited_users_for_organization"""

    @patch("ee.api.v1.users.AuthService")
    def test_get_all_invited_users_success(self, mock_service_cls, client_as_member, sample_invited_users):
        """Postman: Get All Invited Users For Organization - Success (200)"""
        mock_service_cls.return_value.get_all_invited_users_for_organization.return_value = (
            sample_invited_users
        )
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["status"] == "pending"
        assert data[0]["role"] == "admin"
        assert data[1]["role"] == "member"
        assert data[2]["role"] == "viewer"

    @patch("ee.api.v1.users.AuthService")
    def test_get_all_invited_users_empty(self, mock_service_cls, client_as_member):
        """Postman: Get All Invited Users For Organization - Empty (200)"""
        mock_service_cls.return_value.get_all_invited_users_for_organization.return_value = []
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_all_invited_users_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.users.AuthService")
    def test_get_all_invited_users_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_invited_users_for_organization.side_effect = (
            Exception("DB error")
        )
        resp = client_as_member.get("/api/v1/user/get_all_invited_users_for_organization")
        assert resp.status_code in (500, 422, 400)
