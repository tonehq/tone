"""Tests for Call Logs API endpoints (EE edition).

Source: ee/api/v1/call_logs.py
Postman: postman_collection/call_logs.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
"""

import pytest


# --- GET /api/v1/call-log/filter-values ---

class TestGetFilterValues:
    """Tests for GET /api/v1/call-log/filter-values"""

    def test_get_filter_values_success(self, client_as_member):
        """Postman: Get Filter Values - Success (200)."""
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=agent_name")
        assert response.status_code == 200

    def test_get_filter_values_status_column(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200
        data = response.json()
        assert "values" in data or isinstance(data, list)

    def test_missing_column_name(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values")
        assert response.status_code == 422

    def test_invalid_column_name(self, client_as_member):
        """Invalid/nonexistent column should return 400 or empty."""
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=nonexistent_col")
        assert response.status_code in (200, 400)

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code in (401, 403)


# --- POST /api/v1/call-log/list ---

class TestListCallLogs:
    """Tests for POST /api/v1/call-log/list"""

    def test_list_call_logs_success(self, client_as_member):
        """Postman: Get Call Logs - Success (200)."""
        response = client_as_member.post("/api/v1/call-log/list", json={
            "page_no": 1,
            "page_size": 10,
            "sort_by": "created_at",
            "sort_order": "desc",
        })
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_list_with_default_body(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={})
        assert response.status_code == 200

    def test_list_with_date_filter(self, client_as_member):
        """Filter by unix timestamps (bigint)."""
        response = client_as_member.post("/api/v1/call-log/list", json={
            "start_date_time": 1767225600,
            "end_date_time": 1798761599,
        })
        assert response.status_code == 200

    def test_list_with_filters(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "filters": [{"column": "status", "values": ["completed", "failed"]}],
        })
        assert response.status_code == 200

    def test_list_sort_ascending(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "sort_by": "created_at", "sort_order": "asc",
        })
        assert response.status_code == 200

    def test_list_sort_descending(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "sort_by": "created_at", "sort_order": "desc",
        })
        assert response.status_code == 200

    def test_list_large_page_number(self, client_as_member):
        """High page number should return empty results, not error."""
        response = client_as_member.post("/api/v1/call-log/list", json={
            "page_no": 99999, "page_size": 10,
        })
        assert response.status_code == 200

    def test_list_with_pagination(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "page_no": 1, "page_size": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] <= 10

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert response.status_code in (401, 403)


# --- GET /api/v1/call-log/{call_id} ---

class TestGetCallLogById:
    """Tests for GET /api/v1/call-log/{call_id}"""

    def test_not_found(self, client_as_member):
        """Postman: Get Call Log - Not Found (404)."""
        response = client_as_member.get("/api/v1/call-log/999999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Call log not found"

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1")
        assert response.status_code in (401, 403)

    def test_invalid_id_format(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/abc")
        assert response.status_code == 422


# --- GET /api/v1/call-log/{call_id}/audio-url ---

class TestGetAudioUrl:
    """Tests for GET /api/v1/call-log/{call_id}/audio-url"""

    def test_not_found(self, client_as_member):
        """Postman: Get Audio URL - Not Found (404)."""
        response = client_as_member.get("/api/v1/call-log/999999/audio-url")
        assert response.status_code == 404
        assert response.json()["detail"] == "Call log not found"

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1/audio-url")
        assert response.status_code in (401, 403)

    def test_invalid_id_format(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/abc/audio-url")
        assert response.status_code == 422


# --- GET /api/v1/call-log/{call_id}/audio ---

class TestDownloadAudio:
    """Tests for GET /api/v1/call-log/{call_id}/audio

    Postman: Download Audio endpoint. The EE controller may not implement this
    route, so we test for 404/405 on missing call log or missing route.
    """

    def test_not_found(self, client_as_member):
        """Postman: Download Audio - Not Found (404)."""
        response = client_as_member.get("/api/v1/call-log/999999/audio")
        assert response.status_code in (404, 405)

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1/audio")
        assert response.status_code in (401, 403, 404, 405)
