"""Tests for Voices API endpoints (Core edition).

Source: core/api/v1/voices.py
Postman: voices.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_voice():
    return {
        "id": 1,
        "name": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "provider": "elevenlabs",
        "language": "en",
        "gender": "female",
    }


@pytest.fixture
def sample_voices(sample_voice):
    return [
        sample_voice,
        {
            "id": 2,
            "name": "Nova",
            "voice_id": "nova_123",
            "provider": "elevenlabs",
            "language": "en",
            "gender": "female",
        },
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voices
# ---------------------------------------------------------------------------

class TestGetVoices:
    """Tests for GET /api/v1/voice/get_voices"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member, sample_voices):
        mock_service_cls.return_value.get_voices.return_value = sample_voices
        resp = client_as_member.get("/api/v1/voice/get_voices")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Rachel"
        mock_service_cls.return_value.get_voices.assert_called_once()

    @patch("core.api.v1.voices.VoiceService")
    def test_empty_list(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices.return_value = []
        resp = client_as_member.get("/api/v1/voice/get_voices")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/voice/get_voices")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/voice/get_voices")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voice_by_provider
# ---------------------------------------------------------------------------

class TestGetVoiceByProvider:
    """Tests for GET /api/v1/voice/get_voice_by_provider"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_provider_id.return_value = [
            {"id": 1, "name": "Rachel", "voice_id": "21m00Tcm4TlvDq8ikWAM", "language": "en"}
        ]
        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Rachel"
        mock_service_cls.return_value.get_voices_by_provider_id.assert_called_once_with(1)

    @patch("core.api.v1.voices.VoiceService")
    def test_empty_for_provider(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_provider_id.return_value = []
        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 999},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_service_provider_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/voice/get_voice_by_provider")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 1},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_provider_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_provider",
            params={"service_provider_id": 1},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_languages_by_provider
# ---------------------------------------------------------------------------

class TestGetLanguagesByProvider:
    """Tests for GET /api/v1/voice/get_languages_by_provider"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_languages_by_provider_id.return_value = [
            "en", "es", "fr", "de"
        ]
        resp = client_as_member.get(
            "/api/v1/voice/get_languages_by_provider",
            params={"service_provider_id": 1},
        )
        assert resp.status_code == 200
        assert resp.json() == ["en", "es", "fr", "de"]
        mock_service_cls.return_value.get_languages_by_provider_id.assert_called_once_with(1)

    @patch("core.api.v1.voices.VoiceService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_languages_by_provider_id.return_value = []
        resp = client_as_member.get(
            "/api/v1/voice/get_languages_by_provider",
            params={"service_provider_id": 999},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_service_provider_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/voice/get_languages_by_provider")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/voice/get_languages_by_provider",
            params={"service_provider_id": 1},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_languages_by_provider_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/voice/get_languages_by_provider",
            params={"service_provider_id": 1},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voices_by_language
# ---------------------------------------------------------------------------

class TestGetVoicesByLanguage:
    """Tests for GET /api/v1/voice/get_voices_by_language"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_language.return_value = [
            {"id": 1, "name": "Rachel", "voice_id": "21m00Tcm4TlvDq8ikWAM", "language": "en"}
        ]
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language",
            params={"service_provider_id": 1, "language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        mock_service_cls.return_value.get_voices_by_language.assert_called_once_with(1, "en")

    @patch("core.api.v1.voices.VoiceService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_language.return_value = []
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language",
            params={"service_provider_id": 1, "language": "xx"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_service_provider_id(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language",
            params={"language": "en"},
        )
        assert resp.status_code == 422

    def test_missing_language(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language",
            params={"service_provider_id": 1},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/voice/get_voices_by_language",
            params={"service_provider_id": 1, "language": "en"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_language.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language",
            params={"service_provider_id": 1, "language": "en"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voice_by_model_provider
# ---------------------------------------------------------------------------

class TestGetVoiceByModelProvider:
    """Tests for GET /api/v1/voice/get_voice_by_model_provider"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_model_provider_menu_id.return_value = [
            {"id": 1, "name": "Rachel", "voice_id": "21m00Tcm4TlvDq8ikWAM", "language": "en"}
        ]
        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Rachel"
        mock_service_cls.return_value.get_voices_by_model_provider_menu_id.assert_called_once_with(1)

    @patch("core.api.v1.voices.VoiceService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_model_provider_menu_id.return_value = []
        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_model_provider",
            params={"model_provider_menu_id": 999},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_model_provider_menu_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/voice/get_voice_by_model_provider")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/voice/get_voice_by_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_model_provider_menu_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/voice/get_voice_by_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_languages_by_model_provider
# ---------------------------------------------------------------------------

class TestGetLanguagesByModelProvider:
    """Tests for GET /api/v1/voice/get_languages_by_model_provider"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_languages_by_model_provider_menu_id.return_value = [
            "en", "es", "fr"
        ]
        resp = client_as_member.get(
            "/api/v1/voice/get_languages_by_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code == 200
        assert resp.json() == ["en", "es", "fr"]
        mock_service_cls.return_value.get_languages_by_model_provider_menu_id.assert_called_once_with(1)

    @patch("core.api.v1.voices.VoiceService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_languages_by_model_provider_menu_id.return_value = []
        resp = client_as_member.get(
            "/api/v1/voice/get_languages_by_model_provider",
            params={"model_provider_menu_id": 999},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_model_provider_menu_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/voice/get_languages_by_model_provider")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/voice/get_languages_by_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_languages_by_model_provider_menu_id.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/voice/get_languages_by_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/voice/get_voices_by_language_and_model_provider
# ---------------------------------------------------------------------------

class TestGetVoicesByLanguageAndModelProvider:
    """Tests for GET /api/v1/voice/get_voices_by_language_and_model_provider"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_language_and_model_provider.return_value = [
            {"id": 1, "name": "Rachel", "voice_id": "21m00Tcm4TlvDq8ikWAM", "language": "en"}
        ]
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider",
            params={"model_provider_menu_id": 1, "language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Rachel"
        mock_service_cls.return_value.get_voices_by_language_and_model_provider.assert_called_once_with(
            1, "en"
        )

    @patch("core.api.v1.voices.VoiceService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_language_and_model_provider.return_value = []
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider",
            params={"model_provider_menu_id": 1, "language": "xx"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_model_provider_menu_id(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider",
            params={"language": "en"},
        )
        assert resp.status_code == 422

    def test_missing_language(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider",
            params={"model_provider_menu_id": 1},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider",
            params={"model_provider_menu_id": 1, "language": "en"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_voices_by_language_and_model_provider.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider",
            params={"model_provider_menu_id": 1, "language": "en"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/voice/upsert_voice
# ---------------------------------------------------------------------------

class TestUpsertVoice:
    """Tests for POST /api/v1/voice/upsert_voice"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success_create(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_voice.return_value = {
            "id": 1,
            "name": "Custom Voice",
            "voice_id": "custom_voice_123",
            "language": "en",
            "gender": "female",
        }
        payload = {
            "name": "Custom Voice",
            "voice_id": "custom_voice_123",
            "service_provider_id": 1,
            "language": "en",
            "gender": "female",
        }
        resp = client_as_member.post("/api/v1/voice/upsert_voice", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Custom Voice"
        assert data["voice_id"] == "custom_voice_123"
        mock_service_cls.return_value.upsert_voice.assert_called_once_with(payload)

    @patch("core.api.v1.voices.VoiceService")
    def test_success_update(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_voice.return_value = {
            "id": 3, "name": "Nova Updated"
        }
        payload = {"id": 3, "name": "Nova Updated"}
        resp = client_as_member.post("/api/v1/voice/upsert_voice", json=payload)
        assert resp.status_code == 200
        mock_service_cls.return_value.upsert_voice.assert_called_once_with(payload)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/voice/upsert_voice",
            json={"name": "Voice", "voice_id": "v1"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_voice.side_effect = HTTPException(
            status_code=400, detail="Invalid voice data"
        )
        resp = client_as_member.post(
            "/api/v1/voice/upsert_voice",
            json={"name": "Bad Voice"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/voice/delete_voice
# ---------------------------------------------------------------------------

class TestDeleteVoice:
    """Tests for DELETE /api/v1/voice/delete_voice"""

    @patch("core.api.v1.voices.VoiceService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_voice.return_value = {
            "message": "Voice deleted successfully"
        }
        resp = client_as_member.delete(
            "/api/v1/voice/delete_voice", params={"voice_id": 1}
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Voice deleted successfully"
        mock_service_cls.return_value.delete_voice.assert_called_once_with(1)

    @patch("core.api.v1.voices.VoiceService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_voice.side_effect = HTTPException(
            status_code=404, detail="Voice not found"
        )
        resp = client_as_member.delete(
            "/api/v1/voice/delete_voice", params={"voice_id": 999}
        )
        assert resp.status_code == 404

    def test_missing_voice_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/voice/delete_voice")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/voice/delete_voice", params={"voice_id": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.voices.VoiceService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_voice.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.delete(
            "/api/v1/voice/delete_voice", params={"voice_id": 1}
        )
        assert resp.status_code in (500, 422, 400)
