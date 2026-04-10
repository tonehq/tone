"""Tests for Organizations API endpoints (Core edition).

Source: core/api/v1/organizations.py
IMPORTANT: Core edition uses AuthService (NOT EEAuthService).
Core has member limit checks (CORE_MAX_MEMBERS=3) and capability guards.
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/organization/invite_user_to_organization
# ---------------------------------------------------------------------------
class TestInviteUserToOrganization:
    @patch("core.api.v1.organizations.check_member_limit")
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, mock_check_limit, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.invite_user_to_organization.return_value = {
            "message": "Invitation sent"
        }
        mock_service_cls.return_value = mock_instance
        mock_check_limit.return_value = None

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "email": "jane@example.com", "role": "member"},
        )

        assert resp.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.invite_user_to_organization.assert_called_once_with(
            "Jane Doe", "jane@example.com", "member", ANY
        )

    @patch("core.api.v1.organizations.check_member_limit")
    @patch("core.api.v1.organizations.AuthService")
    def test_missing_name(self, mock_service_cls, mock_check_limit, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"email": "jane@example.com", "role": "member"},
        )
        assert resp.status_code == 400
        assert "Name" in resp.json()["detail"]

    @patch("core.api.v1.organizations.check_member_limit")
    @patch("core.api.v1.organizations.AuthService")
    def test_missing_email(self, mock_service_cls, mock_check_limit, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "role": "member"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.organizations.check_member_limit")
    @patch("core.api.v1.organizations.AuthService")
    def test_missing_role(self, mock_service_cls, mock_check_limit, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "email": "jane@example.com"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.organizations.check_member_limit")
    @patch("core.api.v1.organizations.AuthService")
    def test_member_limit_reached(
        self, mock_service_cls, mock_check_limit, client_as_admin
    ):
        mock_check_limit.side_effect = HTTPException(
            status_code=403,
            detail="Member limit reached. Core edition allows up to 3 members. Upgrade to Enterprise for more.",
        )

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "email": "jane@example.com", "role": "member"},
        )

        assert resp.status_code == 403
        assert "Member limit" in resp.json()["detail"]

    @patch("core.api.v1.organizations.check_member_limit")
    @patch("core.api.v1.organizations.AuthService")
    def test_service_error(self, mock_service_cls, mock_check_limit, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.invite_user_to_organization.side_effect = HTTPException(
            status_code=409, detail="User already invited"
        )
        mock_service_cls.return_value = mock_instance
        mock_check_limit.return_value = None

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "email": "jane@example.com", "role": "member"},
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/v1/organization/accept_invitation
# ---------------------------------------------------------------------------
class TestAcceptInvitation:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.accept_invitation.return_value = {"message": "Accepted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "jane@example.com", "code": "abc123"},
        )

        assert resp.status_code == 200
        mock_instance.accept_invitation.assert_called_once_with(
            "jane@example.com", "abc123"
        )

    @patch("core.api.v1.organizations.AuthService")
    def test_invalid_code(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.accept_invitation.side_effect = HTTPException(
            status_code=400, detail="Invalid invitation code"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "jane@example.com", "code": "bad"},
        )
        assert resp.status_code == 400

    def test_missing_email(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation", params={"code": "abc123"}
        )
        assert resp.status_code == 422

    def test_missing_code(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "jane@example.com"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/organization/validate_invitation
# ---------------------------------------------------------------------------
class TestValidateInvitation:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.validate_invitation_token.return_value = {"valid": True}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation",
            params={"email": "jane@example.com", "code": "abc123"},
        )

        assert resp.status_code == 200
        mock_instance.validate_invitation_token.assert_called_once_with(
            "jane@example.com", "abc123"
        )

    @patch("core.api.v1.organizations.AuthService")
    def test_invalid_token(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.validate_invitation_token.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired token"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation",
            params={"email": "jane@example.com", "code": "expired"},
        )
        assert resp.status_code == 400

    def test_missing_email(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation", params={"code": "abc123"}
        )
        assert resp.status_code == 422

    def test_missing_code(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation",
            params={"email": "jane@example.com"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/organization/accept_invitation_with_password
# ---------------------------------------------------------------------------
class TestAcceptInvitationWithPassword:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.accept_invitation_with_password.return_value = {
            "message": "Account created"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "jane@example.com",
                "code": "abc123",
                "password": "securepass",
            },
        )

        assert resp.status_code == 200
        mock_instance.accept_invitation_with_password.assert_called_once_with(
            "jane@example.com", "abc123", "securepass"
        )

    @patch("core.api.v1.organizations.AuthService")
    def test_missing_email(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"code": "abc123", "password": "securepass"},
        )
        assert resp.status_code == 400
        assert "Email" in resp.json()["detail"]

    @patch("core.api.v1.organizations.AuthService")
    def test_missing_code(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"email": "jane@example.com", "password": "securepass"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.organizations.AuthService")
    def test_missing_password(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"email": "jane@example.com", "code": "abc123"},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.organizations.AuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.accept_invitation_with_password.side_effect = HTTPException(
            status_code=400, detail="Invalid invitation"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "jane@example.com",
                "code": "bad",
                "password": "securepass",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/organization/cancel_invitation
# ---------------------------------------------------------------------------
class TestCancelInvitation:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.cancel_invitation.return_value = {"message": "Cancelled"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/cancel_invitation", params={"invite_id": 5}
        )

        assert resp.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.cancel_invitation.assert_called_once_with(5)

    @patch("core.api.v1.organizations.AuthService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.cancel_invitation.side_effect = HTTPException(
            status_code=404, detail="Invitation not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/cancel_invitation", params={"invite_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_invite_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/organization/cancel_invitation")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/organization/remove_user_from_organization
# ---------------------------------------------------------------------------
class TestRemoveUserFromOrganization:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.remove_user_from_organization.return_value = {
            "message": "Removed"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization",
            params={"user_id": 42},
        )

        assert resp.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.remove_user_from_organization.assert_called_once_with(42)

    @patch("core.api.v1.organizations.AuthService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.remove_user_from_organization.side_effect = HTTPException(
            status_code=404, detail="User not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization",
            params={"user_id": 999},
        )
        assert resp.status_code == 404

    def test_missing_user_id(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization"
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/organization/update_member_role
# ---------------------------------------------------------------------------
class TestUpdateMemberRole:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.update_member_role.return_value = {"message": "Role updated"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 7, "role": "admin"},
        )

        assert resp.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.update_member_role.assert_called_once_with(7, "admin")

    @patch("core.api.v1.organizations.AuthService")
    def test_not_found(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.update_member_role.side_effect = HTTPException(
            status_code=404, detail="Member not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 999, "role": "admin"},
        )
        assert resp.status_code == 404

    def test_missing_member_id(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role", params={"role": "admin"}
        )
        assert resp.status_code == 422

    def test_missing_role(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role", params={"member_id": 7}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/organization/settings
# ---------------------------------------------------------------------------
class TestGetOrganizationSettings:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_organization_settings.return_value = {
            "name": "My Org",
            "settings": {},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/settings")

        assert resp.status_code == 200
        assert resp.json()["name"] == "My Org"
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.get_organization_settings.assert_called_once()

    @patch("core.api.v1.organizations.AuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_organization_settings.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/settings")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# PUT /api/v1/organization/settings
# ---------------------------------------------------------------------------
class TestUpdateOrganizationSettings:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.update_organization_settings.return_value = {
            "message": "Updated"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.put(
            "/api/v1/organization/settings",
            json={"name": "New Org Name", "logo_url": "https://example.com/logo.png"},
        )

        assert resp.status_code == 200
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.update_organization_settings.assert_called_once_with(
            {"name": "New Org Name", "logo_url": "https://example.com/logo.png"}
        )

    @patch("core.api.v1.organizations.AuthService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.update_organization_settings.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.put(
            "/api/v1/organization/settings",
            json={"name": "Fail"},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/organization/access_requests
# ---------------------------------------------------------------------------
class TestGetAccessRequests:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.get_access_requests.return_value = [
            {"id": 1, "email": "requester@example.com"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.get("/api/v1/organization/access_requests")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.get_access_requests.assert_called_once()

    @patch("core.api.v1.organizations.AuthService")
    def test_empty_list(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.get_access_requests.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.get("/api/v1/organization/access_requests")

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/v1/organization/handle_access_request
# ---------------------------------------------------------------------------
class TestHandleAccessRequest:
    @patch("core.api.v1.organizations.AuthService")
    def test_success_approve(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.handle_access_request.return_value = {"message": "Approved"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1, "action": "approve"},
        )

        assert resp.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, user_id=ANY)
        mock_instance.handle_access_request.assert_called_once_with(1, "approve", ANY)

    @patch("core.api.v1.organizations.AuthService")
    def test_success_reject(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.handle_access_request.return_value = {"message": "Rejected"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 2, "action": "reject"},
        )

        assert resp.status_code == 200
        mock_instance.handle_access_request.assert_called_once_with(2, "reject", ANY)

    @patch("core.api.v1.organizations.AuthService")
    def test_missing_request_id(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"action": "approve"},
        )
        assert resp.status_code == 400
        assert "Request ID" in resp.json()["detail"]

    @patch("core.api.v1.organizations.AuthService")
    def test_missing_action(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1},
        )
        assert resp.status_code == 400

    @patch("core.api.v1.organizations.AuthService")
    def test_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.handle_access_request.side_effect = HTTPException(
            status_code=404, detail="Request not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 999, "action": "approve"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/organization/roles
# ---------------------------------------------------------------------------
class TestGetRoles:
    @patch("core.api.v1.organizations.AuthService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_roles_by_scope.return_value = [
            {"name": "owner"},
            {"name": "admin"},
            {"name": "member"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/roles")

        assert resp.status_code == 200
        assert len(resp.json()) == 3
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.get_roles_by_scope.assert_called_once()

    @patch("core.api.v1.organizations.AuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_roles_by_scope.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/roles")
        assert resp.status_code == 500
