"""Tests for OAuth API endpoints (EE edition).

Source: ee/api/v1/oauth.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid
import time

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


# ─── Helpers ───

def _create_oauth_connection(client, provider="google_calendar"):
    """Create an OAuth connection directly via DB for test setup.

    Since the callback endpoint requires external token exchange,
    we use the connections list to verify state instead.
    """
    # We can't easily create connections via the API (callback needs real OAuth),
    # so tests that need existing connections will rely on whatever exists in DB.
    pass


# ─── GET /api/v1/oauth/connections ───

class TestGetConnections:
    """Tests for GET /api/v1/oauth/connections"""

    def test_get_connections_success(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/connections")
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
            assert "is_active" in conn

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


# ─── GET /api/v1/oauth/connection ───

class TestGetConnectionByProvider:
    """Tests for GET /api/v1/oauth/connection"""

    def test_get_connection_by_provider_not_connected(self, client_as_member):
        """When no connection exists for a provider, returns connected=False."""
        response = client_as_member.get(
            "/api/v1/oauth/connection",
            params={"provider": "nonexistent_provider"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["connected"] is False
        assert result["provider"] == "nonexistent_provider"

    def test_get_connection_missing_provider_param(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/connection")
        assert response.status_code == 422

    def test_get_connection_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/oauth/connection",
            params={"provider": "google_calendar"},
        )
        assert response.status_code in (401, 403)

    def test_get_connection_google_calendar(self, client_as_member):
        """Check connection status for google_calendar provider."""
        response = client_as_member.get(
            "/api/v1/oauth/connection",
            params={"provider": "google_calendar"},
        )
        assert response.status_code == 200
        result = response.json()
        assert "connected" in result
        assert result["provider"] == "google_calendar"

    def test_get_connection_google_sheets(self, client_as_member):
        """Check connection status for google_sheets provider."""
        response = client_as_member.get(
            "/api/v1/oauth/connection",
            params={"provider": "google_sheets"},
        )
        assert response.status_code == 200
        result = response.json()
        assert "connected" in result
        assert result["provider"] == "google_sheets"


# ─── DELETE /api/v1/oauth/disconnect ───

class TestDisconnect:
    """Tests for DELETE /api/v1/oauth/disconnect"""

    def test_disconnect_missing_connection_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/oauth/disconnect")
        assert response.status_code == 422

    def test_disconnect_invalid_connection_id(self, client_as_member):
        response = client_as_member.delete(
            "/api/v1/oauth/disconnect",
            params={"connection_id": "abc"},
        )
        assert response.status_code == 422

    def test_disconnect_not_found(self, client_as_member):
        response = client_as_member.delete(
            "/api/v1/oauth/disconnect",
            params={"connection_id": 999999},
        )
        assert response.status_code == 404

    def test_disconnect_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete(
            "/api/v1/oauth/disconnect",
            params={"connection_id": 1},
        )
        assert response.status_code in (401, 403)


# ─── GET /api/v1/oauth/providers ───

class TestListProviders:
    """Tests for GET /api/v1/oauth/providers"""

    def test_list_providers_success(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/providers")
        assert response.status_code == 200
        result = response.json()
        assert "providers" in result
        assert isinstance(result["providers"], list)

    def test_list_providers_contains_known_providers(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/providers")
        assert response.status_code == 200
        providers = response.json()["providers"]
        assert "google_calendar" in providers
        assert "google_sheets" in providers

    def test_list_providers_unauthenticated(self, client_unauthenticated):
        """Providers endpoint has no auth dependency — should still work."""
        response = client_unauthenticated.get("/api/v1/oauth/providers")
        assert response.status_code == 200
        assert "providers" in response.json()


# ─── GET /api/v1/oauth/{provider}/authorize ───

class TestAuthorize:
    """Tests for GET /api/v1/oauth/{provider}/authorize"""

    def test_authorize_unsupported_provider(self, client_as_member):
        response = client_as_member.get("/api/v1/oauth/unsupported_provider/authorize")
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    def test_authorize_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/oauth/google_calendar/authorize")
        assert response.status_code in (401, 403)

    def test_authorize_google_calendar(self, client_as_member):
        """If Google OAuth credentials are configured, returns an auth_url."""
        response = client_as_member.get("/api/v1/oauth/google_calendar/authorize")
        # 200 if credentials configured, 500 if not
        if response.status_code == 200:
            result = response.json()
            assert "auth_url" in result
            assert "accounts.google.com" in result["auth_url"]
            assert "client_id" in result["auth_url"]
            assert "redirect_uri" in result["auth_url"]
        else:
            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]

    def test_authorize_google_sheets(self, client_as_member):
        """If Google OAuth credentials are configured, returns an auth_url."""
        response = client_as_member.get("/api/v1/oauth/google_sheets/authorize")
        if response.status_code == 200:
            result = response.json()
            assert "auth_url" in result
            assert "accounts.google.com" in result["auth_url"]
        else:
            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]

    def test_authorize_returns_correct_state(self, client_as_member):
        """State parameter should contain org_id:user_id:provider."""
        response = client_as_member.get("/api/v1/oauth/google_calendar/authorize")
        if response.status_code == 200:
            auth_url = response.json()["auth_url"]
            assert "state=" in auth_url
            assert "google_calendar" in auth_url


# ─── GET /api/v1/oauth/{provider}/callback ───

class TestCallback:
    """Tests for GET /api/v1/oauth/{provider}/callback"""

    def test_callback_unsupported_provider(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/oauth/unsupported_provider/callback",
            params={"code": "fake_code", "state": f"{ORG_ID}:{REAL_USER_ID}:unsupported_provider"},
        )
        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]

    def test_callback_invalid_state_format(self, client_as_member):
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
        """A fake authorization code should fail during token exchange."""
        response = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={
                "code": "fake_authorization_code",
                "state": f"{ORG_ID}:{REAL_USER_ID}:google_calendar",
            },
        )
        assert response.status_code == 400
        assert "Token exchange failed" in response.json().get("detail", "")
