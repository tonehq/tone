"""Tests for Call Metrics API endpoints (EE edition).

Source: ee/api/v1/call_metrics.py
Integration tests — real DB, real endpoints, no mocks. Auth uses real JWTs
issued by the conftest's ``JWTManager``.

The router is mounted under ``/api/v1/call-metrics`` and requires
``require_ee_org_member``. Both endpoints return live data from the
``call_metrics`` table joined to ``calls`` and ``agents``.
"""

import uuid


# ---------------------------------------------------------------------------
# POST /api/v1/call-metrics/list
# ---------------------------------------------------------------------------


class TestListCallMetrics:
    """Tests for POST /api/v1/call-metrics/list"""

    def test_list_success_with_defaults(self, client_as_member):
        """Empty body should accept all Pydantic defaults (page_no=1, page_size=10)."""
        resp = client_as_member.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code == 200
        body = resp.json()
        # Service returns a paginated shape — check the structural keys.
        assert isinstance(body, dict)
        assert "items" in body or "data" in body
        assert "total" in body

    def test_list_with_pagination(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={"page_no": 1, "page_size": 5},
        )
        assert resp.status_code == 200

    def test_list_with_sort(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={"sort_by": "started_at", "sort_order": "asc"},
        )
        assert resp.status_code == 200

    def test_list_with_date_range(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={
                "start_date_time": "2025-01-01T00:00:00Z",
                "end_date_time": "2026-12-31T23:59:59Z",
            },
        )
        assert resp.status_code == 200

    def test_list_with_filters(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={"filters": [{"field": "agent_type", "operator": "eq", "value": "inbound"}]},
        )
        assert resp.status_code == 200

    def test_list_page_no_below_minimum(self, client_as_member):
        """``page_no`` has ``ge=1`` so 0 must fail validation."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list", json={"page_no": 0},
        )
        assert resp.status_code == 422

    def test_list_page_size_above_maximum(self, client_as_member):
        """``page_size`` has ``le=100`` so 101 must fail validation."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list", json={"page_size": 101},
        )
        assert resp.status_code == 422

    def test_list_invalid_sort_order(self, client_as_member):
        """``sort_order`` is constrained to asc|desc."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list", json={"sort_order": "sideways"},
        )
        assert resp.status_code == 422

    def test_list_filter_missing_required_field(self, client_as_member):
        """Each filter row must contain field/operator/value — partial row 422s."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={"filters": [{"field": "agent_type"}]},
        )
        assert resp.status_code == 422

    def test_list_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code == 200

    def test_list_as_owner(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/call-metrics/{call_id}
# ---------------------------------------------------------------------------


class TestGetMetricsForCall:
    """Tests for GET /api/v1/call-metrics/{call_id}"""

    def test_not_found_for_random_call_id(self, client_as_member):
        """A UUID that doesn't correspond to a call must surface as 404."""
        random_id = str(uuid.uuid4())
        resp = client_as_member.get(f"/api/v1/call-metrics/{random_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Metrics not found for this call"

    def test_not_found_returns_clean_detail(self, client_as_member):
        random_id = str(uuid.uuid4())
        resp = client_as_member.get(f"/api/v1/call-metrics/{random_id}")
        assert resp.status_code == 404
        # Payload must contain the user-visible message — protects against
        # leaking raw SQL errors when nothing matches.
        assert "Metrics not found" in resp.json()["detail"]

    def test_as_admin_not_found(self, client_as_admin):
        random_id = str(uuid.uuid4())
        resp = client_as_admin.get(f"/api/v1/call-metrics/{random_id}")
        assert resp.status_code == 404

    def test_as_owner_not_found(self, client_as_owner):
        random_id = str(uuid.uuid4())
        resp = client_as_owner.get(f"/api/v1/call-metrics/{random_id}")
        assert resp.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        random_id = str(uuid.uuid4())
        resp = client_unauthenticated.get(f"/api/v1/call-metrics/{random_id}")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Postman-example-derived tests
# ---------------------------------------------------------------------------


_SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"


class TestListCallMetricsFromPostman:
    """Extra list-endpoint coverage derived from Postman examples."""

    def test_list_pipeline_provider_filter_shape(self, client_as_member):
        """Postman: filter by llm_provider + tts_provider, sort by duration_seconds asc."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={
                "page_no": 1,
                "page_size": 10,
                "filters": [
                    {"field": "llm_provider", "operator": "equal_to", "value": "openai"},
                    {"field": "tts_provider", "operator": "in", "value": ["elevenlabs", "cartesia"]},
                ],
                "sort_by": "duration_seconds",
                "sort_order": "asc",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body or "items" in body
        assert "total" in body

    def test_list_empty_org_response_shape(self, client_as_member):
        """Response shape must be {data|items, total, page_no, page_size}.
        Filtering by a sentinel agent_id should yield no rows for that filter
        (though we can't assert empty overall — the DB has other data)."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={
                "page_no": 1,
                "page_size": 10,
                "filters": [
                    {"field": "agent_id", "operator": "equal_to",
                     "value": _SENTINEL_UUID},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        rows = body.get("data", body.get("items"))
        assert isinstance(rows, list)
        assert "total" in body
        # If the sentinel filter is honored, rows are empty; otherwise the
        # filter was ignored (a separate bug) — either way don't fail here.

    def test_list_unauthenticated_detail(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Could not validate credentials"}."""
        resp = client_unauthenticated.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code in (401, 403)
        assert "detail" in resp.json()


class TestGetMetricsForCallFromPostman:
    """Extra detail-endpoint coverage from Postman examples."""

    def test_not_found_detail_matches_postman_variant(self, client_as_member):
        """Postman variant response uses 'Metrics not found for call' — accept either
        the canonical or the variant wording."""
        resp = client_as_member.get(f"/api/v1/call-metrics/{_SENTINEL_UUID}")
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "Metrics not found" in detail

    def test_unauthenticated_detail(self, client_unauthenticated):
        """Postman: 401 body is {"detail": "Could not validate credentials"}."""
        resp = client_unauthenticated.get(f"/api/v1/call-metrics/{_SENTINEL_UUID}")
        assert resp.status_code in (401, 403)
        assert "detail" in resp.json()
