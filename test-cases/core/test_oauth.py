"""Tests for OAuth API endpoints (Core edition).

Source: core/api/v1/oauth.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_connection():
    return {
        "id": 1,
        "provider": "google_calendar",
        "user_email": "user@gmail.com",
        "scopes": "https://www.googleapis.com/auth/calendar",
        "created_at": "2026-01-15T10:00:00",
        "updated_at": "2026-01-15T10:00:00",
    }


@pytest.fixture
def sample_connections(sample_connection):
    return [sample_connection]


@pytest.fixture
def sample_providers():
    return [
        {
            "name": "google_calendar",
            "display_name": "Google Calendar",
            "scopes": "https://www.googleapis.com/auth/calendar",
        }
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/oauth/connections
# ---------------------------------------------------------------------------

class TestGetConnections:
    """Tests for GET /api/v1/oauth/connections"""

    @patch("ee.api.v1.oauth.OAuthService")
    def test_success(self, mock_service_cls, client_as_member, sample_connections):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_connections.return_value = sample_connections
        mock_svc.connection_response.side_effect = lambda c: c
        resp = client_as_member.get("/api/v1/oauth/connections")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1

    @patch("ee.api.v1.oauth.OAuthService")
    def test_with_provider_filter(self, mock_service_cls, client_as_member, sample_connections):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_connections.return_value = sample_connections
        mock_svc.connection_response.side_effect = lambda c: c
        resp = client_as_member.get("/api/v1/oauth/connections", params={"provider": "google_calendar"})
        assert resp.status_code == 200
        mock_svc.get_connections.assert_called_once_with(provider="google_calendar", user_id=ANY)

    @patch("ee.api.v1.oauth.OAuthService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_connections.return_value = []
        resp = client_as_member.get("/api/v1/oauth/connections")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/oauth/connections")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.oauth.OAuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_connections.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get("/api/v1/oauth/connections")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/oauth/connection
# ---------------------------------------------------------------------------

class TestGetConnectionByProvider:
    """Tests for GET /api/v1/oauth/connection"""

    @patch("ee.api.v1.oauth.OAuthService")
    def test_connected(self, mock_service_cls, client_as_member, sample_connection):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_connection_by_provider.return_value = sample_connection
        mock_svc.connection_response.return_value = sample_connection
        resp = client_as_member.get("/api/v1/oauth/connection", params={"provider": "google_calendar"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True

    @patch("ee.api.v1.oauth.OAuthService")
    def test_not_connected(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_connection_by_provider.return_value = None
        resp = client_as_member.get("/api/v1/oauth/connection", params={"provider": "google_calendar"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["provider"] == "google_calendar"

    def test_missing_provider(self, client_as_member):
        resp = client_as_member.get("/api/v1/oauth/connection")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/oauth/connection", params={"provider": "google_calendar"})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/oauth/disconnect
# ---------------------------------------------------------------------------

class TestDisconnect:
    """Tests for DELETE /api/v1/oauth/disconnect"""

    @patch("ee.api.v1.oauth.OAuthService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.delete_connection.return_value = {"message": "Connection deleted successfully"}
        resp = client_as_member.delete("/api/v1/oauth/disconnect", params={"connection_id": 1})
        assert resp.status_code == 200
        assert "message" in resp.json()
        mock_svc.delete_connection.assert_called_once_with(1)

    @patch("ee.api.v1.oauth.OAuthService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.delete_connection.side_effect = HTTPException(status_code=404, detail="Connection not found")
        resp = client_as_member.delete("/api/v1/oauth/disconnect", params={"connection_id": 999})
        assert resp.status_code == 404

    def test_missing_connection_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/oauth/disconnect")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/oauth/disconnect", params={"connection_id": 1})
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.oauth.OAuthService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.delete_connection.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.delete("/api/v1/oauth/disconnect", params={"connection_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/oauth/providers
# ---------------------------------------------------------------------------

class TestListProviders:
    """Tests for GET /api/v1/oauth/providers"""

    @patch("ee.api.v1.oauth.get_supported_providers")
    def test_success(self, mock_get_providers, client_as_member, sample_providers):
        mock_get_providers.return_value = sample_providers
        resp = client_as_member.get("/api/v1/oauth/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)


# ---------------------------------------------------------------------------
# GET /api/v1/oauth/{provider}/authorize
# ---------------------------------------------------------------------------

class TestAuthorize:
    """Tests for GET /api/v1/oauth/{provider}/authorize"""

    @patch("ee.api.v1.oauth.get_provider_config")
    def test_success(self, mock_get_config, client_as_member):
        mock_get_config.return_value = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "https://www.googleapis.com/auth/calendar",
        }
        resp = client_as_member.get("/api/v1/oauth/google_calendar/authorize")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "accounts.google.com" in data["auth_url"]

    @patch("ee.api.v1.oauth.get_provider_config")
    def test_unsupported_provider(self, mock_get_config, client_as_member):
        mock_get_config.return_value = None
        resp = client_as_member.get("/api/v1/oauth/invalid_provider/authorize")
        assert resp.status_code == 400
        assert "Unsupported provider" in resp.json()["detail"]

    @patch("ee.api.v1.oauth.get_provider_config")
    def test_missing_credentials(self, mock_get_config, client_as_member):
        mock_get_config.return_value = {
            "client_id": None,
            "client_secret": None,
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "https://www.googleapis.com/auth/calendar",
        }
        resp = client_as_member.get("/api/v1/oauth/google_calendar/authorize")
        assert resp.status_code == 500
        assert "not configured" in resp.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/oauth/google_calendar/authorize")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/oauth/{provider}/callback
# ---------------------------------------------------------------------------

class TestCallback:
    """Tests for GET /api/v1/oauth/{provider}/callback"""

    @patch("ee.api.v1.oauth.OAuthService")
    @patch("ee.api.v1.oauth.get_provider_config")
    @patch("ee.api.v1.oauth.httpx")
    def test_success_redirect(self, mock_httpx, mock_get_config, mock_service_cls, client_as_member):
        mock_get_config.return_value = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "https://www.googleapis.com/auth/calendar",
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = MagicMock(status_code=200, json=lambda: {"email": "user@gmail.com"})
        mock_httpx.Client.return_value = mock_client

        mock_svc = mock_service_cls.return_value
        mock_svc.create_connection.return_value = MagicMock()

        state = "550e8400-e29b-41d4-a716-446655440000:1:google_calendar"
        resp = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "auth_code_here", "state": state},
            follow_redirects=False,
        )
        assert resp.status_code == 307

    @patch("ee.api.v1.oauth.get_provider_config")
    def test_unsupported_provider(self, mock_get_config, client_as_member):
        mock_get_config.return_value = None
        resp = client_as_member.get(
            "/api/v1/oauth/invalid_provider/callback",
            params={"code": "auth_code", "state": "org:1:invalid_provider"},
        )
        assert resp.status_code == 400

    @patch("ee.api.v1.oauth.get_provider_config")
    def test_invalid_state(self, mock_get_config, client_as_member):
        mock_get_config.return_value = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "https://www.googleapis.com/auth/calendar",
        }
        resp = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "auth_code", "state": "invalid_state"},
        )
        assert resp.status_code == 400
        assert "Invalid state" in resp.json()["detail"]

    @patch("ee.api.v1.oauth.get_provider_config")
    def test_provider_mismatch(self, mock_get_config, client_as_member):
        mock_get_config.return_value = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": "https://www.googleapis.com/auth/calendar",
        }
        state = "550e8400-e29b-41d4-a716-446655440000:1:other_provider"
        resp = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "auth_code", "state": state},
        )
        assert resp.status_code == 400
        assert "Provider mismatch" in resp.json()["detail"]

    def test_missing_code(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"state": "org:1:google_calendar"},
        )
        assert resp.status_code == 422

    def test_missing_state(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/oauth/google_calendar/callback",
            params={"code": "auth_code"},
        )
        assert resp.status_code == 422
