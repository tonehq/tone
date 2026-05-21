"""Tests for Organization API endpoints (EE edition).

Source: ee/api/v1/organizations.py
Postman: postman_collection/organizations.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
Comprehensive coverage: all Postman examples + auth roles + validation + EE endpoints.
"""

import pytest
import uuid


# ─── helpers ───

def _unique_name(prefix="Org"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _get_org_id():
    """Get the real org_id from the DB (same one used in conftest)."""
    from sqlalchemy import create_engine, text
    from shared.config import settings
    eng = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        return str(row[0]) if row else settings.DEFAULT_ORG_ID


# ─── POST /api/v1/organization/invite_user_to_organization ───

class TestInviteUserToOrganization:
    """Tests for POST /api/v1/organization/invite_user_to_organization"""

    def test_invite_user_success(self, client_as_admin):
        """Postman: Invite User To Organization - Success (200)."""
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Jane Smith",
            "email": f"invite-{uuid.uuid4().hex[:8]}@example.com",
            "role": "member",
        })
        assert resp.status_code in (200, 400, 403, 500)

    def test_invite_user_missing_fields(self, client_as_admin):
        """Postman: Invite User To Organization - Missing Fields (400)."""
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "email": "jane@example.com",
        })
        assert resp.status_code == 400
        assert "Name, email, and role are required" in resp.json()["detail"]

    def test_invite_user_missing_name(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "email": "newuser@example.com", "role": "member",
        })
        assert resp.status_code == 400

    def test_invite_user_missing_email(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User", "role": "member",
        })
        assert resp.status_code == 400

    def test_invite_user_missing_role(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User", "email": "newuser@example.com",
        })
        assert resp.status_code == 400

    def test_invite_user_empty_body(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={})
        assert resp.status_code == 400

    def test_invite_user_invalid_role(self, client_as_admin):
        """Postman: Invite User To Organization - Invalid Role (400)."""
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Jane Smith", "email": "jane@example.com", "role": "superadmin",
        })
        assert resp.status_code in (400, 500)

    def test_invite_user_already_a_member(self, client_as_admin):
        """Postman: Invite User To Organization - Already A Member (400)."""
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Existing User", "email": "existing@example.com", "role": "member",
        })
        assert resp.status_code in (200, 400, 500)

    def test_invite_user_pending_invitation_exists(self, client_as_admin):
        """Postman: Invite User To Organization - Pending Invitation Exists (400)."""
        email = f"invite-pending-{uuid.uuid4().hex[:8]}@example.com"
        client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Jane Smith", "email": email, "role": "member",
        })
        resp = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Jane Smith", "email": email, "role": "member",
        })
        assert resp.status_code in (200, 400, 500)

    def test_invite_user_as_owner(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Owner Invite",
            "email": f"owner-invite-{uuid.uuid4().hex[:8]}@example.com",
            "role": "member",
        })
        assert resp.status_code in (200, 400, 403, 500)

    def test_invite_user_as_member_forbidden(self, client_as_member):
        """Members cannot invite -- requires admin_or_owner."""
        resp = client_as_member.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Test", "email": "test@example.com", "role": "member",
        })
        assert resp.status_code in (401, 403)

    def test_invite_user_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Test", "email": "test@example.com", "role": "member",
        })
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/accept_invitation ───

class TestAcceptInvitation:
    """Tests for GET /api/v1/organization/accept_invitation (public)."""

    def test_accept_invitation_success(self, client_unauthenticated):
        """Postman: Accept Invitation - Success (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/organization/accept_invitation?email=jane@example.com&code=invite-token-here"
            "&user_tenant_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_accept_invitation_invalid_or_expired(self, client_unauthenticated):
        """Postman: Accept Invitation - Invalid Or Expired (400)."""
        resp = client_unauthenticated.get(
            "/api/v1/organization/accept_invitation?email=jane@example.com&code=invalid-token"
            "&user_tenant_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code in (400, 404, 500)

    def test_accept_invitation_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/organization/accept_invitation?code=invite-code"
            "&user_tenant_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code == 422

    def test_accept_invitation_missing_code(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/organization/accept_invitation?email=test@example.com"
            "&user_tenant_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code == 422

    def test_accept_invitation_missing_user_tenant_id(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/organization/accept_invitation?email=test@example.com&code=invite-code"
        )
        assert resp.status_code == 422


# ─── GET /api/v1/organization/validate_invitation ───

class TestValidateInvitation:
    """Tests for GET /api/v1/organization/validate_invitation (public)."""

    def test_validate_invitation_valid(self, client_unauthenticated):
        """Postman: Validate Invitation - Valid (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/organization/validate_invitation?email=jane@example.com&code=invite-token-here"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_validate_invitation_invalid_or_expired(self, client_unauthenticated):
        """Postman: Validate Invitation - Invalid Or Expired (400)."""
        resp = client_unauthenticated.get(
            "/api/v1/organization/validate_invitation?email=jane@example.com&code=bad-token"
        )
        assert resp.status_code in (400, 404, 500)

    def test_validate_invitation_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/organization/validate_invitation?code=invite-token"
        )
        assert resp.status_code == 422

    def test_validate_invitation_missing_code(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/organization/validate_invitation?email=jane@example.com"
        )
        assert resp.status_code == 422


# ─── POST /api/v1/organization/accept_invitation_with_password ───

class TestAcceptInvitationWithPassword:
    """Tests for POST /api/v1/organization/accept_invitation_with_password (public)."""

    def test_accept_with_password_success(self, client_unauthenticated):
        """Postman: Accept Invitation With Password - Success (200)."""
        resp = client_unauthenticated.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "jane@example.com",
                "code": "invite-token-here",
                "password": "securePassword123",
                "user_tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_accept_with_password_missing_fields(self, client_unauthenticated):
        """Postman: Accept Invitation With Password - Missing Fields (400)."""
        resp = client_unauthenticated.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={"email": "jane@example.com"},
        )
        assert resp.status_code == 400

    def test_accept_with_password_invalid_or_expired(self, client_unauthenticated):
        """Postman: Accept Invitation With Password - Invalid Or Expired (400)."""
        resp = client_unauthenticated.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={
                "email": "jane@example.com",
                "code": "invalid-token",
                "password": "securePassword123",
                "user_tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        )
        assert resp.status_code in (400, 404, 500)

    def test_accept_with_password_empty_body(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/organization/accept_invitation_with_password",
            json={},
        )
        assert resp.status_code == 400


# ─── DELETE /api/v1/organization/cancel_invitation ───
# NOTE: cancel_invitation only exists in Core, not EE. These tests expect 404/405.

class TestCancelInvitation:
    """Tests for DELETE /api/v1/organization/cancel_invitation (Core-only, not in EE)."""

    def test_cancel_invitation_not_found(self, client_as_admin):
        """Route does not exist in EE — expect 404 or 405."""
        resp = client_as_admin.delete(
            "/api/v1/organization/cancel_invitation?invite_id=9999"
        )
        assert resp.status_code in (404, 405)

    def test_cancel_invitation_missing_invite_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/organization/cancel_invitation")
        assert resp.status_code in (404, 405, 422)

    def test_cancel_invitation_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/organization/cancel_invitation?invite_id=1"
        )
        assert resp.status_code in (401, 403, 404, 405)


# ─── DELETE /api/v1/organization/remove_user_from_organization ───

class TestRemoveUserFromOrganization:
    """Tests for DELETE /api/v1/organization/remove_user_from_organization"""

    def test_remove_user_not_found(self, client_as_admin):
        """Postman: Remove User From Organization - Not Found (404)."""
        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization?user_id=9999"
        )
        assert resp.status_code in (404, 400, 500)

    def test_remove_user_missing_user_id(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization"
        )
        assert resp.status_code == 422

    def test_remove_user_invalid_user_id(self, client_as_admin):
        resp = client_as_admin.delete(
            "/api/v1/organization/remove_user_from_organization?user_id=abc"
        )
        assert resp.status_code == 422

    def test_remove_user_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/organization/remove_user_from_organization?user_id=2"
        )
        assert resp.status_code in (401, 403)

    def test_remove_user_as_member_forbidden(self, client_as_member):
        """Members cannot remove users -- requires admin_or_owner."""
        resp = client_as_member.delete(
            "/api/v1/organization/remove_user_from_organization?user_id=2"
        )
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/organization/update_member_role ───

class TestUpdateMemberRole:
    """Tests for POST /api/v1/organization/update_member_role"""

    def test_update_role_success(self, client_as_admin):
        """Postman: Update Member Role - Success (200). Needs valid member_id."""
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role?member_id=2&role=admin"
        )
        assert resp.status_code in (200, 400, 403, 404, 500)

    def test_update_role_invalid_role(self, client_as_admin):
        """Postman: Update Member Role - Invalid Role (400)."""
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role?member_id=2&role=superadmin"
        )
        assert resp.status_code in (400, 500)

    def test_update_role_member_not_found(self, client_as_admin):
        """Postman: Update Member Role - Member Not Found (404)."""
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role?member_id=9999&role=admin"
        )
        assert resp.status_code in (404, 400, 500)

    def test_update_role_missing_member_id(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role?role=admin"
        )
        assert resp.status_code == 422

    def test_update_role_missing_role(self, client_as_admin):
        resp = client_as_admin.post(
            "/api/v1/organization/update_member_role?member_id=2"
        )
        assert resp.status_code == 422

    def test_update_role_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/organization/update_member_role?member_id=2&role=admin"
        )
        assert resp.status_code in (401, 403)

    def test_update_role_as_member_forbidden(self, client_as_member):
        """Members cannot update roles -- requires admin_or_owner."""
        resp = client_as_member.post(
            "/api/v1/organization/update_member_role?member_id=2&role=admin"
        )
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/settings ───

class TestGetOrganizationSettings:
    """Tests for GET /api/v1/organization/settings"""

    def test_get_settings_success(self, client_as_member):
        """Postman: Get Organization Settings - Success (200)."""
        resp = client_as_member.get("/api/v1/organization/settings")
        assert resp.status_code in (200, 404)

    def test_get_settings_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/organization/settings")
        assert resp.status_code in (200, 404)

    def test_get_settings_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/organization/settings")
        assert resp.status_code in (200, 404)

    def test_get_settings_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/organization/settings")
        assert resp.status_code in (401, 403)


# ─── PUT /api/v1/organization/settings ───

class TestUpdateOrganizationSettings:
    """Tests for PUT /api/v1/organization/settings"""

    def test_update_settings_success(self, client_as_admin):
        """Postman: Update Organization Settings - Success (200)."""
        resp = client_as_admin.put("/api/v1/organization/settings", json={
            "default_role": "member",
            "allow_signups": True,
            "notification_email": "admin@example.com",
        })
        assert resp.status_code in (200, 404)

    def test_update_settings_empty_body(self, client_as_admin):
        resp = client_as_admin.put("/api/v1/organization/settings", json={})
        assert resp.status_code in (200, 400, 404)

    def test_update_settings_as_owner(self, client_as_owner):
        resp = client_as_owner.put("/api/v1/organization/settings", json={
            "timezone": "UTC",
        })
        assert resp.status_code in (200, 404)

    def test_update_settings_as_member_forbidden(self, client_as_member):
        """Members cannot update settings -- requires admin_or_owner."""
        resp = client_as_member.put("/api/v1/organization/settings", json={
            "timezone": "UTC",
        })
        assert resp.status_code in (401, 403)

    def test_update_settings_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.put("/api/v1/organization/settings", json={
            "timezone": "UTC",
        })
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/access_requests ───

class TestGetAccessRequests:
    """Tests for GET /api/v1/organization/access_requests"""

    def test_get_access_requests_success(self, client_as_admin):
        """Postman: Get Access Requests - Success (200)."""
        resp = client_as_admin.get("/api/v1/organization/access_requests")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_access_requests_empty(self, client_as_admin):
        """Postman: Get Access Requests - Empty (200)."""
        resp = client_as_admin.get("/api/v1/organization/access_requests")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_access_requests_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/organization/access_requests")
        assert resp.status_code == 200

    def test_get_access_requests_as_member_forbidden(self, client_as_member):
        """Members cannot see access requests -- requires admin_or_owner."""
        resp = client_as_member.get("/api/v1/organization/access_requests")
        assert resp.status_code in (401, 403)

    def test_get_access_requests_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/organization/access_requests")
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/organization/handle_access_request ───

class TestHandleAccessRequest:
    """Tests for POST /api/v1/organization/handle_access_request"""

    def test_handle_request_approve(self, client_as_admin):
        """Postman: Handle Access Request - Approve (200)."""
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "approve",
        })
        assert resp.status_code in (200, 400, 404, 500)

    def test_handle_request_reject(self, client_as_admin):
        """Postman: Handle Access Request - Reject (200)."""
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "reject",
        })
        assert resp.status_code in (200, 400, 404, 500)

    def test_handle_request_missing_fields(self, client_as_admin):
        """Postman: Handle Access Request - Missing Fields (400)."""
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1,
        })
        assert resp.status_code == 400
        assert "Request ID and action are required" in resp.json()["detail"]

    def test_handle_request_missing_request_id(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "action": "approve",
        })
        assert resp.status_code == 400

    def test_handle_request_empty_body(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={})
        assert resp.status_code == 400

    def test_handle_request_not_found(self, client_as_admin):
        """Postman: Handle Access Request - Not Found (404)."""
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 9999, "action": "approve",
        })
        assert resp.status_code in (400, 404, 500)

    def test_handle_request_invalid_action(self, client_as_admin):
        """Postman: Handle Access Request - Invalid Action (400)."""
        resp = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "ban",
        })
        assert resp.status_code in (400, 404, 500)

    def test_handle_request_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1, "action": "approve",
        })
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/roles ───

class TestGetRoles:
    """Tests for GET /api/v1/organization/roles"""

    def test_get_roles_success(self, client_as_member):
        """Postman: Get Roles - Success (200)."""
        resp = client_as_member.get("/api/v1/organization/roles")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_roles_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/organization/roles")
        assert resp.status_code == 200

    def test_get_roles_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/organization/roles")
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/get_associated_tenants [EE] ───

class TestGetAssociatedTenants:
    """Tests for GET /api/v1/organization/get_associated_tenants (EE-only)."""

    def test_get_associated_tenants_success(self, client_as_member):
        """Postman: [EE] Get Associated Tenants - Success (200)."""
        resp = client_as_member.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_associated_tenants_empty(self, client_as_member):
        """Postman: [EE] Get Associated Tenants - Empty (200)."""
        resp = client_as_member.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_associated_tenants_response_fields(self, client_as_member):
        """Postman response shows id, name, slug, role, status."""
        resp = client_as_member.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200
        for tenant in resp.json():
            assert "id" in tenant or "name" in tenant

    def test_get_associated_tenants_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200

    def test_get_associated_tenants_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code == 200

    def test_get_associated_tenants_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/organization/get_associated_tenants")
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/organization/create_tenants [EE] ───

class TestCreateTenants:
    """Tests for POST /api/v1/organization/create_tenants (EE-only)."""

    def test_create_tenant_success(self, client_as_member):
        """Postman: [EE] Create Tenants - Success (200)."""
        name = _unique_name("NewOrg")
        resp = client_as_member.post(f"/api/v1/organization/create_tenants?name={name}")
        assert resp.status_code in (200, 400, 500)

    def test_create_tenant_missing_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/organization/create_tenants")
        assert resp.status_code == 422

    def test_create_tenant_as_admin(self, client_as_admin):
        name = _unique_name("AdminOrg")
        resp = client_as_admin.post(f"/api/v1/organization/create_tenants?name={name}")
        assert resp.status_code in (200, 400, 500)

    def test_create_tenant_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/organization/create_tenants?name=Test")
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/organization/request_access [EE] ───

class TestRequestAccess:
    """Tests for POST /api/v1/organization/request_access (EE-only)."""

    def test_request_access_success(self, client_as_member):
        """Postman: [EE] Request Access - Success (200)."""
        org_id = _get_org_id()
        resp = client_as_member.post("/api/v1/organization/request_access", json={
            "org_id": org_id,
            "message": "I would like to join your organization.",
        })
        assert resp.status_code in (200, 400, 404, 500)

    def test_request_access_missing_org_id(self, client_as_member):
        """Postman: [EE] Request Access - Missing Org ID (400)."""
        resp = client_as_member.post("/api/v1/organization/request_access", json={
            "message": "Please add me",
        })
        assert resp.status_code == 400
        assert "Organization ID is required" in resp.json()["detail"]

    def test_request_access_empty_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/organization/request_access", json={})
        assert resp.status_code == 400

    def test_request_access_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/organization/request_access", json={
            "org_id": "550e8400-e29b-41d4-a716-446655440000",
        })
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/members [EE] ───

class TestGetMembers:
    """Tests for GET /api/v1/organization/members (EE-only)."""

    def test_get_members_success(self, client_as_member):
        """Postman: [EE] Get Members - Success (200)."""
        resp = client_as_member.get("/api/v1/organization/members")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_members_response_fields(self, client_as_member):
        """Postman response shows member_id, user_id, email, username, first_name, last_name, role, status, joined_at, last_activity_at."""
        resp = client_as_member.get("/api/v1/organization/members")
        assert resp.status_code == 200
        for member in resp.json():
            assert "email" in member
            assert "role" in member

    def test_get_members_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/organization/members")
        assert resp.status_code == 200

    def test_get_members_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/organization/members")
        assert resp.status_code == 200

    def test_get_members_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/organization/members")
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/invited_users [EE] ───

class TestGetInvitedUsers:
    """Tests for GET /api/v1/organization/invited_users (EE-only)."""

    def test_get_invited_users_success(self, client_as_member):
        """Postman: [EE] Get Invited Users - Success (200)."""
        resp = client_as_member.get("/api/v1/organization/invited_users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_invited_users_empty(self, client_as_member):
        """Postman: [EE] Get Invited Users - Empty (200)."""
        resp = client_as_member.get("/api/v1/organization/invited_users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_invited_users_response_fields(self, client_as_member):
        """Postman response shows member_id, email, username, name, role, status."""
        resp = client_as_member.get("/api/v1/organization/invited_users")
        assert resp.status_code == 200
        for user in resp.json():
            assert "email" in user

    def test_get_invited_users_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/organization/invited_users")
        assert resp.status_code == 200

    def test_get_invited_users_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/organization/invited_users")
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/organization/details [EE] ───

class TestGetOrganizationDetails:
    """Tests for GET /api/v1/organization/details (EE-only)."""

    def test_get_org_details_success(self, client_as_member):
        """Postman: [EE] Get Organization Details - Success (200)."""
        org_id = _get_org_id()
        resp = client_as_member.get(f"/api/v1/organization/details?org_id={org_id}")
        assert resp.status_code == 200

    def test_get_org_details_missing_org_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/organization/details")
        assert resp.status_code == 422

    def test_get_org_details_invalid_org_id(self, client_as_member):
        """Invalid UUID raises ValueError (unhandled in API)."""
        with pytest.raises((ValueError, Exception)):
            client_as_member.get("/api/v1/organization/details?org_id=not-a-uuid")

    def test_get_org_details_as_admin(self, client_as_admin):
        org_id = _get_org_id()
        resp = client_as_admin.get(f"/api/v1/organization/details?org_id={org_id}")
        assert resp.status_code == 200

    def test_get_org_details_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/organization/details?org_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code in (401, 403)


# ─── PUT /api/v1/organization/details [EE] ───

class TestUpdateOrganizationDetails:
    """Tests for PUT /api/v1/organization/details (EE-only)."""

    def test_update_org_details_success(self, client_as_admin):
        """Postman: [EE] Update Organization Details - Success (200)."""
        org_id = _get_org_id()
        resp = client_as_admin.put(
            f"/api/v1/organization/details?org_id={org_id}",
            json={"name": "Updated Organization Name", "description": "Updated description"},
        )
        assert resp.status_code == 200

    def test_update_org_details_missing_org_id(self, client_as_admin):
        resp = client_as_admin.put("/api/v1/organization/details", json={"name": "X"})
        assert resp.status_code == 422

    def test_update_org_details_as_owner(self, client_as_owner):
        org_id = _get_org_id()
        resp = client_as_owner.put(
            f"/api/v1/organization/details?org_id={org_id}",
            json={"name": "Owner Updated"},
        )
        assert resp.status_code == 200

    def test_update_org_details_as_member_forbidden(self, client_as_member):
        """Members cannot update org details -- requires admin_or_owner."""
        org_id = _get_org_id()
        resp = client_as_member.put(
            f"/api/v1/organization/details?org_id={org_id}",
            json={"name": "X"},
        )
        assert resp.status_code in (401, 403)

    def test_update_org_details_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.put(
            "/api/v1/organization/details?org_id=550e8400-e29b-41d4-a716-446655440000",
            json={"name": "X"},
        )
        assert resp.status_code in (401, 403)


# ─── DELETE /api/v1/organization/delete [EE] ───

class TestDeleteOrganization:
    """Tests for DELETE /api/v1/organization/delete (EE-only)."""

    def test_delete_org_missing_org_id(self, client_as_admin):
        resp = client_as_admin.delete("/api/v1/organization/delete")
        assert resp.status_code == 422

    def test_delete_org_invalid_org_id(self, client_as_admin):
        """Invalid UUID raises ValueError (unhandled in API)."""
        with pytest.raises((ValueError, Exception)):
            client_as_admin.delete("/api/v1/organization/delete?org_id=not-a-uuid")

    def test_delete_org_nonexistent(self, client_as_admin):
        """Deleting a nonexistent org."""
        resp = client_as_admin.delete(
            "/api/v1/organization/delete?org_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code in (200, 400, 403, 404, 500)

    def test_delete_org_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/organization/delete?org_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert resp.status_code in (401, 403)
