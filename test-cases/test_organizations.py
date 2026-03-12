"""Tests for Organization API endpoints.

Source: core/api/v1/organizations.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── POST /api/v1/organization/invite_user_to_organization ───

class TestInviteUserToOrganization:
    """Tests for POST /api/v1/organization/invite_user_to_organization"""

    @patch("core.api.v1.organizations.AuthService")
    def test_invite_user_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.invite_user_to_organization.return_value = {"message": "invited"}
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User",
            "email": "newuser@example.com",
            "role": "member"
        })
        assert response.status_code == 200

    @patch("core.api.v1.organizations.AuthService")
    def test_invite_user_missing_name(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "email": "newuser@example.com",
            "role": "member"
        })
        assert response.status_code == 400
        assert "Name, email, and role are required" in response.json()["detail"]

    @patch("core.api.v1.organizations.AuthService")
    def test_invite_user_missing_email(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User",
            "role": "member"
        })
        assert response.status_code == 400

    @patch("core.api.v1.organizations.AuthService")
    def test_invite_user_missing_role(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User",
            "email": "newuser@example.com"
        })
        assert response.status_code == 400

    @patch("core.api.v1.organizations.AuthService")
    def test_invite_user_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={})
        assert response.status_code == 400

    def test_invite_user_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Test", "email": "test@example.com", "role": "member"
        })
        assert response.status_code in (401, 403)

    @patch("core.api.v1.organizations.AuthService")
    def test_invite_user_duplicate_email(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.invite_user_to_organization.side_effect = HTTPException(
            status_code=409, detail="User already invited"
        )
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Dup User", "email": "dup@example.com", "role": "member"
        })
        assert response.status_code == 409


# ─── GET /api/v1/organization/accept_invitation ───

class TestAcceptInvitation:
    """Tests for GET /api/v1/organization/accept_invitation"""

    @patch("core.api.v1.organizations.AuthService")
    def test_accept_invitation_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.accept_invitation.return_value = {"message": "accepted"}
        response = client_as_member.get(
            "/api/v1/organization/accept_invitation?email=test@example.com&code=invite-code"
        )
        assert response.status_code == 200

    def test_accept_invitation_missing_email(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/accept_invitation?code=invite-code")
        assert response.status_code == 422

    def test_accept_invitation_missing_code(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/accept_invitation?email=test@example.com")
        assert response.status_code == 422

    @patch("core.api.v1.organizations.AuthService")
    def test_accept_invitation_invalid_code(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.accept_invitation.side_effect = HTTPException(
            status_code=400, detail="Invalid invitation code"
        )
        response = client_as_member.get(
            "/api/v1/organization/accept_invitation?email=test@example.com&code=bad-code"
        )
        assert response.status_code == 400


# ─── DELETE /api/v1/organization/remove_user_from_organization ───

class TestRemoveUserFromOrganization:
    """Tests for DELETE /api/v1/organization/remove_user_from_organization"""

    @patch("core.api.v1.organizations.AuthService")
    def test_remove_user_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.remove_user_from_organization.return_value = {"message": "removed"}
        response = client_as_admin.delete("/api/v1/organization/remove_user_from_organization?user_id=2")
        assert response.status_code == 200

    def test_remove_user_missing_user_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/organization/remove_user_from_organization")
        assert response.status_code == 422

    def test_remove_user_invalid_user_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/organization/remove_user_from_organization?user_id=abc")
        assert response.status_code == 422

    def test_remove_user_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/organization/remove_user_from_organization?user_id=2")
        assert response.status_code in (401, 403)

    @patch("core.api.v1.organizations.AuthService")
    def test_remove_user_not_found(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.remove_user_from_organization.side_effect = HTTPException(
            status_code=404, detail="User not found"
        )
        response = client_as_admin.delete("/api/v1/organization/remove_user_from_organization?user_id=999")
        assert response.status_code == 404


# ─── POST /api/v1/organization/update_member_role ───

class TestUpdateMemberRole:
    """Tests for POST /api/v1/organization/update_member_role"""

    @patch("core.api.v1.organizations.AuthService")
    def test_update_role_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.update_member_role.return_value = {"message": "updated"}
        response = client_as_admin.post("/api/v1/organization/update_member_role?member_id=2&role=admin")
        assert response.status_code == 200

    def test_update_role_missing_member_id(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/update_member_role?role=admin")
        assert response.status_code == 422

    def test_update_role_missing_role(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/update_member_role?member_id=2")
        assert response.status_code == 422

    def test_update_role_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/organization/update_member_role?member_id=2&role=admin")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/settings ───

class TestGetOrganizationSettings:
    """Tests for GET /api/v1/organization/settings"""

    @patch("core.api.v1.organizations.AuthService")
    def test_get_settings_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_organization_settings.return_value = {"timezone": "UTC"}
        response = client_as_member.get("/api/v1/organization/settings")
        assert response.status_code == 200

    def test_get_settings_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/settings")
        assert response.status_code in (401, 403)


# ─── PUT /api/v1/organization/settings ───

class TestUpdateOrganizationSettings:
    """Tests for PUT /api/v1/organization/settings"""

    @patch("core.api.v1.organizations.AuthService")
    def test_update_settings_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.update_organization_settings.return_value = {"message": "updated"}
        response = client_as_admin.put("/api/v1/organization/settings", json={"timezone": "US/Pacific"})
        assert response.status_code == 200

    def test_update_settings_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.put("/api/v1/organization/settings", json={"timezone": "UTC"})
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/access_requests ───

class TestGetAccessRequests:
    """Tests for GET /api/v1/organization/access_requests"""

    @patch("core.api.v1.organizations.AuthService")
    def test_get_access_requests_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.get_access_requests.return_value = []
        response = client_as_admin.get("/api/v1/organization/access_requests")
        assert response.status_code == 200

    def test_get_access_requests_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/access_requests")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/organization/handle_access_request ───

class TestHandleAccessRequest:
    """Tests for POST /api/v1/organization/handle_access_request"""

    @patch("core.api.v1.organizations.AuthService")
    def test_handle_request_approve_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.handle_access_request.return_value = {"message": "approved"}
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "approve"
        })
        assert response.status_code == 200

    @patch("core.api.v1.organizations.AuthService")
    def test_handle_request_reject_success(self, mock_service_cls, client_as_admin):
        mock_service_cls.return_value.handle_access_request.return_value = {"message": "rejected"}
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "reject"
        })
        assert response.status_code == 200

    @patch("core.api.v1.organizations.AuthService")
    def test_handle_request_missing_request_id(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "action": "approve"
        })
        assert response.status_code == 400
        assert "Request ID and action are required" in response.json()["detail"]

    @patch("core.api.v1.organizations.AuthService")
    def test_handle_request_missing_action(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1
        })
        assert response.status_code == 400

    @patch("core.api.v1.organizations.AuthService")
    def test_handle_request_empty_body(self, mock_service_cls, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={})
        assert response.status_code == 400

    def test_handle_request_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "approve"
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/roles ───

class TestGetRoles:
    """Tests for GET /api/v1/organization/roles"""

    @patch("core.api.v1.organizations.AuthService")
    def test_get_roles_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_roles_by_scope.return_value = [
            {"id": 1, "name": "owner"}, {"id": 2, "name": "admin"}, {"id": 3, "name": "member"}
        ]
        response = client_as_member.get("/api/v1/organization/roles")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_roles_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/roles")
        assert response.status_code in (401, 403)
