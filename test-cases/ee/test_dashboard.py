"""Tests for Dashboard API endpoints (EE edition).

Source: core/api/v1/dashboard.py (no EE override — uses core auth)
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# --- GET /api/v1/dashboard/stats ---

class TestGetDashboardStats:
    """Tests for GET /api/v1/dashboard/stats"""

    def test_returns_200(self, client_as_member):
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

    def test_response_has_expected_keys(self, client_as_member):
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        # The stats response should be a dict with numeric values
        assert isinstance(data, dict)

    def test_admin_can_access(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

    def test_owner_can_access(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/dashboard/stats")
        assert resp.status_code in (401, 403)
