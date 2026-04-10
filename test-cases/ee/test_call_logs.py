"""Tests for Call Logs API endpoints (EE edition).

Source: ee/api/v1/call_logs.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# --- Fixtures ---

@pytest.fixture
def sample_call_log():
    return {
        "id": 1,
        "call_id": "call_abc123",
        "agent_name": "Test Agent",
        "duration": 120,
        "status": "completed",
        "audio_file_path": "recordings/call_abc123.wav",
    }


@pytest.fixture
def sample_list_request():
    return {
        "page_no": 1,
        "page_size": 10,
        "filters": {"status": "completed"},
        "sort_by": "created_at",
        "sort_order": "desc",
        "start_date_time": "2025-01-01T00:00:00",
        "end_date_time": "2025-12-31T23:59:59",
    }


# --- GET /api/v1/call-log/filter-values ---

class TestGetFilterValues:
    """Tests for GET /api/v1/call-log/filter-values"""

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_svc, client_as_member):
        mock_svc.return_value.get_filter_values.return_value = ["completed", "failed", "in_progress"]
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)
        mock_svc.return_value.get_filter_values.assert_called_once_with(column_name="status")

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_empty_result(self, mock_svc, client_as_member):
        mock_svc.return_value.get_filter_values.return_value = []
        response = client_as_member.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code == 200
        assert response.json() == []

    def test_missing_column_name(self, client_as_member):
        response = client_as_member.get("/api/v1/call-log/filter-values")
        assert response.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/filter-values?column_name=status")
        assert response.status_code in (401, 403)


# --- POST /api/v1/call-log/list ---

class TestListCallLogs:
    """Tests for POST /api/v1/call-log/list"""

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_svc, client_as_member, sample_list_request):
        mock_svc.return_value.get_call_logs.return_value = {
            "data": [{"id": 1}],
            "total": 1,
        }
        response = client_as_member.post("/api/v1/call-log/list", json=sample_list_request)
        assert response.status_code == 200
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_with_defaults(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_logs.return_value = {"data": [], "total": 0}
        response = client_as_member.post("/api/v1/call-log/list", json={})
        assert response.status_code == 200
        mock_svc.return_value.get_call_logs.assert_called_once_with(
            page_no=1,
            page_size=10,
            start_date_time=None,
            end_date_time=None,
            filters=None,
            sort_by=None,
            sort_order="desc",
        )

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_with_filters(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_logs.return_value = {"data": [], "total": 0}
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={"filters": {"status": "completed"}, "sort_by": "duration", "sort_order": "asc"},
        )
        assert response.status_code == 200

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_with_date_range(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_logs.return_value = {"data": [], "total": 0}
        response = client_as_member.post(
            "/api/v1/call-log/list",
            json={
                "start_date_time": "2025-01-01T00:00:00",
                "end_date_time": "2025-12-31T23:59:59",
            },
        )
        assert response.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert response.status_code in (401, 403)


# --- GET /api/v1/call-log/{call_id} ---

class TestGetCallLogById:
    """Tests for GET /api/v1/call-log/{call_id}"""

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_svc, client_as_member, sample_call_log):
        mock_svc.return_value.get_call_log_by_id.return_value = sample_call_log
        response = client_as_member.get("/api/v1/call-log/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)
        mock_svc.return_value.get_call_log_by_id.assert_called_once_with(call_log_id=1)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_not_found(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_log_by_id.return_value = None
        response = client_as_member.get("/api/v1/call-log/999")
        assert response.status_code == 404
        assert "Call log not found" in response.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1")
        assert response.status_code in (401, 403)


# --- GET /api/v1/call-log/{call_id}/audio-url ---

class TestGetAudioUrl:
    """Tests for GET /api/v1/call-log/{call_id}/audio-url"""

    @patch("ee.api.v1.call_logs.generate_presigned_url")
    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_svc, mock_presigned, client_as_member, sample_call_log):
        mock_svc.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_presigned.return_value = "https://storage.example.com/signed-url"
        response = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert response.status_code == 200
        assert "url" in response.json()
        mock_presigned.assert_called_once_with("recordings/call_abc123.wav")
        mock_svc.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_not_found(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_log_by_id.return_value = None
        response = client_as_member.get("/api/v1/call-log/999/audio-url")
        assert response.status_code == 404
        assert "Call log not found" in response.json()["detail"]

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_no_audio_file(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_log_by_id.return_value = {
            "id": 1,
            "call_id": "call_abc123",
            "audio_file_path": None,
        }
        response = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert response.status_code == 404
        assert "No audio recording" in response.json()["detail"]

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_empty_audio_path(self, mock_svc, client_as_member):
        mock_svc.return_value.get_call_log_by_id.return_value = {
            "id": 1,
            "call_id": "call_abc123",
            "audio_file_path": "",
        }
        response = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert response.status_code == 404
        assert "No audio recording" in response.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/call-log/1/audio-url")
        assert response.status_code in (401, 403)
