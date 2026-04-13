"""Tests for Call Logs API endpoints (EE edition).

Source: ee/api/v1/call_logs.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest


# ─── GET /api/v1/call-log/filter-values ───

class TestGetFilterValues:
    """Tests for GET /api/v1/call-log/filter-values"""

    def test_get_filter_values_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200
        data = response.json()
        # Response is {"column": "status", "values": [...]}
        assert "values" in data or isinstance(data, list)

    def test_missing_column_name(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values")
        assert response.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/call-log/list ───

class TestListCallLogs:
    """Tests for POST /api/v1/call-log/list"""

    def test_list_call_logs_returns_200(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={})
        assert response.status_code == 200

    def test_list_with_pagination(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "page_no": 1, "page_size": 10
        })
        assert response.status_code == 200

    def test_list_with_sort(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "sort_by": "created_at", "sort_order": "desc"
        })
        assert response.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert response.status_code in (401, 403)


# ─── GET /api/v1/call-log/{call_id} ───

class TestGetCallLogById:
    """Tests for GET /api/v1/call-log/{call_id}"""

    def test_not_found(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/999999")
        assert response.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/call-log/{call_id}/audio-url ───

class TestGetAudioUrl:
    """Tests for GET /api/v1/call-log/{call_id}/audio-url"""

    def test_not_found(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/999999/audio-url")
        assert response.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1/audio-url")
        assert response.status_code in (401, 403)
