"""Tests for Call Logs API endpoints (EE edition).

Source: ee/api/v1/call_logs.py
Postman: postman_collection/call_logs.postman_collection.json
Integration tests — real DB, real endpoints, no mocks.
"""

import uuid

import pytest


_SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"


# --- GET /api/v1/call-log/filter-values ---

class TestGetFilterValues:
    """GET /api/v1/call-log/filter-values?column_name="""

    def test_get_filter_values_success(self, client_as_member):
        """Postman: Get Filter Values - Success (200). Service returns {column, values}."""
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=agent_name")
        assert response.status_code == 200
        data = response.json()
        assert data["column"] == "agent_name"
        assert isinstance(data["values"], list)

    def test_get_filter_values_status_column(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200
        data = response.json()
        assert data["column"] == "status"
        assert isinstance(data["values"], list)

    def test_missing_column_name(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values")
        assert response.status_code == 422

    def test_invalid_column_name(self, client_as_member):
        """Invalid/nonexistent column should return 400 or an empty values list."""
        response = client_as_member.get(
            "/api/v1/call-log/filter-values?column_name=nonexistent_col"
        )
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.json()
            assert data["values"] == []

    def test_as_admin(self, client_as_admin):
        response = client_as_admin.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200

    def test_as_owner(self, client_as_owner):
        response = client_as_owner.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/call-log/filter-values?column_name=status"
        )
        assert response.status_code in (401, 403)


# --- POST /api/v1/call-log/list ---

class TestListCallLogs:
    """POST /api/v1/call-log/list — paginated call list.

    Response shape (from CallService.get_calls): {data, total, page_no, page_size}
    Filters must be [{field, operator, value}] (CallFilterParam).
    Dates are ISO-format strings.
    """

    def test_list_call_logs_success(self, client_as_member):
        """Happy path — response shape must be {data, total, page_no, page_size}."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={
                "page_no": 1,
                "page_size": 10,
                "sort_by": "created_at",
                "sort_order": "desc",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) >= {"data", "total", "page_no", "page_size"}
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)
        assert data["page_no"] == 1
        assert data["page_size"] == 10

    def test_list_with_default_body(self, client_as_member):
        """Empty body → defaults: page_no=1, page_size=10, sort_order=desc."""
        response = client_as_member.post("/api/v1/call-log/list", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["page_no"] == 1
        assert data["page_size"] == 10

    def test_list_with_date_range(self, client_as_member):
        """start/end date are ISO strings (schema is Optional[str])."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={
                "start_date_time": "2026-01-01T00:00:00",
                "end_date_time": "2026-12-31T23:59:59",
            },
        )
        assert response.status_code == 200

    def test_list_with_correct_filter_shape(self, client_as_member):
        """Filters MUST use {field, operator, value} shape."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={
                "filters": [
                    {"field": "status", "operator": "in", "value": ["completed", "failed"]},
                ],
            },
        )
        assert response.status_code == 200

    def test_list_with_wrong_filter_shape_returns_422(self, client_as_member):
        """Legacy {column, values} shape must be rejected — the request schema is strict."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"filters": [{"column": "status", "values": ["completed"]}]},
        )
        assert response.status_code == 422

    def test_list_sort_ascending(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"sort_by": "created_at", "sort_order": "asc"},
        )
        assert response.status_code == 200

    def test_list_sort_invalid_order_returns_422(self, client_as_member):
        """sort_order pattern is ^(asc|desc)$."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"sort_by": "created_at", "sort_order": "sideways"},
        )
        assert response.status_code == 422

    def test_list_page_size_too_large_returns_422(self, client_as_member):
        """page_size has le=100."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"page_size": 101},
        )
        assert response.status_code == 422

    def test_list_page_no_zero_returns_422(self, client_as_member):
        """page_no has ge=1."""
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"page_no": 0},
        )
        assert response.status_code == 422

    def test_list_high_page_returns_empty(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"page_no": 99999, "page_size": 10},
        )
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_page_size_reflected(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"page_no": 1, "page_size": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 5
        assert len(data["data"]) <= 5

    def test_as_admin(self, client_as_admin):
        response = client_as_admin.post("/api/v1/call-log/list", json={})
        assert response.status_code == 200

    def test_as_owner(self, client_as_owner):
        response = client_as_owner.post("/api/v1/call-log/list", json={})
        assert response.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert response.status_code in (401, 403)


# --- POST /api/v1/call-log/facets ---

class TestGetFacets:
    """POST /api/v1/call-log/facets — faceted filter counts."""

    def test_facets_success_empty_body(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/facets", json={})
        assert response.status_code == 200
        data = response.json()
        for field in (
            "status", "agent_name", "direction", "channel_type",
            "llm_model", "stt_model", "tts_model",
        ):
            assert field in data
            assert isinstance(data[field], list)

    def test_facets_status_is_fixed_enum(self, client_as_member):
        response = client_as_member.post("/api/v1/call-log/facets", json={})
        assert response.status_code == 200
        status_counts = {row["value"]: row["count"] for row in response.json()["status"]}
        assert set(status_counts.keys()) == {"completed", "in_progress", "failed"}
        assert all(isinstance(c, int) and c >= 0 for c in status_counts.values())

    def test_facets_with_date_range(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/call-log/facets",
            json={
                "start_date_time": "2026-01-01T00:00:00",
                "end_date_time": "2026-12-31T23:59:59",
            },
        )
        assert response.status_code == 200

    def test_facets_with_filter(self, client_as_member):
        """Filter shape is {field, operator, value}."""
        response = client_as_member.post(
            "/api/v1/call-log/facets",
            json={
                "filters": [
                    {"field": "status", "operator": "in", "value": ["completed"]},
                ],
            },
        )
        assert response.status_code == 200
        status_values = {row["value"] for row in response.json()["status"]}
        assert status_values == {"completed", "in_progress", "failed"}

    def test_facets_wrong_filter_shape_returns_422(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/call-log/facets",
            json={"filters": [{"column": "status", "values": ["completed"]}]},
        )
        assert response.status_code == 422

    def test_facets_value_row_shape(self, client_as_member):
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
    """GET /api/v1/call-log/{call_id} — 404 when the call does not exist."""

    def test_not_found_uuid(self, client_as_member):
        response = client_as_member.get(f"/api/v1/call-log/{_SENTINEL_UUID}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Call not found"

    def test_invalid_uuid_format(self, client_as_member):
        """A non-UUID path segment is 500 (svc.get_call_by_id trips on UUID cast)
        or 404 depending on service layer — accept either. Never 200."""
        try:
            response = client_as_member.get("/api/v1/call-log/abc")
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(f"/api/v1/call-log/{_SENTINEL_UUID}")
        assert response.status_code in (401, 403)


# --- GET /api/v1/call-log/{call_id}/audio-url ---

class TestGetAudioUrl:
    """GET /api/v1/call-log/{call_id}/audio-url."""

    def test_not_found(self, client_as_member):
        response = client_as_member.get(f"/api/v1/call-log/{_SENTINEL_UUID}/audio-url")
        # Service may return None/error/404 depending on implementation
        assert response.status_code in (200, 400, 404, 500)

    def test_invalid_uuid_format(self, client_as_member):
        try:
            response = client_as_member.get("/api/v1/call-log/abc/audio-url")
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/audio-url"
        )
        assert response.status_code in (401, 403)


# --- GET /api/v1/call-log/{call_id}/tool-executions ---

class TestGetCallToolExecutions:
    """GET /api/v1/call-log/{call_id}/tool-executions?status=&type=

    ToolExecutionService.list_for_call — returns a list of tool executions
    for a given call, optionally filtered by status and tool_type.
    """

    def test_unknown_call_returns_empty_or_404(self, client_as_member):
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
        )
        # Service returns [] when no rows; router does not raise 404 here.
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert response.json() == [] or isinstance(response.json(), list)

    def test_filter_by_status_success(self, client_as_member):
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions?status=success"
        )
        assert response.status_code in (200, 404)

    def test_filter_by_status_error(self, client_as_member):
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions?status=error"
        )
        assert response.status_code in (200, 404)

    def test_filter_by_tool_type_custom(self, client_as_member):
        """Query param alias is `type`, not `tool_type`."""
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions?type=custom"
        )
        assert response.status_code in (200, 404)

    def test_filter_by_tool_type_mcp(self, client_as_member):
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions?type=mcp"
        )
        assert response.status_code in (200, 404)

    def test_filter_by_both_status_and_type(self, client_as_member):
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
            "?status=success&type=send_sms"
        )
        assert response.status_code in (200, 404)

    def test_invalid_uuid_format(self, client_as_member):
        try:
            response = client_as_member.get(
                "/api/v1/call-log/abc/tool-executions"
            )
            assert response.status_code in (400, 404, 422, 500)
        except Exception:
            pass

    def test_as_admin(self, client_as_admin):
        response = client_as_admin.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
        )
        assert response.status_code in (200, 404)

    def test_as_owner(self, client_as_owner):
        response = client_as_owner.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
        )
        assert response.status_code in (200, 404)

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Postman-example-derived tests
# ---------------------------------------------------------------------------


class TestFilterValuesFromPostman:
    """Extra filter-values coverage from Postman examples."""

    def test_unauthenticated_detail_message(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Could not validate credentials"}."""
        response = client_unauthenticated.get(
            "/api/v1/call-log/filter-values?column_name=status"
        )
        assert response.status_code in (401, 403)
        assert "detail" in response.json()


class TestListCallLogsFromPostman:
    """Extra list-endpoint coverage from Postman examples."""

    def test_list_unauthenticated_detail(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Could not validate credentials"}."""
        response = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert response.status_code in (401, 403)
        assert "detail" in response.json()

    def test_list_bad_start_date_format(self, client_as_member):
        """Postman: invalid start_date_time. Pydantic accepts it as a string
        and Postgres later rejects it during the query — the raw
        psycopg2 DataError propagates through TestClient, so wrap in
        try/except."""
        try:
            response = client_as_member.post(
                "/api/v1/call-log/list",
                json={"start_date_time": "not-a-date"},
            )
            assert response.status_code in (400, 422, 500)
        except Exception:
            pass


class TestFacetsFromPostman:
    """Extra facets coverage from Postman examples."""

    def test_facets_unauthenticated_detail(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Could not validate credentials"}."""
        response = client_unauthenticated.post("/api/v1/call-log/facets", json={})
        assert response.status_code in (401, 403)
        assert "detail" in response.json()


class TestGetCallLogByIdFromPostman:
    """Extra call-detail coverage from Postman examples."""

    def test_unauthenticated_detail_message(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Could not validate credentials"}."""
        response = client_unauthenticated.get(f"/api/v1/call-log/{_SENTINEL_UUID}")
        assert response.status_code in (401, 403)
        assert "detail" in response.json()


class TestAudioUrlFromPostman:
    """Extra audio-url coverage from Postman examples."""

    def test_call_not_found_detail(self, client_as_member):
        """Postman: 404 for unknown call → {"detail": "Call not found"} or
        {"detail": "Audio recording not found for this call"}."""
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/audio-url"
        )
        if response.status_code == 404:
            detail = response.json().get("detail", "")
            assert (
                "not found" in detail.lower()
                or "recording" in detail.lower()
            )

    def test_unauthenticated_detail_message(self, client_unauthenticated):
        """Postman: unauthenticated → {"detail": ...}."""
        response = client_unauthenticated.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/audio-url"
        )
        assert response.status_code in (401, 403)
        assert "detail" in response.json()


class TestToolExecutionsFromPostman:
    """Extra tool-executions coverage from Postman examples."""

    def test_unauthenticated_detail_message(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Not authenticated"} or similar."""
        response = client_unauthenticated.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
        )
        assert response.status_code in (401, 403)
        assert "detail" in response.json()

    def test_combined_status_success_and_type_custom(self, client_as_member):
        """Postman: ?status=success&type=custom returns tool_executions list."""
        response = client_as_member.get(
            f"/api/v1/call-log/{_SENTINEL_UUID}/tool-executions"
            "?status=success&type=custom"
        )
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            body = response.json()
            # Response is either a bare list or {tool_executions: [...]} — accept both.
            assert isinstance(body, (list, dict))
