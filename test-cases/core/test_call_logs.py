"""Tests for Call Logs API endpoints (Core edition).

Source: core/api/v1/call_logs.py
Postman: call_logs.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


PATCH_SERVICE = "core.api.v1.call_logs.CallLogService"
PATCH_PRESIGNED = "core.api.v1.call_logs.generate_presigned_url"
PATCH_R2 = "core.api.v1.call_logs.get_r2_object"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_call_log():
    return {
        "id": 1,
        "call_id": "call-123",
        "agent_id": 1,
        "agent_name": "Sales Agent",
        "from_number": "+1234567890",
        "to_number": "+0987654321",
        "status": "completed",
        "duration": 120,
        "transcript": [],
        "audio_file_path": "recordings/call-123.wav",
        "created_at": "2026-01-15T10:00:00",
    }


@pytest.fixture
def sample_call_logs_response(sample_call_log):
    return {
        "data": [sample_call_log],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total": 1,
        },
    }


@pytest.fixture
def filter_values():
    return ["Sales Agent", "Support Agent", "Booking Agent"]


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/filter-values
# ---------------------------------------------------------------------------

class TestGetFilterValues:
    """Tests for GET /api/v1/call-log/filter-values"""

    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, client_as_member, filter_values):
        """Postman: Get Filter Values - Success (200)"""
        mock_service_cls.return_value.get_filter_values.return_value = filter_values
        resp = client_as_member.get(
            "/api/v1/call-log/filter-values", params={"column_name": "agent_name"}
        )
        assert resp.status_code == 200
        assert resp.json() == filter_values
        mock_service_cls.return_value.get_filter_values.assert_called_once_with(
            column_name="agent_name",
        )

    def test_missing_column_name(self, client_as_member):
        """column_name is required query param -- 422 when missing."""
        resp = client_as_member.get("/api/v1/call-log/filter-values")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/call-log/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code in (401, 403)

    @patch(PATCH_SERVICE)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_filter_values.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/call-log/filter-values", params={"column_name": "status"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/call-log/list
# ---------------------------------------------------------------------------

class TestGetCallLogs:
    """Tests for POST /api/v1/call-log/list"""

    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, client_as_member, sample_call_logs_response):
        """Postman: Get Call Logs - Success (200)"""
        mock_service_cls.return_value.get_call_logs.return_value = sample_call_logs_response
        resp = client_as_member.post("/api/v1/call-log/list", json={
            "page_no": 1,
            "page_size": 10,
            "start_date_time": "2026-01-01T00:00:00",
            "end_date_time": "2026-12-31T23:59:59",
            "filters": {},
            "sort_by": "created_at",
            "sort_order": "desc",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total"] == 1

    @patch(PATCH_SERVICE)
    def test_success_defaults(self, mock_service_cls, client_as_member, sample_call_logs_response):
        """Empty body uses defaults."""
        mock_service_cls.return_value.get_call_logs.return_value = sample_call_logs_response
        resp = client_as_member.post("/api/v1/call-log/list", json={})
        assert resp.status_code == 200
        mock_service_cls.return_value.get_call_logs.assert_called_once_with(
            page_no=1,
            page_size=10,
            start_date_time=None,
            end_date_time=None,
            filters=None,
            sort_by=None,
            sort_order="desc",
        )

    @patch(PATCH_SERVICE)
    def test_success_with_params(self, mock_service_cls, client_as_member, sample_call_logs_response):
        mock_service_cls.return_value.get_call_logs.return_value = sample_call_logs_response
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

    @patch(PATCH_SERVICE)
    def test_empty_results(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_logs.return_value = {
            "data": [],
            "pagination": {"page": 1, "page_size": 10, "total": 0},
        }
        resp = client_as_member.post("/api/v1/call-log/list", json={})
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/call-log/list", json={})
        assert resp.status_code in (401, 403)

    @patch(PATCH_SERVICE)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_logs.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.post("/api/v1/call-log/list", json={})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/call-log/facets
# ---------------------------------------------------------------------------

PATCH_CALL_SERVICE = "core.api.v1.call_logs.CallService"


@pytest.fixture
def sample_facets():
    return {
        "status": [
            {"value": "completed", "count": 12},
            {"value": "in_progress", "count": 3},
            {"value": "failed", "count": 1},
        ],
        "agent_name": [{"value": "Sales Agent", "count": 9}],
        "direction": [{"value": "inbound", "count": 10}],
        "channel_type": [{"value": "twilio", "count": 16}],
        "llm_model": [{"value": "gpt-4o", "count": 16}],
        "stt_model": [{"value": "nova-2", "count": 16}],
        "tts_model": [{"value": "eleven_turbo_v2", "count": 16}],
    }


class TestGetFacets:
    """Tests for POST /api/v1/call-log/facets"""

    @patch(PATCH_CALL_SERVICE)
    def test_success_empty_body(self, mock_service_cls, client_as_member, sample_facets):
        mock_service_cls.return_value.get_facets.return_value = sample_facets
        resp = client_as_member.post("/api/v1/call-log/facets", json={})
        assert resp.status_code == 200
        assert resp.json()["status"][0]["value"] == "completed"
        mock_service_cls.return_value.get_facets.assert_called_once_with(
            start_date_time=None,
            end_date_time=None,
            filters=None,
        )

    @patch(PATCH_CALL_SERVICE)
    def test_passes_filters_and_dates(self, mock_service_cls, client_as_member, sample_facets):
        mock_service_cls.return_value.get_facets.return_value = sample_facets
        payload = {
            "start_date_time": "2026-01-01T00:00:00",
            "end_date_time": "2026-12-31T23:59:59",
            "filters": [{"field": "status", "operator": "in", "value": ["completed"]}],
        }
        resp = client_as_member.post("/api/v1/call-log/facets", json=payload)
        assert resp.status_code == 200
        mock_service_cls.return_value.get_facets.assert_called_once_with(
            start_date_time="2026-01-01T00:00:00",
            end_date_time="2026-12-31T23:59:59",
            filters=[{"field": "status", "operator": "in", "value": ["completed"]}],
        )

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/call-log/facets", json={})
        assert resp.status_code in (401, 403)

    @patch(PATCH_CALL_SERVICE)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_facets.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.post("/api/v1/call-log/facets", json={})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/{call_id}
# ---------------------------------------------------------------------------

class TestGetCallLogById:
    """Tests for GET /api/v1/call-log/{call_id}"""

    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, client_as_member, sample_call_log):
        """Postman: Get Call Log - Success (200)"""
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        resp = client_as_member.get("/api/v1/call-log/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["call_id"] == "call-123"
        assert data["status"] == "completed"
        mock_service_cls.return_value.get_call_log_by_id.assert_called_once_with(call_log_id=1)

    @patch(PATCH_SERVICE)
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Call Log - Not Found (404)"""
        mock_service_cls.return_value.get_call_log_by_id.return_value = None
        resp = client_as_member.get("/api/v1/call-log/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Call log not found"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/call-log/1")
        assert resp.status_code in (401, 403)

    @patch(PATCH_SERVICE)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/call-log/1")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/{call_id}/audio-url
# ---------------------------------------------------------------------------

class TestGetAudioUrl:
    """Tests for GET /api/v1/call-log/{call_id}/audio-url"""

    @patch(PATCH_PRESIGNED)
    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, mock_presigned, client_as_member, sample_call_log):
        """Postman: Get Audio URL - Success (200)"""
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_presigned.return_value = "https://r2.example.com/recordings/call-123.wav?token=..."
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code == 200
        assert "url" in resp.json()
        assert resp.json()["url"] == "https://r2.example.com/recordings/call-123.wav?token=..."
        mock_presigned.assert_called_once_with(sample_call_log["audio_file_path"])

    @patch(PATCH_SERVICE)
    def test_call_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Audio URL - Not Found (404)"""
        mock_service_cls.return_value.get_call_log_by_id.return_value = None
        resp = client_as_member.get("/api/v1/call-log/999/audio-url")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Call log not found"

    @patch(PATCH_SERVICE)
    def test_no_audio_recording(self, mock_service_cls, client_as_member):
        """Postman: Get Audio URL - No Recording (404)"""
        mock_service_cls.return_value.get_call_log_by_id.return_value = {
            "id": 1,
            "call_id": "call-123",
            "audio_file_path": None,
        }
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No audio recording for this call"

    @patch(PATCH_SERVICE)
    def test_no_audio_key_in_result(self, mock_service_cls, client_as_member):
        """Result dict has no audio_file_path key at all."""
        mock_service_cls.return_value.get_call_log_by_id.return_value = {
            "id": 1,
            "call_id": "call-123",
        }
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code in (401, 403)

    @patch(PATCH_SERVICE)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/call-log/1/audio-url")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/call-log/{call_id}/audio
# ---------------------------------------------------------------------------

class TestDownloadAudio:
    """Tests for GET /api/v1/call-log/{call_id}/audio

    Streams audio from R2 storage. Supports HTTP Range requests.
    """

    @patch(PATCH_R2)
    @patch(PATCH_SERVICE)
    def test_success(self, mock_service_cls, mock_r2, client_as_member, sample_call_log):
        """Postman: Download Audio - Success (200) with audio/wav content type."""
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

    @patch(PATCH_SERVICE)
    def test_call_not_found(self, mock_service_cls, client_as_member):
        """Postman: Download Audio - Not Found (404)"""
        mock_service_cls.return_value.get_call_log_by_id.return_value = None
        resp = client_as_member.get("/api/v1/call-log/999/audio")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Call log not found"

    @patch(PATCH_SERVICE)
    def test_no_audio_path(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_call_log_by_id.return_value = {
            "id": 1, "audio_file_path": None,
        }
        resp = client_as_member.get("/api/v1/call-log/1/audio")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No audio recording for this call"

    @patch(PATCH_R2)
    @patch(PATCH_SERVICE)
    def test_r2_error(self, mock_service_cls, mock_r2, client_as_member, sample_call_log):
        """R2 storage error returns 404 with storage message."""
        mock_service_cls.return_value.get_call_log_by_id.return_value = sample_call_log
        mock_r2.side_effect = Exception("R2 not reachable")

        resp = client_as_member.get("/api/v1/call-log/1/audio")
        assert resp.status_code == 404
        assert "not found in storage" in resp.json()["detail"].lower()

    @patch(PATCH_R2)
    @patch(PATCH_SERVICE)
    def test_range_request(self, mock_service_cls, mock_r2, client_as_member, sample_call_log):
        """HTTP Range request returns 206 with Content-Range header."""
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

        resp = client_as_member.get(
            "/api/v1/call-log/1/audio", headers={"Range": "bytes=0-511"}
        )
        assert resp.status_code == 206
        assert resp.headers.get("content-range") == "bytes 0-511/1024"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/call-log/1/audio")
        assert resp.status_code in (401, 403)
