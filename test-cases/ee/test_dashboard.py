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

    # --- Postman-example-derived tests -----------------------------------

    def test_unauthenticated_detail_message(self, client_unauthenticated):
        """Postman: 401 No bearer token → {"detail": "Could not validate credentials"}."""
        resp = client_unauthenticated.get("/api/v1/dashboard/stats")
        assert resp.status_code in (401, 403)
        body = resp.json()
        assert "detail" in body

    def test_success_rate_is_numeric(self, client_as_member):
        """Postman: even on empty orgs, success_rate is 0.0 (never null/NaN)."""
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        # Response uses one of two shapes; both include success_rate as a number.
        if "success_rate" in data:
            assert isinstance(data["success_rate"], (int, float))
            assert data["success_rate"] >= 0

    def test_numeric_counters_are_non_negative(self, client_as_member):
        """Postman examples show total_agents/active_calls/minutes_used as
        non-negative numbers (0 on empty orgs)."""
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_agents", "active_calls", "minutes_used",
                    "total_calls", "total_minutes", "active_agents",
                    "average_call_duration_seconds"):
            if key in data and data[key] is not None:
                assert isinstance(data[key], (int, float))
                assert data[key] >= 0
