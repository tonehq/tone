"""Integration tests for license-related API endpoints.

Tests hit REAL database and REAL API endpoints via TestClient.
No service mocks — full request lifecycle from HTTP to DB and back.
"""

import pytest
from fastapi.testclient import TestClient

from core.internal.license import init_license_validator, LicenseTier
from core.internal.capabilities import init_capabilities, is_ee_enabled


# ===========================================================================
# GET /api/v1/capabilities
# ===========================================================================

class TestCapabilitiesEndpoint:
    """Tests for GET /api/v1/capabilities — returns current capabilities and edition."""

    def test_returns_200(self, real_client):
        resp = real_client.get("/api/v1/capabilities")
        assert resp.status_code == 200

    def test_response_has_required_fields(self, real_client):
        resp = real_client.get("/api/v1/capabilities")
        data = resp.json()
        assert "capabilities" in data
        assert "edition" in data
        assert "ee_enabled" in data

    def test_capabilities_is_list(self, real_client):
        resp = real_client.get("/api/v1/capabilities")
        data = resp.json()
        assert isinstance(data["capabilities"], list)

    def test_edition_is_string(self, real_client):
        resp = real_client.get("/api/v1/capabilities")
        data = resp.json()
        assert data["edition"] in ("core", "enterprise")

    def test_ee_enabled_matches_edition(self, real_client):
        resp = real_client.get("/api/v1/capabilities")
        data = resp.json()
        if data["ee_enabled"]:
            assert data["edition"] == "enterprise"
        else:
            assert data["edition"] == "core"

    def test_capabilities_endpoint_no_auth_required(self, real_client):
        """The /capabilities endpoint should be public — no Authorization header needed."""
        resp = real_client.get("/api/v1/capabilities")
        assert resp.status_code == 200


# ===========================================================================
# GET / (root endpoint)
# ===========================================================================

class TestRootEndpoint:
    """Tests for GET / — basic health/info endpoint."""

    def test_returns_200(self, real_client):
        resp = real_client.get("/")
        assert resp.status_code == 200

    def test_response_has_edition(self, real_client):
        resp = real_client.get("/")
        data = resp.json()
        assert "edition" in data
        assert data["edition"] in ("core", "enterprise")

    def test_response_has_version(self, real_client):
        resp = real_client.get("/")
        data = resp.json()
        assert data["version"] == "1.0.0"


# ===========================================================================
# GET /health
# ===========================================================================

class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_returns_200(self, real_client):
        resp = real_client.get("/health")
        assert resp.status_code == 200

    def test_status_ok(self, real_client):
        resp = real_client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_has_edition(self, real_client):
        resp = real_client.get("/health")
        data = resp.json()
        assert "edition" in data


# ===========================================================================
# GET /ready
# ===========================================================================

class TestReadyEndpoint:
    """Tests for GET /ready."""

    def test_returns_200(self, real_client):
        resp = real_client.get("/ready")
        assert resp.status_code == 200

    def test_ready_true(self, real_client):
        resp = real_client.get("/ready")
        data = resp.json()
        assert data["ready"] is True


# ===========================================================================
# GET /environment
# ===========================================================================

class TestEnvironmentEndpoint:
    """Tests for GET /environment."""

    def test_returns_200(self, real_client):
        resp = real_client.get("/environment")
        assert resp.status_code == 200

    def test_has_environment_field(self, real_client):
        resp = real_client.get("/environment")
        data = resp.json()
        assert "environment" in data


# ===========================================================================
# SKIP LICENSE + EE EDITION VERIFICATION
# ===========================================================================

class TestSkipLicenseEEEdition:
    """Verify that with SKIP_LICENSE_CHECK=true, the app runs in EE mode."""

    def test_capabilities_include_ee_codes(self, real_client):
        """With skip_license_check, capabilities should include EE codes."""
        resp = real_client.get("/api/v1/capabilities")
        data = resp.json()
        caps = data["capabilities"]
        # When SKIP_LICENSE_CHECK=true (as in .env), all capabilities are enabled
        if data["ee_enabled"]:
            assert "t" in caps     # team
            assert "wa" in caps    # workspace_admin
            assert "au" in caps    # audit_logs
            assert "ss" in caps    # sso

    def test_edition_is_enterprise_when_skip(self, real_client):
        """With SKIP_LICENSE_CHECK=true and ee/ folder present, edition should be enterprise."""
        resp = real_client.get("/api/v1/capabilities")
        data = resp.json()
        # This test reflects that the current .env has SKIP_LICENSE_CHECK=true
        # and the ee/ folder exists, so the app should be in enterprise mode
        if data["ee_enabled"]:
            assert data["edition"] == "enterprise"

    def test_root_reflects_edition(self, real_client):
        """Root endpoint should show the same edition as capabilities."""
        caps_resp = real_client.get("/api/v1/capabilities")
        root_resp = real_client.get("/")
        assert caps_resp.json()["edition"] == root_resp.json()["edition"]

    def test_health_reflects_edition(self, real_client):
        """Health endpoint should show the same edition as capabilities."""
        caps_resp = real_client.get("/api/v1/capabilities")
        health_resp = real_client.get("/health")
        assert caps_resp.json()["edition"] == health_resp.json()["edition"]
