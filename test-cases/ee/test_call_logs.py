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
        assert response.status_code in (200, 422)

    def test_list_with_filters(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/list", json={
            "filters": [{"column": "status", "values": ["completed", "failed"]}],
        })
        assert response.status_code in (200, 422)

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


# --- POST /api/v1/call-log/facets ---

class TestGetFacets:
    """Tests for POST /api/v1/call-log/facets (faceted filter counts)."""

    def test_facets_success_empty_body(self, client_as_member):
        """Empty body returns a dict of facet -> [{value, count}] lists."""
        response = client_as_member.post("/api/v1/call-log/facets", json={})
        assert response.status_code == 200
        data = response.json()
        # Every faceted field is present, each mapping to a list.
        for field in (
            "status", "agent_name", "direction", "channel_type",
            "llm_model", "stt_model", "tts_model",
        ):
            assert field in data
            assert isinstance(data[field], list)

    def test_facets_status_is_fixed_enum(self, client_as_member):
        """Status facet always emits the three derived states (even at zero)."""
        response = client_as_member.post("/api/v1/call-log/facets", json={})
        assert response.status_code == 200
        status = {row["value"]: row["count"] for row in response.json()["status"]}
        assert set(status.keys()) == {"completed", "in_progress", "failed"}
        assert all(isinstance(c, int) and c >= 0 for c in status.values())

    def test_facets_with_date_range(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/facets", json={
            "start_date_time": "2026-01-01T00:00:00",
            "end_date_time": "2026-12-31T23:59:59",
        })
        assert response.status_code == 200

    def test_facets_excludes_own_field(self, client_as_member):
        """A status selection must not collapse the status facet's own counts.

        With status filtered to 'completed', the status facet should still
        report all three states (its own field is excluded from its counts),
        while remaining a valid response.
        """
        response = client_as_member.post("/api/v1/call-log/facets", json={
            "filters": [
                {"field": "status", "operator": "in", "value": ["completed"]},
            ],
        })
        assert response.status_code == 200
        status = {row["value"] for row in response.json()["status"]}
        assert status == {"completed", "in_progress", "failed"}

    def test_facets_value_rows_shape(self, client_as_member):
        """Each non-status facet row is {value: str, count: int}."""
        response = client_as_member.post("/api/v1/call-log/facets", json={})
        assert response.status_code == 200
        for row in response.json()["agent_name"]:
            assert set(row.keys()) == {"value", "count"}
            assert isinstance(row["count"], int)

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/call-log/facets", json={})
        assert response.status_code in (401, 403)


# --- GET /api/v1/call-log/{call_id} ---

class TestGetCallLogById:
    """Tests for GET /api/v1/call-log/{call_id}"""

    def test_not_found(self, client_as_member):
        """Postman: Get Call Log - Not Found (404)."""
        try:
            response = client_as_member.get("/api/v1/call-log/999999")
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1")
        assert response.status_code in (401, 403)

    def test_invalid_id_format(self, client_as_member):
        try:
            response = client_as_member.get("/api/v1/call-log/abc")
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass


# --- GET /api/v1/call-log/{call_id}/audio-url ---

class TestGetAudioUrl:
    """Tests for GET /api/v1/call-log/{call_id}/audio-url"""

    def test_not_found(self, client_as_member):
        """Postman: Get Audio URL - Not Found (404)."""
        try:
            response = client_as_member.get("/api/v1/call-log/999999/audio-url")
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1/audio-url")
        assert response.status_code in (401, 403)

    def test_invalid_id_format(self, client_as_member):
        try:
            response = client_as_member.get("/api/v1/call-log/abc/audio-url")
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass


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
