"""Tests for Organizations API endpoints (Core edition).

Source: core/api/v1/organizations.py
Postman collection: postman_collection/organizations.postman_collection.json
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
    """Tests for POST /api/v1/organization/invite_user_to_organization"""

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_success(self, mock_service_cls, mock_check_limit, client_as_admin):
        """Postman: Invite User To Organization - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.invite_user_to_organization.return_value = {
            "id": 1,
            "email": "jane@example.com",
            "role": "member",
            "status": "pending",
            "expires_at": 1710806400,
        }
        mock_service_cls.return_value = mock_instance
        mock_check_limit.return_value = None

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Smith", "email": "jane@example.com", "role": "member"},
        )

        assert resp.status_code == 200
        mock_instance.invite_user_to_organization.assert_called_once_with(
            "Jane Smith", "jane@example.com", "member", ANY
        )

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_missing_fields(self, mock_service_cls, mock_check_limit, client_as_admin):
        """Postman: Invite User To Organization - Missing Fields (400)"""
        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"email": "jane@example.com"},
        )
        assert resp.status_code == 400
        assert "Name" in resp.json()["detail"] or "required" in resp.json()["detail"]

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_missing_email(self, mock_service_cls, mock_check_limit, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "role": "member"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_missing_role(self, mock_service_cls, mock_check_limit, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Doe", "email": "jane@example.com"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_invalid_role(self, mock_service_cls, mock_check_limit, client_as_admin):
        """Postman: Invite User To Organization - Invalid Role (400)"""
        mock_instance = MagicMock()
        mock_instance.invite_user_to_organization.side_effect = HTTPException(
            status_code=400, detail="Invalid role"
        )
        mock_service_cls.return_value = mock_instance
        mock_check_limit.return_value = None

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Smith", "email": "jane@example.com", "role": "superadmin"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid role"

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_already_a_member(self, mock_service_cls, mock_check_limit, client_as_admin):
        """Postman: Invite User To Organization - Already A Member (400)"""
        mock_instance = MagicMock()
        mock_instance.invite_user_to_organization.side_effect = HTTPException(
            status_code=400, detail="User is already a member of the organization"
        )
        mock_service_cls.return_value = mock_instance
        mock_check_limit.return_value = None

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Existing User", "email": "existing@example.com", "role": "member"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "User is already a member of the organization"

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_pending_invitation_exists(self, mock_service_cls, mock_check_limit, client_as_admin):
        """Postman: Invite User To Organization - Pending Invitation Exists (400)"""
        mock_instance = MagicMock()
        mock_instance.invite_user_to_organization.side_effect = HTTPException(
            status_code=400, detail="Pending invitation already exists"
        )
        mock_service_cls.return_value = mock_instance
        mock_check_limit.return_value = None

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Smith", "email": "pending@example.com", "role": "member"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Pending invitation already exists"

    @patch("ee.api.v1.organizations.check_member_limit")
    @patch("ee.api.v1.organizations.AuthService")
    def test_invite_member_limit_reached(self, mock_service_cls, mock_check_limit, client_as_admin):
        """Postman: Invite User To Organization - Member Limit Reached (403)"""
        mock_check_limit.side_effect = HTTPException(
            status_code=403,
            detail="Member limit reached. Core edition allows up to 3 members. Upgrade to Enterprise for more.",
        )

        resp = client_as_admin.post(
            "/api/v1/organization/invite_user_to_organization",
            json={"name": "Jane Smith", "email": "jane@example.com", "role": "member"},
        )

        assert resp.status_code == 403
        assert "Member limit" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/organization/accept_invitation
# ---------------------------------------------------------------------------
class TestAcceptInvitation:
    """Tests for GET /api/v1/organization/accept_invitation"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_invitation_success(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation.return_value = {
            "message": "Invitation accepted successfully",
            "role": "member",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "jane@example.com", "code": "invite-token-here"},
        )

        assert resp.status_code == 200
        mock_instance.accept_invitation.assert_called_once_with(
            "jane@example.com", "invite-token-here"
        )

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_invitation_invalid_or_expired(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation - Invalid Or Expired (400)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired invitation"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "jane@example.com", "code": "invalid-token"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired invitation"

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_invitation_user_not_signed_up(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation - User Not Signed Up (400)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation.side_effect = HTTPException(
            status_code=400, detail="Please sign up first before accepting the invitation"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "nosignup@example.com", "code": "invite-token-here"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Please sign up first before accepting the invitation"

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_invitation_already_a_member(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation - Already A Member (400)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation.side_effect = HTTPException(
            status_code=400, detail="You are already a member"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "existing@example.com", "code": "invite-token-here"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "You are already a member"

    def test_accept_invitation_missing_email(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation", params={"code": "abc123"}
        )
        assert resp.status_code == 422

    def test_accept_invitation_missing_code(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/accept_invitation",
            params={"email": "jane@example.com"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/organization/validate_invitation
# ---------------------------------------------------------------------------
class TestValidateInvitation:
    """Tests for GET /api/v1/organization/validate_invitation"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_validate_invitation_valid(self, mock_service_cls, client_as_member):
        """Postman: Validate Invitation - Valid (200)"""
        mock_instance = MagicMock()
        mock_instance.validate_invitation_token.return_value = {
            "valid": True,
            "email": "jane@example.com",
            "name": "Jane Smith",
            "role": "member",
            "user_exists": True,
            "has_password": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation",
            params={"email": "jane@example.com", "code": "invite-token-here"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        mock_instance.validate_invitation_token.assert_called_once_with(
            "jane@example.com", "invite-token-here"
        )

    @patch("ee.api.v1.organizations.AuthService")
    def test_validate_invitation_invalid_or_expired(self, mock_service_cls, client_as_member):
        """Postman: Validate Invitation - Invalid Or Expired (400)"""
        mock_instance = MagicMock()
        mock_instance.validate_invitation_token.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired invitation"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation",
            params={"email": "jane@example.com", "code": "bad-token"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired invitation"

    def test_validate_invitation_missing_email(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation", params={"code": "abc123"}
        )
        assert resp.status_code == 422

    def test_validate_invitation_missing_code(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/organization/validate_invitation",
            params={"email": "jane@example.com"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/organization/accept_invitation_with_password
# ---------------------------------------------------------------------------
class TestAcceptInvitationWithPassword:
    """Tests for POST /api/v1/organization/accept_invitation_with_password"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_with_password_success(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation With Password - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation_with_password.return_value = {
            "message": "Account created and invitation accepted successfully",
            "role": "member",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "jane@example.com",
                "code": "invite-token-here",
                "password": "securePassword123",
            },
        )

        assert resp.status_code == 200
        mock_instance.accept_invitation_with_password.assert_called_once_with(
            "jane@example.com", "invite-token-here", "securePassword123"
        )

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_with_password_missing_fields(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation With Password - Missing Fields (400)"""
        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"email": "jane@example.com"},
        )
        assert resp.status_code == 400
        assert "Email" in resp.json()["detail"] or "required" in resp.json()["detail"]

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_with_password_missing_code(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"email": "jane@example.com", "password": "securepass"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_with_password_missing_password(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"email": "jane@example.com", "code": "abc123"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_with_password_invalid_or_expired(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation With Password - Invalid Or Expired (400)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation_with_password.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired invitation"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "jane@example.com",
                "code": "invalid-token",
                "password": "securePassword123",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired invitation"

    @patch("ee.api.v1.organizations.AuthService")
    def test_accept_with_password_user_already_has_password(self, mock_service_cls, client_as_member):
        """Postman: Accept Invitation With Password - User Already Has Password (400)"""
        mock_instance = MagicMock()
        mock_instance.accept_invitation_with_password.side_effect = HTTPException(
            status_code=400, detail="User already exists. Please login and accept the invitation."
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "existing@example.com",
                "code": "invite-token-here",
                "password": "securePassword123",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "User already exists. Please login and accept the invitation."


# ---------------------------------------------------------------------------
# DELETE /api/v1/organization/cancel_invitation
# ---------------------------------------------------------------------------
class TestCancelInvitation:
    """Tests for DELETE /api/v1/organization/cancel_invitation"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_cancel_invitation_success(self, mock_service_cls, client_as_admin):
        """Postman: Cancel Invitation - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.cancel_invitation.return_value = {
            "message": "Invitation cancelled successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/cancel_invitation", params={"invite_id": 1}
        )

        assert resp.status_code == 200
        mock_instance.cancel_invitation.assert_called_once_with(1)

    @patch("ee.api.v1.organizations.AuthService")
    def test_cancel_invitation_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Cancel Invitation - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.cancel_invitation.side_effect = HTTPException(
            status_code=404, detail="Pending invitation not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/cancel_invitation", params={"invite_id": 9999}
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Pending invitation not found"

    def test_cancel_invitation_missing_invite_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/organization/cancel_invitation")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/organization/remove_user_from_organization
# ---------------------------------------------------------------------------
class TestRemoveUserFromOrganization:
    """Tests for DELETE /api/v1/organization/remove_user_from_organization"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_remove_user_success(self, mock_service_cls, client_as_admin):
        """Postman: Remove User From Organization - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.remove_user_from_organization.return_value = {
            "message": "Member removed successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization",
            params={"user_id": 3},
        )

        assert resp.status_code == 200
        mock_instance.remove_user_from_organization.assert_called_once_with(3)

    @patch("ee.api.v1.organizations.AuthService")
    def test_remove_user_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Remove User From Organization - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.remove_user_from_organization.side_effect = HTTPException(
            status_code=404, detail="Member not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization",
            params={"user_id": 9999},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Member not found"

    @patch("ee.api.v1.organizations.AuthService")
    def test_remove_user_cannot_remove_last_owner(self, mock_service_cls, client_as_admin):
        """Postman: Remove User From Organization - Cannot Remove Last Owner (400)"""
        mock_instance = MagicMock()
        mock_instance.remove_user_from_organization.side_effect = HTTPException(
            status_code=400, detail="Cannot remove the last owner"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization",
            params={"user_id": 1},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Cannot remove the last owner"

    def test_remove_user_missing_user_id(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization"
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/organization/update_member_role
# ---------------------------------------------------------------------------
class TestUpdateMemberRole:
    """Tests for POST /api/v1/organization/update_member_role"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_member_role_success(self, mock_service_cls, client_as_admin):
        """Postman: Update Member Role - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.update_member_role.return_value = {
            "member_id": 2,
            "role": "admin",
            "message": "Role updated successfully",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 2, "role": "admin"},
        )

        assert resp.status_code == 200
        mock_instance.update_member_role.assert_called_once_with(2, "admin")

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_member_role_invalid_role(self, mock_service_cls, client_as_admin):
        """Postman: Update Member Role - Invalid Role (400)"""
        mock_instance = MagicMock()
        mock_instance.update_member_role.side_effect = HTTPException(
            status_code=400, detail="Invalid role"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 2, "role": "superadmin"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid role"

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_member_role_member_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Update Member Role - Member Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.update_member_role.side_effect = HTTPException(
            status_code=404, detail="Member not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 9999, "role": "admin"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Member not found"

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_member_role_cannot_change_last_owner(self, mock_service_cls, client_as_admin):
        """Postman: Update Member Role - Cannot Change Last Owner (400)"""
        mock_instance = MagicMock()
        mock_instance.update_member_role.side_effect = HTTPException(
            status_code=400, detail="Cannot change role of the last owner"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 1, "role": "member"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Cannot change role of the last owner"

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_member_role_admin_cannot_modify_owner(self, mock_service_cls, client_as_admin):
        """Postman: Update Member Role - Admin Cannot Modify Owner (403)"""
        mock_instance = MagicMock()
        mock_instance.update_member_role.side_effect = HTTPException(
            status_code=403, detail="Admins cannot modify owner roles"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role",
            params={"member_id": 1, "role": "admin"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admins cannot modify owner roles"

    def test_update_member_role_missing_member_id(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role", params={"role": "admin"}
        )
        assert resp.status_code == 422

    def test_update_member_role_missing_role(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role", params={"member_id": 7}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/organization/settings
# ---------------------------------------------------------------------------
class TestGetOrganizationSettings:
    """Tests for GET /api/v1/organization/settings"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_settings_success(self, mock_service_cls, client_as_member):
        """Postman: Get Organization Settings - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_organization_settings.return_value = {}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/settings")

        assert resp.status_code == 200
        mock_instance.get_organization_settings.assert_called_once()

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_settings_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_organization_settings.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/settings")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# PUT /api/v1/organization/settings
# ---------------------------------------------------------------------------
class TestUpdateOrganizationSettings:
    """Tests for PUT /api/v1/organization/settings"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_settings_success(self, mock_service_cls, client_as_admin):
        """Postman: Update Organization Settings - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.update_organization_settings.return_value = {
            "message": "Settings updated successfully",
            "settings": {
                "default_role": "member",
                "allow_signups": True,
                "notification_email": "admin@example.com",
            },
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.put(
            "/api/v1/organization/settings",
            json={
                "default_role": "member",
                "allow_signups": True,
                "notification_email": "admin@example.com",
            },
        )

        assert resp.status_code == 200
        mock_instance.update_organization_settings.assert_called_once_with(
            {
                "default_role": "member",
                "allow_signups": True,
                "notification_email": "admin@example.com",
            }
        )

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_settings_service_error(self, mock_service_cls, client_as_admin):
        mock_instance = MagicMock()
        mock_instance.update_organization_settings.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.put(
            "/api/v1/organization/settings",
            json={"name": "Fail"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/organization/access_requests
# ---------------------------------------------------------------------------
class TestGetAccessRequests:
    """Tests for GET /api/v1/organization/access_requests"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_access_requests_success(self, mock_service_cls, client_as_admin):
        """Postman: Get Access Requests - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_access_requests.return_value = [
            {
                "id": 1,
                "user_id": 5,
                "email": "requester@example.com",
                "username": "requester1",
                "message": "I would like to join your organization.",
                "created_at": 1710201600,
            },
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.get("/api/v1/organization/access_requests")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_instance.get_access_requests.assert_called_once()

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_access_requests_empty(self, mock_service_cls, client_as_admin):
        """Postman: Get Access Requests - Empty (200)"""
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
    """Tests for POST /api/v1/organization/handle_access_request"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_approve(self, mock_service_cls, client_as_admin):
        """Postman: Handle Access Request - Approve (200)"""
        mock_instance = MagicMock()
        mock_instance.handle_access_request.return_value = {"message": "Access request approved"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1, "action": "approve"},
        )

        assert resp.status_code == 200
        mock_instance.handle_access_request.assert_called_once_with(1, "approve", ANY)

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_reject(self, mock_service_cls, client_as_admin):
        """Postman: Handle Access Request - Reject (200)"""
        mock_instance = MagicMock()
        mock_instance.handle_access_request.return_value = {"message": "Access request rejected"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1, "action": "reject"},
        )

        assert resp.status_code == 200
        mock_instance.handle_access_request.assert_called_once_with(1, "reject", ANY)

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_missing_fields(self, mock_service_cls, client_as_admin):
        """Postman: Handle Access Request - Missing Fields (400)"""
        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1},
        )
        assert resp.status_code == 400
        assert "Request ID" in resp.json()["detail"] or "required" in resp.json()["detail"]

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_missing_request_id(self, mock_service_cls, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"action": "approve"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_not_found(self, mock_service_cls, client_as_admin):
        """Postman: Handle Access Request - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.handle_access_request.side_effect = HTTPException(
            status_code=404, detail="Access request not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 9999, "action": "approve"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Access request not found"

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_already_processed(self, mock_service_cls, client_as_admin):
        """Postman: Handle Access Request - Already Processed (400)"""
        mock_instance = MagicMock()
        mock_instance.handle_access_request.side_effect = HTTPException(
            status_code=400, detail="This request has already been processed"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1, "action": "approve"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "This request has already been processed"

    @patch("ee.api.v1.organizations.AuthService")
    def test_handle_access_request_invalid_action(self, mock_service_cls, client_as_admin):
        """Postman: Handle Access Request - Invalid Action (400)"""
        mock_instance = MagicMock()
        mock_instance.handle_access_request.side_effect = HTTPException(
            status_code=400, detail="Invalid action. Use 'approve' or 'reject'"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.post(
            "/api/v1/organization/handle_access_request",
            json={"request_id": 1, "action": "ban"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid action. Use 'approve' or 'reject'"


# ---------------------------------------------------------------------------
# GET /api/v1/organization/roles
# ---------------------------------------------------------------------------
class TestGetRoles:
    """Tests for GET /api/v1/organization/roles"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_roles_success(self, mock_service_cls, client_as_member):
        """Postman: Get Roles - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_roles_by_scope.return_value = [
            {"role": "owner", "description": "Full access to organization"},
            {"role": "admin", "description": "Administrative access"},
            {"role": "member", "description": "Standard member access"},
            {"role": "viewer", "description": "Read-only access"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/roles")

        assert resp.status_code == 200
        assert len(resp.json()) == 4
        mock_instance.get_roles_by_scope.assert_called_once()

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_roles_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_roles_by_scope.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/roles")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# [EE] GET /api/v1/organization/get_associated_tenants
# ---------------------------------------------------------------------------
class TestGetAssociatedTenants:
    """Tests for GET /api/v1/organization/get_associated_tenants (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_associated_tenants_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Get Associated Tenants - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_associated_tenants.return_value = [
            {
                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "name": "My Organization",
                "slug": "my-organization",
                "role": "owner",
                "status": "active",
            },
            {
                "id": "c3d4e5f6-a7b8-9012-cdef-234567890123",
                "name": "Second Org",
                "slug": "second-org",
                "role": "member",
                "status": "active",
            },
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_associated_tenants_empty(self, mock_service_cls, client_as_member):
        """Postman: [EE] Get Associated Tenants - Empty (200)"""
        mock_instance = MagicMock()
        mock_instance.get_associated_tenants.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# [EE] POST /api/v1/organization/create_tenants
# ---------------------------------------------------------------------------
class TestCreateTenants:
    """Tests for POST /api/v1/organization/create_tenants (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_create_tenants_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Create Tenants - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.create_tenants.return_value = {
            "id": "d4e5f6a7-b8c9-0123-def0-345678901234",
            "name": "New Organization",
            "slug": "new-organization",
            "status": "active",
            "created_by": 1,
            "created_at": 1710201600,
            "updated_at": 1710201600,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/create_tenants",
            params={"name": "New Organization"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# [EE] POST /api/v1/organization/request_access
# ---------------------------------------------------------------------------
class TestRequestAccess:
    """Tests for POST /api/v1/organization/request_access (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_request_access_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Request Access - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.request_access.return_value = {
            "message": "Access request submitted successfully",
            "request": {
                "id": 1,
                "user_id": 5,
                "organization_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "status": "pending",
                "message": "I would like to join your organization.",
                "created_at": 1710201600,
            },
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/request_access",
            json={
                "org_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "message": "I would like to join your organization.",
            },
        )
        assert resp.status_code == 200

    @patch("ee.api.v1.organizations.AuthService")
    def test_request_access_missing_org_id(self, mock_service_cls, client_as_member):
        """Postman: [EE] Request Access - Missing Org ID (400)"""
        mock_instance = MagicMock()
        mock_instance.request_access.side_effect = HTTPException(
            status_code=400, detail="Organization ID is required"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/organization/request_access",
            json={"message": "I would like to join."},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# [EE] GET /api/v1/organization/members
# ---------------------------------------------------------------------------
class TestGetMembers:
    """Tests for GET /api/v1/organization/members (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_members_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Get Members - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_members.return_value = [
            {
                "member_id": 1,
                "user_id": 1,
                "email": "owner@example.com",
                "username": "owneruser",
                "first_name": "John",
                "last_name": "Doe",
                "role": "owner",
                "status": "active",
                "joined_at": 1710201600,
                "last_activity_at": 1710288000,
            },
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/members")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# [EE] GET /api/v1/organization/invited_users
# ---------------------------------------------------------------------------
class TestGetInvitedUsers:
    """Tests for GET /api/v1/organization/invited_users (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_invited_users_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Get Invited Users - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_invited_users.return_value = [
            {
                "member_id": 5,
                "email": "invited@example.com",
                "username": "Invited User",
                "name": "Invited User",
                "role": "member",
                "status": "pending",
            },
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/invited_users")
        assert resp.status_code == 200

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_invited_users_empty(self, mock_service_cls, client_as_member):
        """Postman: [EE] Get Invited Users - Empty (200)"""
        mock_instance = MagicMock()
        mock_instance.get_invited_users.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/organization/invited_users")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# [EE] GET /api/v1/organization/details
# ---------------------------------------------------------------------------
class TestGetOrganizationDetails:
    """Tests for GET /api/v1/organization/details (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_get_organization_details_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Get Organization Details - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_organization_details.return_value = {
            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "name": "My Organization",
            "slug": "my-organization",
            "description": "A voice agent organization",
            "status": "active",
            "created_by": 1,
            "created_at": 1710201600,
            "updated_at": 1710201600,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/organization/details",
            params={"org_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# [EE] PUT /api/v1/organization/details
# ---------------------------------------------------------------------------
class TestUpdateOrganizationDetails:
    """Tests for PUT /api/v1/organization/details (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_update_organization_details_success(self, mock_service_cls, client_as_admin):
        """Postman: [EE] Update Organization Details - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.update_organization_details.return_value = {
            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "name": "Updated Organization Name",
            "slug": "my-organization",
            "description": "Updated description",
            "status": "active",
            "created_by": 1,
            "created_at": 1710201600,
            "updated_at": 1710288000,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_admin.put(
            "/api/v1/organization/details",
            params={"org_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"},
            json={
                "name": "Updated Organization Name",
                "description": "Updated description",
            },
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# [EE] DELETE /api/v1/organization/delete
# ---------------------------------------------------------------------------
class TestDeleteOrganization:
    """Tests for DELETE /api/v1/organization/delete (EE endpoint)"""

    @patch("ee.api.v1.organizations.AuthService")
    def test_delete_organization_success(self, mock_service_cls, client_as_owner):
        """Postman: [EE] Delete Organization - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.delete_organization.return_value = {
            "message": "Organization deleted successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_owner.delete(
            "/api/v1/organization/delete",
            params={"org_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"},
        )
        assert resp.status_code == 200
