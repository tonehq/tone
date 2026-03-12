"""Tests for Voices API endpoints.

Source: core/api/v1/voices.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── Fixtures ───

@pytest.fixture
def sample_voice_data():
    return {
        "name": "Test Voice",
        "service_provider_id": 1,
        "voice_id": "voice-123",
        "language": "en",
    }


# ─── GET /api/v1/voice/get_voices — Get All Voices ───

class TestGetVoices:
    """Tests for GET /api/v1/voice/get_voices"""

    @patch("core.api.v1.voices.VoiceService")
    def test_get_voices_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices.return_value = [{"id": 1, "name": "Voice1"}]
        response = client_as_member.get("/api/v1/voice/get_voices")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.voices.VoiceService")
    def test_get_voices_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices.return_value = []
        response = client_as_member.get("/api/v1/voice/get_voices")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_voices_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/voice/get_voices")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/voice/get_voice_by_provider — Get Voices By Provider ───

class TestGetVoiceByProvider:
    """Tests for GET /api/v1/voice/get_voice_by_provider"""

    @patch("core.api.v1.voices.VoiceService")
    def test_get_voice_by_provider_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_provider_id.return_value = [
            {"id": 1, "name": "Voice1"}
        ]
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=1")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("core.api.v1.voices.VoiceService")
    def test_get_voice_by_provider_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_provider_id.return_value = []
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=1")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_voice_by_provider_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider")
        assert response.status_code == 422

    def test_get_voice_by_provider_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=abc")
        assert response.status_code == 422

    def test_get_voice_by_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/voice/get_voice_by_provider?service_provider_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/voice/upsert_voice — Upsert Voice ───

class TestUpsertVoice:
    """Tests for POST /api/v1/voice/upsert_voice"""

    @patch("core.api.v1.voices.VoiceService")
    def test_upsert_voice_create_success(self, mock_service_cls, client_as_member, sample_voice_data):
        mock_service_cls.return_value.upsert_voice.return_value = {"id": 1, **sample_voice_data}
        response = client_as_member.post("/api/v1/voice/upsert_voice", json=sample_voice_data)
        assert response.status_code == 200

    @patch("core.api.v1.voices.VoiceService")
    def test_upsert_voice_update_success(self, mock_service_cls, client_as_member):
        data = {"id": 1, "name": "Updated Voice"}
        mock_service_cls.return_value.upsert_voice.return_value = data
        response = client_as_member.post("/api/v1/voice/upsert_voice", json=data)
        assert response.status_code == 200

    @patch("core.api.v1.voices.VoiceService")
    def test_upsert_voice_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_voice.side_effect = HTTPException(
            status_code=400, detail="Invalid voice data"
        )
        response = client_as_member.post("/api/v1/voice/upsert_voice", json={})
        assert response.status_code == 400

    def test_upsert_voice_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/voice/upsert_voice", json={"name": "V"})
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/voice/delete_voice — Delete Voice ───

class TestDeleteVoice:
    """Tests for DELETE /api/v1/voice/delete_voice"""

    @patch("core.api.v1.voices.VoiceService")
    def test_delete_voice_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_voice.return_value = {"message": "deleted"}
        response = client_as_member.delete("/api/v1/voice/delete_voice?voice_id=1")
        assert response.status_code == 200

    def test_delete_voice_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/voice/delete_voice")
        assert response.status_code == 422

    def test_delete_voice_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/voice/delete_voice?voice_id=abc")
        assert response.status_code == 422

    @patch("core.api.v1.voices.VoiceService")
    def test_delete_voice_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_voice.side_effect = HTTPException(
            status_code=404, detail="Voice not found"
        )
        response = client_as_member.delete("/api/v1/voice/delete_voice?voice_id=999")
        assert response.status_code == 404

    def test_delete_voice_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/voice/delete_voice?voice_id=1")
        assert response.status_code in (401, 403)
