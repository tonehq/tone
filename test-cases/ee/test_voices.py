"""Tests for Voices API endpoints (EE edition).

Source: ee/api/v1/voices.py
Postman: voices.postman_collection.json
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid

from sqlalchemy import text, create_engine
from shared.config import settings

_cached_sp_id = None
_cached_mpm_id = None
_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def _get_real_service_provider_id():
    """Look up a real TTS service_provider_id from the database. Returns None if none exist."""
    global _cached_sp_id
    if _cached_sp_id is not None:
        return _cached_sp_id
    with _engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM service_providers WHERE provider_type = 'tts' LIMIT 1")
        ).fetchone()
        if not row:
            row = conn.execute(
                text("SELECT id FROM service_providers LIMIT 1")
            ).fetchone()
    _cached_sp_id = row[0] if row else None
    return _cached_sp_id


def _get_real_model_provider_menu_id():
    """Look up a real model_provider_menu_id from the database."""
    global _cached_mpm_id
    if _cached_mpm_id is not None:
        return _cached_mpm_id
    with _engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM model_providers_menu LIMIT 1")
        ).fetchone()
    _cached_mpm_id = row[0] if row else 1
    return _cached_mpm_id


# ─── Helpers ───

_requires_sp = pytest.mark.skipif(
    _get_real_service_provider_id() is None,
    reason="No service_providers in DB — cannot create voices",
)


def _create_voice(client, **overrides):
    """Create a voice via upsert endpoint. Returns response JSON."""
    default_sp_id = overrides.pop("service_provider_id", None) or _get_real_service_provider_id()
    payload = {
        "service_provider_id": default_sp_id,
        "name": overrides.pop("name", f"test-voice-{uuid.uuid4().hex[:8]}"),
        "voice_id": overrides.pop("voice_id", f"vid-{uuid.uuid4().hex[:8]}"),
        "language": overrides.pop("language", "en"),
        "gender": overrides.pop("gender", "female"),
        "accent": overrides.pop("accent", "american"),
        "description": overrides.pop("description", "Test voice"),
        **overrides,
    }
    resp = client.post("/api/v1/voice/upsert_voice", json=payload)
    assert resp.status_code == 200
    return resp.json()


# ─── GET /api/v1/voice/get_voices ───

class TestGetVoices:
    """Tests for GET /api/v1/voice/get_voices

    Postman examples:
      - Get Voices - Success (200)
    """

    def test_get_voices_returns_200(self, client_as_member):
        """Postman: Get Voices - Success (200)."""
        response = client_as_member.get("/api/v1/voice/get_voices")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_voices_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/voice/get_voices")
        assert response.status_code in (401, 403)

    @_requires_sp
    def test_get_voices_contains_expected_fields(self, client_as_member):
        """After creating a voice, verify list includes core fields."""
        _create_voice(client_as_member)
        response = client_as_member.get("/api/v1/voice/get_voices")
        assert response.status_code == 200
        voices = response.json()
        assert len(voices) > 0
        voice = voices[-1]
        for field in ("id", "voice_id", "name", "service_provider_id"):
            assert field in voice


# ─── GET /api/v1/voice/get_voice_by_provider ───

class TestGetVoiceByProvider:
    """Tests for GET /api/v1/voice/get_voice_by_provider?service_provider_id=

    Postman examples:
      - Get Voice By Provider - Success (200)
    """

    @_requires_sp
    def test_get_voice_by_provider_returns_200(self, client_as_member):
        """Postman: Get Voice By Provider - Success (200)."""
        sp_id = _get_real_service_provider_id()
        response = client_as_member.get(f"/api/v1/voice/get_voice_by_provider?service_provider_id={sp_id}")
        assert response.status_code == 200

    def test_get_voice_by_provider_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider")
        assert response.status_code == 422

    def test_get_voice_by_provider_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=abc")
        assert response.status_code == 422

    def test_get_voice_by_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/voice/get_voice_by_provider?service_provider_id=1")
        assert response.status_code in (401, 403)

    def test_get_voice_by_provider_no_voices_found(self, client_as_member):
        """Provider with no voices returns appropriate response."""
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=999999")
        assert response.status_code == 200


# ─── GET /api/v1/voice/get_languages_by_provider ───

class TestGetLanguagesByProvider:
    """Tests for GET /api/v1/voice/get_languages_by_provider?service_provider_id=

    Postman examples:
      - Get Languages - Success (200)
    """

    @_requires_sp
    def test_get_languages_by_provider_returns_200(self, client_as_member):
        """Postman: Get Languages - Success (200)."""
        sp_id = _get_real_service_provider_id()
        response = client_as_member.get(f"/api/v1/voice/get_languages_by_provider?service_provider_id={sp_id}")
        assert response.status_code == 200

    def test_get_languages_by_provider_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_languages_by_provider")
        assert response.status_code == 422

    def test_get_languages_by_provider_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_languages_by_provider?service_provider_id=abc")
        assert response.status_code == 422

    def test_get_languages_by_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/voice/get_languages_by_provider?service_provider_id=1")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/voice/get_voices_by_language ───

class TestGetVoicesByLanguage:
    """Tests for GET /api/v1/voice/get_voices_by_language?service_provider_id=&language=

    Postman examples:
      - Get Voices By Language - Success (200)
    """

    @_requires_sp
    def test_get_voices_by_language_returns_200(self, client_as_member):
        """Postman: Get Voices By Language - Success (200)."""
        sp_id = _get_real_service_provider_id()
        response = client_as_member.get(
            f"/api/v1/voice/get_voices_by_language?service_provider_id={sp_id}&language=en"
        )
        assert response.status_code == 200

    def test_get_voices_by_language_missing_provider_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voices_by_language?language=en")
        assert response.status_code == 422

    def test_get_voices_by_language_missing_language(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voices_by_language?service_provider_id=1")
        assert response.status_code == 422

    def test_get_voices_by_language_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/voice/get_voices_by_language?service_provider_id=1&language=en"
        )
        assert response.status_code in (401, 403)


# ─── GET /api/v1/voice/get_voice_by_model_provider ───

class TestGetVoiceByModelProvider:
    """Tests for GET /api/v1/voice/get_voice_by_model_provider?model_provider_menu_id=

    Postman examples:
      - Get Voice By Model Provider - Success (200)
    """

    def test_get_voice_by_model_provider_returns_200(self, client_as_member):
        """Postman: Get Voice By Model Provider - Success (200)."""
        mpm_id = _get_real_model_provider_menu_id()
        response = client_as_member.get(
            f"/api/v1/voice/get_voice_by_model_provider?model_provider_menu_id={mpm_id}"
        )
        assert response.status_code == 200

    def test_get_voice_by_model_provider_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_model_provider")
        assert response.status_code == 422

    def test_get_voice_by_model_provider_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_model_provider?model_provider_menu_id=abc")
        assert response.status_code == 422

    def test_get_voice_by_model_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/voice/get_voice_by_model_provider?model_provider_menu_id=1"
        )
        assert response.status_code in (401, 403)

    def test_get_voice_by_model_provider_nonexistent(self, client_as_member):
        """Non-existent model_provider_menu_id returns empty or error."""
        response = client_as_member.get(
            "/api/v1/voice/get_voice_by_model_provider?model_provider_menu_id=999999"
        )
        assert response.status_code in (200, 404)


# ─── GET /api/v1/voice/get_languages_by_model_provider ───

class TestGetLanguagesByModelProvider:
    """Tests for GET /api/v1/voice/get_languages_by_model_provider?model_provider_menu_id=

    Postman examples:
      - Get Languages By Model Provider - Success (200)
    """

    def test_get_languages_by_model_provider_returns_200(self, client_as_member):
        """Postman: Get Languages By Model Provider - Success (200)."""
        mpm_id = _get_real_model_provider_menu_id()
        response = client_as_member.get(
            f"/api/v1/voice/get_languages_by_model_provider?model_provider_menu_id={mpm_id}"
        )
        assert response.status_code == 200

    def test_get_languages_by_model_provider_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_languages_by_model_provider")
        assert response.status_code == 422

    def test_get_languages_by_model_provider_invalid_id(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/voice/get_languages_by_model_provider?model_provider_menu_id=abc"
        )
        assert response.status_code == 422

    def test_get_languages_by_model_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/voice/get_languages_by_model_provider?model_provider_menu_id=1"
        )
        assert response.status_code in (401, 403)


# ─── GET /api/v1/voice/get_voices_by_language_and_model_provider ───

class TestGetVoicesByLanguageAndModelProvider:
    """Tests for GET /api/v1/voice/get_voices_by_language_and_model_provider?model_provider_menu_id=&language=

    Postman examples:
      - Get Voices By Language And Model Provider - Success (200)
    """

    def test_get_voices_by_language_and_model_provider_returns_200(self, client_as_member):
        """Postman: Get Voices By Language And Model Provider - Success (200)."""
        mpm_id = _get_real_model_provider_menu_id()
        response = client_as_member.get(
            f"/api/v1/voice/get_voices_by_language_and_model_provider?model_provider_menu_id={mpm_id}&language=en"
        )
        assert response.status_code == 200

    def test_get_voices_by_language_and_model_provider_missing_id(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider?language=en"
        )
        assert response.status_code == 422

    def test_get_voices_by_language_and_model_provider_missing_language(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider?model_provider_menu_id=1"
        )
        assert response.status_code == 422

    def test_get_voices_by_language_and_model_provider_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get(
            "/api/v1/voice/get_voices_by_language_and_model_provider?model_provider_menu_id=1&language=en"
        )
        assert response.status_code in (401, 403)


# ─── POST /api/v1/voice/upsert_voice ───

@_requires_sp
class TestUpsertVoice:
    """Tests for POST /api/v1/voice/upsert_voice

    Postman examples:
      - Upsert Voice - Success (200)
    """

    def test_upsert_voice_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/voice/upsert_voice", json={"name": "V"})
        assert response.status_code in (401, 403)

    def test_create_voice_success(self, client_as_member):
        """Postman: Upsert Voice - Success (200)."""
        sp_id = _get_real_service_provider_id()
        data = _create_voice(
            client_as_member,
            service_provider_id=sp_id,
            name="Custom Voice",
            voice_id=f"custom_voice_{uuid.uuid4().hex[:8]}",
            language="en",
            gender="female",
        )
        assert data["name"] == "Custom Voice"
        assert "id" in data

    def test_create_elevenlabs_voice(self, client_as_member):
        """Create ElevenLabs voice."""
        data = _create_voice(
            client_as_member,
            name="Rachel",
            voice_id=f"el-{uuid.uuid4().hex[:8]}",
            language="en",
            gender="female",
            accent="american",
            description="ElevenLabs voice",
        )
        assert data["name"] == "Rachel"
        assert data["gender"] == "female"

    def test_create_voice_with_language_list(self, client_as_member):
        """Create voice with language_list."""
        data = _create_voice(
            client_as_member,
            name="Multilingual Voice",
            voice_id=f"multi-{uuid.uuid4().hex[:8]}",
            language="en",
            language_list=["en", "es", "fr"],
        )
        assert data["name"] == "Multilingual Voice"


# ─── DELETE /api/v1/voice/delete_voice ───

@_requires_sp
class TestDeleteVoice:
    """Tests for DELETE /api/v1/voice/delete_voice?voice_id=

    Postman examples:
      - Delete Voice - Success (200)
    """

    def test_delete_voice_success(self, client_as_member):
        """Postman: Delete Voice - Success (200)."""
        created = _create_voice(client_as_member)
        resp = client_as_member.delete(f"/api/v1/voice/delete_voice?voice_id={created['id']}")
        assert resp.status_code == 200

    def test_delete_voice_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/voice/delete_voice")
        assert response.status_code == 422

    def test_delete_voice_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/voice/delete_voice?voice_id=abc")
        assert response.status_code == 422

    def test_delete_voice_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/voice/delete_voice?voice_id=1")
        assert response.status_code in (401, 403)

    def test_delete_voice_not_found(self, client_as_member):
        response = client_as_member.delete("/api/v1/voice/delete_voice?voice_id=999999")
        assert response.status_code == 404
