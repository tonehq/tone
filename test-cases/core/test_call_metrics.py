"""Tests for Call Metrics API endpoints (Core edition).

Source: core/api/v1/call_metrics.py
The router is mounted under ``/api/v1/call-metrics`` in both editions and uses
``require_org_member`` for auth.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.internal.capabilities import is_ee_enabled

# main.py mounts the EE router under ``/api/v1/call-metrics`` when EE is
# enabled (license check passed or skipped). Patching has to target whichever
# module actually owns the live handler, otherwise the mock never intercepts
# the service call.
_MODULE = "ee.api.v1.call_metrics" if is_ee_enabled() else "core.api.v1.call_metrics"
_SVC = f"{_MODULE}.CallMetricsService"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_metric_row():
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "call_id": "22222222-2222-2222-2222-222222222222",
        "agent_name": "Sales Agent",
        "agent_type": "inbound",
        "started_at": "2026-06-01T10:00:00+00:00",
        "ended_at": "2026-06-01T10:05:00+00:00",
        "duration_seconds": 300,
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "stt_provider": "deepgram",
        "stt_model": "nova-2",
        "tts_provider": "elevenlabs",
        "tts_model": "eleven_turbo_v2",
        "ttfb": {"avg": 0.42},
        "processing": {"avg": 0.19},
        "llm_usage": {"total_tokens": 1500},
        "tts_usage": {"chars": 6200},
        "user_bot_latency": {"avg": 0.65},
        "turns": 12,
        "turn_metrics": [],
    }


@pytest.fixture
def sample_list_response(sample_metric_row):
    return {
        "items": [sample_metric_row],
        "total": 1,
        "page": 1,
        "page_size": 10,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/call-metrics/list
# ---------------------------------------------------------------------------


class TestListCallMetrics:
    """Tests for POST /api/v1/call-metrics/list"""

    @patch(_SVC)
    def test_list_success_with_defaults(self, mock_service_cls, client_as_member, sample_list_response):
        mock_service_cls.return_value.list_metrics.return_value = sample_list_response

        resp = client_as_member.post("/api/v1/call-metrics/list", json={})

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["call_id"] == "22222222-2222-2222-2222-222222222222"
        # Defaults from the Pydantic schema must be forwarded to the service.
        _, kwargs = mock_service_cls.return_value.list_metrics.call_args
        assert kwargs["page_no"] == 1
        assert kwargs["page_size"] == 10
        assert kwargs["sort_order"] == "desc"
        assert kwargs["filters"] is None

    @patch(_SVC)
    def test_list_success_with_full_body(self, mock_service_cls, client_as_member, sample_list_response):
        mock_service_cls.return_value.list_metrics.return_value = sample_list_response

        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={
                "page_no": 2,
                "page_size": 50,
                "start_date_time": "2026-06-01T00:00:00Z",
                "end_date_time": "2026-06-30T23:59:59Z",
                "filters": [
                    {"field": "agent_name", "operator": "eq", "value": "Sales Agent"},
                ],
                "sort_by": "started_at",
                "sort_order": "asc",
            },
        )

        assert resp.status_code == 200
        _, kwargs = mock_service_cls.return_value.list_metrics.call_args
        assert kwargs["page_no"] == 2
        assert kwargs["page_size"] == 50
        assert kwargs["sort_by"] == "started_at"
        assert kwargs["sort_order"] == "asc"
        # Filters should arrive as dicts (the route dumps each Pydantic filter).
        assert kwargs["filters"] == [
            {"field": "agent_name", "operator": "eq", "value": "Sales Agent"},
        ]

    @patch(_SVC)
    def test_list_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.list_metrics.return_value = {
            "items": [], "total": 0, "page": 1, "page_size": 10,
        }
        resp = client_as_member.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_page_no_below_minimum(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list", json={"page_no": 0},
        )
        assert resp.status_code == 422

    def test_list_page_size_above_maximum(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list", json={"page_size": 101},
        )
        assert resp.status_code == 422

    def test_list_invalid_sort_order(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/call-metrics/list", json={"sort_order": "sideways"},
        )
        assert resp.status_code == 422

    def test_list_filter_missing_required_field(self, client_as_member):
        """Filter entries must contain field/operator/value — partial entry should 422."""
        resp = client_as_member.post(
            "/api/v1/call-metrics/list",
            json={"filters": [{"field": "agent_name"}]},
        )
        assert resp.status_code == 422

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/call-metrics/list", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/call-metrics/{call_id}
# ---------------------------------------------------------------------------


class TestGetMetricsForCall:
    """Tests for GET /api/v1/call-metrics/{call_id}"""

    @patch(_SVC)
    def test_success(self, mock_service_cls, client_as_member, sample_metric_row):
        mock_service_cls.return_value.get_by_call_id.return_value = sample_metric_row

        resp = client_as_member.get(
            "/api/v1/call-metrics/22222222-2222-2222-2222-222222222222"
        )

        assert resp.status_code == 200
        assert resp.json()["call_id"] == "22222222-2222-2222-2222-222222222222"
        mock_service_cls.return_value.get_by_call_id.assert_called_once_with(
            call_id="22222222-2222-2222-2222-222222222222"
        )

    @patch(_SVC)
    def test_not_found(self, mock_service_cls, client_as_member):
        """The route raises 404 when the service returns a falsy result."""
        mock_service_cls.return_value.get_by_call_id.return_value = None

        resp = client_as_member.get(
            "/api/v1/call-metrics/99999999-9999-9999-9999-999999999999"
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Metrics not found for this call"

    @patch(_SVC)
    def test_empty_dict_treated_as_not_found(self, mock_service_cls, client_as_member):
        """An empty dict is falsy too, so it must surface as 404 instead of a 200 with {}."""
        mock_service_cls.return_value.get_by_call_id.return_value = {}

        resp = client_as_member.get(
            "/api/v1/call-metrics/22222222-2222-2222-2222-222222222222"
        )

        assert resp.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/call-metrics/22222222-2222-2222-2222-222222222222"
        )
        assert resp.status_code in (401, 403)
