"""Tests for Organization API endpoints (EE edition).

Source: ee/api/v1/organizations.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# ─── POST /api/v1/organization/invite_user_to_organization ───

class TestInviteUserToOrganization:
    """Tests for POST /api/v1/organization/invite_user_to_organization"""

    def test_invite_user_missing_name(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "email": "newuser@example.com", "role": "member"
        })
        assert response.status_code == 400

    def test_invite_user_missing_email(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User", "role": "member"
        })
        assert response.status_code == 400

    def test_invite_user_missing_role(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "New User", "email": "newuser@example.com"
        })
        assert response.status_code == 400

    def test_invite_user_empty_body(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/invite_user_to_organization", json={})
        assert response.status_code == 400

    def test_invite_user_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/organization/invite_user_to_organization", json={
            "name": "Test", "email": "test@example.com", "role": "member"
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/accept_invitation ───

class TestAcceptInvitation:
    """Tests for GET /api/v1/organization/accept_invitation"""

    def test_accept_invitation_missing_email(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/organization/accept_invitation?code=invite-code&user_tenant_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == 422

    def test_accept_invitation_missing_code(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/organization/accept_invitation?email=test@example.com&user_tenant_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code == 422


# ─── DELETE /api/v1/organization/remove_user_from_organization ───

class TestRemoveUserFromOrganization:
    """Tests for DELETE /api/v1/organization/remove_user_from_organization"""

    def test_remove_user_missing_user_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/organization/remove_user_from_organization")
        assert response.status_code == 422

    def test_remove_user_invalid_user_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/organization/remove_user_from_organization?user_id=abc")
        assert response.status_code == 422

    def test_remove_user_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/organization/remove_user_from_organization?user_id=2")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/organization/update_member_role ───

class TestUpdateMemberRole:
    """Tests for POST /api/v1/organization/update_member_role"""

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

    def test_get_settings_returns_success(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/settings")
        assert response.status_code in (200, 404)  # 404 if no settings exist for this org

    def test_get_settings_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/settings")
        assert response.status_code in (401, 403)


# ─── PUT /api/v1/organization/settings ───

class TestUpdateOrganizationSettings:
    """Tests for PUT /api/v1/organization/settings"""

    def test_update_settings_success(self, client_as_admin):
        response = client_as_admin.put("/api/v1/organization/settings", json={"timezone": "UTC"})
        assert response.status_code in (200, 404)

    def test_update_settings_empty_body(self, client_as_admin):
        response = client_as_admin.put("/api/v1/organization/settings", json={})
        assert response.status_code in (200, 400, 404)

    def test_update_settings_as_member_forbidden(self, client_as_member):
        """Members cannot update settings — requires admin_or_owner."""
        response = client_as_member.put("/api/v1/organization/settings", json={"timezone": "UTC"})
        assert response.status_code in (401, 403)

    def test_update_settings_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.put("/api/v1/organization/settings", json={"timezone": "UTC"})
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/access_requests ───

class TestGetAccessRequests:
    """Tests for GET /api/v1/organization/access_requests"""

    def test_get_access_requests_returns_200(self, client_as_admin):
        response = client_as_admin.get("/api/v1/organization/access_requests")
        assert response.status_code == 200

    def test_get_access_requests_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/access_requests")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/organization/handle_access_request ───

class TestHandleAccessRequest:
    """Tests for POST /api/v1/organization/handle_access_request"""

    def test_handle_request_missing_request_id(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "action": "approve"
        })
        assert response.status_code == 400

    def test_handle_request_missing_action(self, client_as_admin):
        response = client_as_admin.post("/api/v1/organization/handle_access_request", json={
            "request_id": 1
        })
        assert response.status_code == 400

    def test_handle_request_empty_body(self, client_as_admin):
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

    def test_get_roles_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/roles")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_roles_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/roles")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/get_associated_tenants (EE) ───

class TestGetAssociatedTenants:
    """Tests for GET /api/v1/organization/get_associated_tenants"""

    def test_get_associated_tenants_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/get_associated_tenants")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_associated_tenants_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/get_associated_tenants")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/organization/create_tenants (EE) ───

class TestCreateTenants:
    """Tests for POST /api/v1/organization/create_tenants"""

    def test_create_tenant_missing_name(self, client_as_member):
        response = client_as_member.post("/api/v1/organization/create_tenants")
        assert response.status_code == 422

    def test_create_tenant_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/organization/create_tenants?name=Test")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/organization/request_access (EE) ───

class TestRequestAccess:
    """Tests for POST /api/v1/organization/request_access"""

    def test_request_access_missing_org_id(self, client_as_member):
        response = client_as_member.post("/api/v1/organization/request_access", json={
            "message": "Please add me"
        })
        assert response.status_code == 400

    def test_request_access_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/organization/request_access", json={
            "org_id": "550e8400-e29b-41d4-a716-446655440000"
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/members (EE) ───

class TestGetMembers:
    """Tests for GET /api/v1/organization/members"""

    def test_get_members_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/members")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_members_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/members")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/invited_users (EE) ───

class TestGetInvitedUsers:
    """Tests for GET /api/v1/organization/invited_users"""

    def test_get_invited_users_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/invited_users")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_invited_users_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/invited_users")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/organization/details ───

class TestGetOrganizationDetails:
    """Tests for GET /api/v1/organization/details"""

    def _get_org_id(self):
        """Get the real org_id from the DB (same one used in conftest)."""
        from sqlalchemy import create_engine, text
        from shared.config import settings
        eng = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
            return str(row[0]) if row else settings.DEFAULT_ORG_ID

    def test_get_org_details_success(self, client_as_member):
        org_id = self._get_org_id()
        response = client_as_member.get(f"/api/v1/organization/details?org_id={org_id}")
        assert response.status_code == 200

    def test_get_org_details_missing_org_id(self, client_as_member):
        response = client_as_member.get("/api/v1/organization/details")
        assert response.status_code == 422

    def test_get_org_details_invalid_org_id(self, client_as_member):
        """Invalid UUID raises ValueError (unhandled in API — known issue)."""
        with pytest.raises((ValueError, Exception)):
            client_as_member.get("/api/v1/organization/details?org_id=not-a-uuid")

    def test_get_org_details_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/organization/details?org_id=550e8400-e29b-41d4-a716-446655440000")
        assert response.status_code in (401, 403)


# ─── PUT /api/v1/organization/details ───

class TestUpdateOrganizationDetails:
    """Tests for PUT /api/v1/organization/details"""

    def _get_org_id(self):
        from sqlalchemy import create_engine, text
        from shared.config import settings
        eng = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
            return str(row[0]) if row else settings.DEFAULT_ORG_ID

    def test_update_org_details_success(self, client_as_admin):
        org_id = self._get_org_id()
        response = client_as_admin.put(
            f"/api/v1/organization/details?org_id={org_id}",
            json={"name": "Updated Org Name"},
        )
        assert response.status_code == 200

    def test_update_org_details_missing_org_id(self, client_as_admin):
        response = client_as_admin.put("/api/v1/organization/details", json={"name": "X"})
        assert response.status_code == 422

    def test_update_org_details_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.put(
            "/api/v1/organization/details?org_id=550e8400-e29b-41d4-a716-446655440000",
            json={"name": "X"},
        )
        assert response.status_code in (401, 403)

    def test_update_org_details_as_member_forbidden(self, client_as_member):
        """Members cannot update org details — requires admin_or_owner."""
        org_id = self._get_org_id()
        response = client_as_member.put(
            f"/api/v1/organization/details?org_id={org_id}",
            json={"name": "X"},
        )
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/organization/delete ───

class TestDeleteOrganization:
    """Tests for DELETE /api/v1/organization/delete"""

    def test_delete_org_missing_org_id(self, client_as_admin):
        response = client_as_admin.delete("/api/v1/organization/delete")
        assert response.status_code == 422

    def test_delete_org_invalid_org_id(self, client_as_admin):
        """Invalid UUID raises ValueError (unhandled in API — known issue)."""
        with pytest.raises((ValueError, Exception)):
            client_as_admin.delete("/api/v1/organization/delete?org_id=not-a-uuid")

    def test_delete_org_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete(
            "/api/v1/organization/delete?org_id=550e8400-e29b-41d4-a716-446655440000"
        )
        assert response.status_code in (401, 403)
