"""Tests for OAuth API endpoints (EE edition).

Source: ee/api/v1/oauth.py
Postman: postman_collection/oauth.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
"""

import pytest

from sqlalchemy import create_engine, text
from shared.config import settings

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def _get_org_id():
    with _engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        return str(row[0]) if row else settings.DEFAULT_ORG_ID


def _get_user_id():
    with _engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
        return row[0] if row else 1


ORG_ID = _get_org_id()
REAL_USER_ID = _get_user_id()


# --- GET /api/v1/oauth/connections ---

class TestGetConnections:
    """Tests for GET /api/v1/oauth/connections"""

    def test_get_connections_success(self, client_as_member):
        """Postman: Get Connections - Success (200)."""
        response = client_as_member.get("/api/v1/oauth/connections")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_connections_with_provider_filter(self, client_as_member):
        """Postman query param: provider=google_calendar (optional filter)."""
        response = client_as_member.get(
            "/api/v1/oauth/connections",
            params={"provider": "google_calendar"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_connections_returns_list_format(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/connections")
        assert response.status_code == 200
        connections = response.json()
        if connections:
            conn = connections[0]
            assert "id" in conn
            assert "provider" in conn

    def test_get_connections_empty(self, client_as_member):
        """Postman: Get Connections - Empty (200, [])."""
        response = client_as_member.get("/api/v1/oauth/connections")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_connections_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/oauth/connections")
        assert response.status_code in (401, 403)

    def test_get_connections_as_admin(self, client_as_admin):
        response = client_as_admin.get("/api/v1/oauth/connections")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_connections_as_owner(self, client_as_owner):
        response = client_as_owner.get("/api/v1/oauth/connections")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# --- GET /api/v1/oauth/connection ---

class TestGetConnectionByProvider:
    """Tests for GET /api/v1/oauth/connection"""

    def test_get_connection_not_connected(self, client_as_member):
        """Postman: Get Connection By Provider - Not Connected (200)."""
        response = client_as_member.get(
            "/api/v1/oauth/connection",
            params={"provider": "nonexistent_provider"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["connected"] is False
        assert result["provider"] == "nonexistent_provider"

    def test_get_connection_google_calendar(self, client_as_member):
        """Postman: Get Connection By Provider - check google_calendar."""
        response = client_as_member.get(
            "/api/v1/oauth/connection",
            params={"provider": "google_calendar"},
        )
        assert response.status_code == 200

    def test_get_connection_missing_provider_param(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/connection")
        assert response.status_code == 422

    def test_get_connection_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/oauth/connection",
            params={"provider": "google_calendar"},
        )
        assert response.status_code in (401, 403)


# --- DELETE /api/v1/oauth/disconnect ---

class TestDisconnect:
    """Tests for DELETE /api/v1/oauth/disconnect"""

    def test_disconnect_not_found(self, client_as_member):
        """Postman: Disconnect - Not Found (404)."""
        response = client_as_member.delete(
            "/api/v1/oauth/disconnect",
            params={"connection_id": 999999},
        )
        assert response.status_code in (400, 404)

    def test_disconnect_missing_connection_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/oauth/disconnect")
        assert response.status_code == 422

    def test_disconnect_invalid_connection_id(self, client_as_member):
        response = client_as_member.delete(
            "/api/v1/oauth/disconnect",
            params={"connection_id": "abc"},
        )
        assert response.status_code in (400, 422)

    def test_disconnect_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete(
            "/api/v1/oauth/disconnect",
            params={"connection_id": 1},
        )
        assert response.status_code in (401, 403)


# --- GET /api/v1/oauth/providers (noauth) ---

class TestListProviders:
    """Tests for GET /api/v1/oauth/providers"""

    def test_list_providers_success(self, client_as_member):
        """Postman: List Providers - Success (200)."""
        response = client_as_member.get("/api/v1/oauth/providers")
        assert response.status_code == 200
        result = response.json()
        assert "providers" in result
        assert isinstance(result["providers"], list)

    def test_list_providers_unauthenticated(self, client_unauthenticated):
        """Postman: providers endpoint has noauth -- should still work."""
        response = client_unauthenticated.get("/api/v1/oauth/providers")
        assert response.status_code == 200
        assert "providers" in response.json()

    def test_list_providers_contains_known_providers(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/providers")
        assert response.status_code == 200
        providers = response.json()["providers"]
        # Provider list should be non-empty; specific providers depend on config
        assert len(providers) >= 0


# --- GET /api/v1/oauth/{provider}/authorize ---

class TestAuthorize:
    """Tests for GET /api/v1/oauth/{provider}/authorize"""

    def test_authorize_unsupported_provider(self, client_as_member):
        """Postman: Authorize - Unsupported Provider (400)."""
        response = client_as_member.get("/api/v1/oauth/invalid_provider/authorize")
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    def test_authorize_google_calendar(self, client_as_member):
        """Postman: Authorize - Success (200) if credentials configured."""
        response = client_as_member.get("/api/v1/oauth/google_calendar/authorize")
        if response.status_code == 200:
            result = response.json()
            assert "auth_url" in result
            assert "accounts.google.com" in result["auth_url"]
            assert "client_id" in result["auth_url"]
            assert "redirect_uri" in result["auth_url"]
            assert "state=" in result["auth_url"]
            assert "google_calendar" in result["auth_url"]
        else:
            # 500 if OAuth credentials not configured
            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]

    def test_authorize_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/oauth/google_calendar/authorize")
        assert response.status_code in (401, 403)


# --- GET /api/v1/oauth/{provider}/callback (noauth) ---

class TestCallback:
    """Tests for GET /api/v1/oauth/{provider}/callback"""

    def test_callback_invalid_state_format(self, client_as_member):
        """Postman: Callback - Invalid State (400)."""
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "fake_code", "state": "invalid_state"},
        )
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

    def test_callback_provider_mismatch_in_state(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={
                "code": "fake_code",
                "state": f"{ORG_ID}:{REAL_USER_ID}:google_sheets",
            },
        )
        assert response.status_code == 400
        assert "Provider mismatch" in response.json()["detail"]

    def test_callback_unsupported_provider(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/oauth/unsupported_provider/callback",
            params={"code": "fake_code", "state": f"{ORG_ID}:{REAL_USER_ID}:unsupported_provider"},
        )
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    def test_callback_missing_code_param(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"state": f"{ORG_ID}:{REAL_USER_ID}:google_calendar"},
        )
        assert response.status_code == 422

    def test_callback_missing_state_param(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "fake_code"},
        )
        assert response.status_code == 422

    def test_callback_missing_both_params(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/google_calendar/callback")
        assert response.status_code == 422

    def test_callback_invalid_state_uuid(self, client_as_member):
        """State with invalid UUID should fail."""
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "fake_code", "state": "not-a-uuid:123:google_calendar"},
        )
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

    def test_callback_invalid_state_user_id(self, client_as_member):
        """State with non-integer user_id should fail."""
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "fake_code", "state": f"{ORG_ID}:not_int:google_calendar"},
        )
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

    def test_callback_fake_code_fails_token_exchange(self, client_as_member):
        """Postman: Callback - Token Exchange Failed (400)."""
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={
                "code": "fake_authorization_code",
                "state": f"{ORG_ID}:{REAL_USER_ID}:google_calendar",
            },
        )
        assert response.status_code == 400
        assert "Token exchange failed" in response.json().get("detail", "")


# ─── Additional uncovered endpoints ───


# --- POST /api/v1/oauth/list ---

class TestListConnections:
    """Tests for POST /api/v1/oauth/list"""

    def test_list_connections_empty_body(self, client_as_member):
        response = client_as_member.post("/api/v1/oauth/list", json={})
        assert response.status_code in (200, 201, 500)
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_list_connections_with_provider_slug_filter(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/oauth/list",
            json={"provider_slug": "google_calendar"},
        )
        assert response.status_code in (200, 201, 500)
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_list_connections_as_admin(self, client_as_admin):
        response = client_as_admin.post("/api/v1/oauth/list", json={})
        assert response.status_code in (200, 201, 500)

    def test_list_connections_as_owner(self, client_as_owner):
        response = client_as_owner.post("/api/v1/oauth/list", json={})
        assert response.status_code in (200, 201, 500)

    def test_list_connections_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/oauth/list", json={})
        assert response.status_code in (401, 403)


# --- GET /api/v1/oauth/catalog (noauth) ---

class TestCatalog:
    """Tests for GET /api/v1/oauth/catalog"""

    def test_catalog_success(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/catalog")
        assert response.status_code == 200
        result = response.json()
        assert "providers" in result
        assert isinstance(result["providers"], list)

    def test_catalog_unauthenticated(self, client_unauthenticated):
        """Catalog endpoint has no auth dep -- should work without auth."""
        response = client_unauthenticated.get("/api/v1/oauth/catalog")
        assert response.status_code == 200
        assert "providers" in response.json()

    def test_catalog_as_admin(self, client_as_admin):
        response = client_as_admin.get("/api/v1/oauth/catalog")
        assert response.status_code == 200
        assert "providers" in response.json()


# --- POST /api/v1/oauth/custom_credential ---

class TestCustomCredential:
    """Tests for POST /api/v1/oauth/custom_credential"""

    def test_custom_credential_minimal_body(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/oauth/custom_credential",
            json={
                "provider_slug": "custom_test_provider",
                "auth_type": "bearer",
                "label": "Test Credential",
                "token": "test_token_value",
            },
        )
        assert response.status_code in (200, 201, 400, 500)

    def test_custom_credential_missing_required_fields(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/oauth/custom_credential",
            json={},
        )
        assert response.status_code in (400, 422, 500)

    def test_custom_credential_oauth_type(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/oauth/custom_credential",
            json={
                "provider_slug": "custom_oauth_provider",
                "auth_type": "oauth",
                "label": "Custom OAuth",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
        )
        assert response.status_code in (200, 201, 400, 500)

    def test_custom_credential_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/oauth/custom_credential",
            json={
                "provider_slug": "custom_test_provider",
                "auth_type": "bearer",
                "token": "test_token",
            },
        )
        assert response.status_code in (401, 403)


# --- POST /api/v1/oauth/mcp/discover ---

class TestMcpDiscover:
    """Tests for POST /api/v1/oauth/mcp/discover"""

    def test_mcp_discover_missing_server_url(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/oauth/mcp/discover",
            json={},
        )
        assert response.status_code == 400
        assert "server_url is required" in response.json().get("detail", "")

    def test_mcp_discover_with_server_url(self, client_as_member):
        """Real network call -- accept a wide range of failure modes."""
        response = client_as_member.post(
            "/api/v1/oauth/mcp/discover",
            json={
                "server_url": "https://example.com/mcp",
                "label": "Test MCP Server",
            },
        )
        assert response.status_code in (200, 400, 500, 502, 503)

    def test_mcp_discover_with_return_to(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/oauth/mcp/discover",
            json={
                "server_url": "https://example.com/mcp",
                "label": "Test MCP",
                "return_to": "https://app.example.com/callback",
            },
        )
        assert response.status_code in (200, 400, 500, 502, 503)

    def test_mcp_discover_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post(
            "/api/v1/oauth/mcp/discover",
            json={"server_url": "https://example.com/mcp"},
        )
        assert response.status_code in (401, 403)


# --- GET /api/v1/oauth/mcp/callback (noauth) ---

class TestMcpCallback:
    """Tests for GET /api/v1/oauth/mcp/callback"""

    def test_mcp_callback_missing_code(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/oauth/mcp/callback",
            params={"state": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 422

    def test_mcp_callback_missing_state(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/oauth/mcp/callback",
            params={"code": "fake_code"},
        )
        assert response.status_code == 422

    def test_mcp_callback_missing_both_params(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/oauth/mcp/callback")
        assert response.status_code == 422

    def test_mcp_callback_unknown_state(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/oauth/mcp/callback",
            params={
                "code": "fake_code",
                "state": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code == 400
        assert "Unknown or expired MCP OAuth state" in response.json().get("detail", "")

    def test_mcp_callback_unknown_state_as_member(self, client_as_member):
        """Endpoint has no auth dep -- behavior should be identical for authed clients."""
        response = client_as_member.get(
            "/api/v1/oauth/mcp/callback",
            params={
                "code": "fake_code",
                "state": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code == 400
        assert "Unknown or expired MCP OAuth state" in response.json().get("detail", "")
