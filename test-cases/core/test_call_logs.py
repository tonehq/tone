"""Tests for Call Logs API endpoints (Core edition).

Source: core/api/v1/call_logs.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_call_log():
    return {
        "id": 1,
        "call_id": "call-abc-123",
        "agent_id": 10,
        "duration": 120,
        "status": "completed",
        "audio_file_path": "s3://bucket/recordings/call-abc-123.wav",
    }


@pytest.fixture
def sample_call_logs(sample_call_log):
    return {
        "data": [
            sample_call_log,
            {"id": 2, "call_id": "call-def-456", "agent_id": 10, "duration": 60, "status": "completed"},
        ],
        "total": 2,
        "page_no": 1,
        "page_size": 10,
    }


@pytest.fixture
def filter_values():
    return ["completed", "failed", "in_progress"]


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/filter-values
# ---------------------------------------------------------------------------

class TestGetFilterValues:
    """Tests for GET /api/v1/call-log/filter-values"""

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_service_cls, client_as_member, filter_values):
        mock_service_cls.return_value.get_filter_values.return_value = filter_values
        resp = client_as_member.get(
            "/api/v1/call-log/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code == 200
        assert resp.json() == filter_values
        mock_service_cls.return_value.get_filter_values.assert_called_once_with(
            column_name="status",
        )

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/call-log/filter-values")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/call-log/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_filter_values.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get(
            "/api/v1/call-log/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/call-log/list
# ---------------------------------------------------------------------------

class TestGetCallLogs:
    """Tests for POST /api/v1/call-log/list"""

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success_defaults(self, mock_service_cls, client_as_member, sample_call_logs):
        mock_service_cls.return_value.get_call_logs.return_value = sample_call_logs
        resp = client_as_member.post("/api/v1/call-log/list", json={})
        assert resp.status_code == 200
        assert resp.json()["total"] == 2
        mock_service_cls.return_value.get_call_logs.assert_called_once_with(
            page_no=1,
            page_size=10,
            start_date_time=None,
            end_date_time=None,
            filters=None,
            sort_by=None,
            sort_order="desc",
        )

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success_with_params(self, mock_service_cls, client_as_member, sample_call_logs):
        mock_service_cls.return_value.get_call_logs.return_value = sample_call_logs
        payload = {
            "page_no": 2,
            "page_size": 5,
            "sort_by": "duration",
            "sort_order": "asc",
            "filters": {"status": "completed"},
        }
        resp = client_as_member.post("/api/v1/call-log/list", json=payload)
        assert resp.status_code == 200
        mock_service_cls.return_value.get_call_logs.assert_called_once_with(
            page_no=2,
            page_size=5,
            start_date_time=None,
            end_date_time=None,
            filters={"status": "completed"},
            sort_by="duration",
            sort_order="asc",
        )

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_empty_results(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_logs.return_value = {
            "data": [],
            "total": 0,
            "page_no": 1,
            "page_size": 10,
        }
        resp = client_as_member.post("/api/v1/call-log/list", json={})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_logs.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.post("/api/v1/call-log/list", json={})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/{call_id}
# ---------------------------------------------------------------------------

class TestGetCallLogById:
    """Tests for GET /api/v1/call-log/{call_id}"""

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_service_cls, client_as_member, sample_call_log):
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        resp = client_as_member.get("/api/v1/call-log/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_service_cls.return_value.get_call_log_by_id.assert_called_once_with(call_log_id=1)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.return_value = None
        resp = client_as_member.get("/api/v1/call-log/999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/call-log/1")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get("/api/v1/call-log/1")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/{call_id}/audio-url
# ---------------------------------------------------------------------------

class TestGetAudioUrl:
    """Tests for GET /api/v1/call-log/{call_id}/audio-url"""

    @patch("ee.api.v1.call_logs.generate_presigned_url")
    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_service_cls, mock_presigned, client_as_member, sample_call_log):
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_presigned.return_value = "https://s3.example.com/presigned-url"
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://s3.example.com/presigned-url"
        mock_presigned.assert_called_once_with(sample_call_log["audio_file_path"])

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_call_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.return_value = None
        resp = client_as_member.get("/api/v1/call-log/999/audio-url")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_no_audio_recording(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.return_value = {
            "id": 1,
            "call_id": "call-abc-123",
            "audio_file_path": None,
        }
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code == 404
        assert "no audio" in resp.json()["detail"].lower()

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_no_audio_key_in_result(self, mock_service_cls, client_as_member):
        """Result dict has no audio_file_path key at all."""
        mock_service_cls.return_value.get_call_log_by_id.return_value = {
            "id": 1,
            "call_id": "call-abc-123",
        }
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/{call_id}/audio
# NOTE: This endpoint only exists in Core edition (not in EE call_logs router).
# When EE is enabled, these tests are skipped.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    True,  # EE is always enabled in this environment
    reason="/audio endpoint only exists in Core edition"
)
class TestDownloadAudio:
    """Tests for GET /api/v1/call-log/{call_id}/audio"""

    @patch("ee.api.v1.call_logs.get_r2_object")
    @patch("ee.api.v1.call_logs.CallLogService")
    def test_success(self, mock_service_cls, mock_r2, client_as_member, sample_call_log):
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_body = MagicMock()
        mock_body.iter_chunks.return_value = [b"audio data"]
        mock_r2.return_value = {
            "Body": mock_body,
            "ContentLength": 1024,
            "ContentType": "audio/wav",
            "StatusCode": 200,
        }

        resp = client_as_member.get("/api/v1/call-log/1/audio")
        assert resp.status_code == 200
        assert resp.headers.get("accept-ranges") == "bytes"

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_call_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.return_value = None
        resp = client_as_member.get("/api/v1/call-log/999/audio")
        assert resp.status_code == 404

    @patch("ee.api.v1.call_logs.CallLogService")
    def test_no_audio_path(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.return_value = {
            "id": 1, "audio_file_path": None,
        }
        resp = client_as_member.get("/api/v1/call-log/1/audio")
        assert resp.status_code == 404
        assert "no audio" in resp.json()["detail"].lower()

    @patch("ee.api.v1.call_logs.get_r2_object")
    @patch("ee.api.v1.call_logs.CallLogService")
    def test_r2_error(self, mock_service_cls, mock_r2, client_as_member, sample_call_log):
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_r2.side_effect = Exception("R2 not reachable")

        resp = client_as_member.get("/api/v1/call-log/1/audio")
        assert resp.status_code == 404
        assert "not found in storage" in resp.json()["detail"].lower()

    @patch("ee.api.v1.call_logs.get_r2_object")
    @patch("ee.api.v1.call_logs.CallLogService")
    def test_range_request(self, mock_service_cls, mock_r2, client_as_member, sample_call_log):
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_body = MagicMock()
        mock_body.iter_chunks.return_value = [b"partial"]
        mock_r2.return_value = {
            "Body": mock_body,
            "ContentLength": 512,
            "ContentType": "audio/wav",
            "ContentRange": "bytes 0-511/1024",
            "StatusCode": 206,
        }

        resp = client_as_member.get("/api/v1/call-log/1/audio", headers={"Range": "bytes=0-511"})
        assert resp.status_code == 206
        assert resp.headers.get("content-range") == "bytes 0-511/1024"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/call-log/1/audio")
        assert resp.status_code in (401, 403)
