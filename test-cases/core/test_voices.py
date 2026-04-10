"""Tests for Voices API endpoints (Core edition).

Source: core/api/v1/voices.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voices
# ---------------------------------------------------------------------------
class TestGetVoices:
    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_voices.return_value = [
            {"id": 1, "name": "Alloy"},
            {"id": 2, "name": "Nova"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/voice/get_voices")

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.get_voices.assert_called_once()

    @patch("core.api.v1.voices.VoiceService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_voices.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/voice/get_voices")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_voices.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/voice/get_voices")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voice_by_provider
# ---------------------------------------------------------------------------
class TestGetVoiceByProvider:
    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_voices_by_provider_id.return_value = [
            {"id": 1, "name": "Alloy", "service_provider_id": 5},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 5},
        )

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_instance.get_voices_by_provider_id.assert_called_once_with(5)

    @patch("core.api.v1.voices.VoiceService")
    def test_empty_for_provider(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_voices_by_provider_id.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 999},
        )

        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_service_provider_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/voice/get_voice_by_provider")
        assert resp.status_code == 422

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_voices_by_provider_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 5},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/voice/upsert_voice
# ---------------------------------------------------------------------------
class TestUpsertVoice:
    @patch("core.api.v1.voices.VoiceService")
    def test_success_create(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_voice.return_value = {
            "id": 1,
            "name": "Alloy",
            "service_provider_id": 5,
        }
        mock_service_cls.return_value = mock_instance

        payload = {"name": "Alloy", "service_provider_id": 5, "voice_id": "alloy"}
        resp = client_as_member.post("/api/v1/voice/upsert_voice", json=payload)

        assert resp.status_code == 200
        assert resp.json()["name"] == "Alloy"
        mock_service_cls.assert_called_once_with(ANY)
        mock_instance.upsert_voice.assert_called_once_with(payload)

    @patch("core.api.v1.voices.VoiceService")
    def test_success_update(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_voice.return_value = {"id": 3, "name": "Nova Updated"}
        mock_service_cls.return_value = mock_instance

        payload = {"id": 3, "name": "Nova Updated"}
        resp = client_as_member.post("/api/v1/voice/upsert_voice", json=payload)

        assert resp.status_code == 200
        mock_instance.upsert_voice.assert_called_once_with(payload)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_voice.side_effect = HTTPException(
            status_code=400, detail="Invalid voice data"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post(
            "/api/v1/voice/upsert_voice",
            json={"name": "Bad Voice"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/voice/delete_voice
# ---------------------------------------------------------------------------
class TestDeleteVoice:
    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_voice.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/voice/delete_voice", params={"voice_id": 2}
        )

        assert resp.status_code == 200
        mock_instance.delete_voice.assert_called_once_with(2)

    @patch("core.api.v1.voices.VoiceService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_voice.side_effect = HTTPException(
            status_code=404, detail="Voice not found"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete(
            "/api/v1/voice/delete_voice", params={"voice_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_voice_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/voice/delete_voice")
        assert resp.status_code == 422
