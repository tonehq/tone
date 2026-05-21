"""Tests for Dashboard API endpoints (Core edition).

Source: core/api/v1/dashboard.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_stats():
    return {
        "total_agents": 5,
        "active_calls": 2,
        "minutes_used": 1250,
        "success_rate": 94.5,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/stats
# ---------------------------------------------------------------------------

class TestGetDashboardStats:
    """Tests for GET /api/v1/dashboard/stats"""

    @patch("core.api.v1.dashboard.DashboardService")
    def test_success(self, mock_service_cls, client_as_member, sample_stats):
        mock_service_cls.return_value.get_stats.return_value = sample_stats
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_agents"] == 5
        assert data["active_calls"] == 2
        assert data["minutes_used"] == 1250
        assert data["success_rate"] == 94.5

    @patch("core.api.v1.dashboard.DashboardService")
    def test_empty_stats(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_stats.return_value = {
            "total_agents": 0,
            "active_calls": 0,
            "minutes_used": 0,
            "success_rate": 0.0,
        }
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_agents"] == 0

    @patch("core.api.v1.dashboard.DashboardService")
    def test_as_admin(self, mock_service_cls, client_as_admin, sample_stats):
        mock_service_cls.return_value.get_stats.return_value = sample_stats
        resp = client_as_admin.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        assert resp.json()["total_agents"] == 5

    @patch("core.api.v1.dashboard.DashboardService")
    def test_as_owner(self, mock_service_cls, client_as_owner, sample_stats):
        mock_service_cls.return_value.get_stats.return_value = sample_stats
        resp = client_as_owner.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200
        assert resp.json()["total_agents"] == 5

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/dashboard/stats")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.dashboard.DashboardService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_stats.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/dashboard/stats")
        assert resp.status_code in (500, 422, 400)
