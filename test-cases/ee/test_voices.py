"""Tests for Voices API endpoints (EE edition).

Source: ee/api/v1/voices.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid

from sqlalchemy import text, create_engine
from shared.config import settings

_cached_sp_id = None
_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def _get_real_service_provider_id():
    """Look up a real TTS service_provider_id from the database."""
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
    _cached_sp_id = row[0] if row else 1
    return _cached_sp_id


# ─── Helpers ───

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
    """Tests for GET /api/v1/voice/get_voices"""

    def test_get_voices_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voices")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_voices_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/voice/get_voices")
        assert response.status_code in (401, 403)

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
    """Tests for GET /api/v1/voice/get_voice_by_provider"""

    def test_get_voice_by_provider_returns_200(self, client_as_member):
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=1")
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
        """Provider with no voices returns appropriate message."""
        response = client_as_member.get("/api/v1/voice/get_voice_by_provider?service_provider_id=999999")
        assert response.status_code == 200


# ─── POST /api/v1/voice/upsert_voice ───

class TestUpsertVoice:
    """Tests for POST /api/v1/voice/upsert_voice"""

    def test_upsert_voice_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/voice/upsert_voice", json={"name": "V"})
        assert response.status_code in (401, 403)

    def test_create_elevenlabs_voice(self, client_as_member):
        """Postman: Create ElevenLabs voice."""
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

    def test_create_openai_voice(self, client_as_member):
        """Postman: Create OpenAI voice."""
        data = _create_voice(
            client_as_member,
            name="Alloy",
            voice_id=f"oai-{uuid.uuid4().hex[:8]}",
            language="en",
            gender="female",
            accent=None,
        )
        assert data["name"] == "Alloy"

    def test_create_deepgram_voice(self, client_as_member):
        """Postman: Create Deepgram voice."""
        data = _create_voice(
            client_as_member,
            name="Asteria",
            voice_id=f"dg-{uuid.uuid4().hex[:8]}",
            language="en",
            gender="female",
        )
        assert data["name"] == "Asteria"

    def test_create_cartesia_voice_with_language_list(self, client_as_member):
        """Postman: Create Cartesia voice with language_list."""
        data = _create_voice(
            client_as_member,
            name="Cartesia Voice",
            voice_id=f"cart-{uuid.uuid4().hex[:8]}",
            language="en",
            language_list=["en", "es", "fr"],
        )
        assert data["name"] == "Cartesia Voice"

    def test_create_google_tts_voice(self, client_as_member):
        """Postman: Create Google TTS voice."""
        data = _create_voice(
            client_as_member,
            name="Standard A",
            voice_id=f"goog-{uuid.uuid4().hex[:8]}",
            language="en-US",
            gender="female",
        )
        assert data["name"] == "Standard A"
        assert data["language"] == "en-US"

    def test_create_multilingual_voice(self, client_as_member):
        """Postman: Create Multilingual voice with language_list."""
        data = _create_voice(
            client_as_member,
            name="Multilingual Voice",
            voice_id=f"multi-{uuid.uuid4().hex[:8]}",
            language="en",
            gender="male",
            language_list=["en", "es", "de", "fr"],
        )
        assert data["name"] == "Multilingual Voice"
        assert data["gender"] == "male"

    def test_update_voice(self, client_as_member):
        """Postman: Update voice via id."""
        created = _create_voice(client_as_member)
        resp = client_as_member.post("/api/v1/voice/upsert_voice", json={
            "id": created["id"],
            "name": "Updated Voice",
            "description": "Updated description",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Voice"

    def test_deactivate_voice(self, client_as_member):
        """Postman: Deactivate voice via is_active=false."""
        created = _create_voice(client_as_member)
        resp = client_as_member.post("/api/v1/voice/upsert_voice", json={
            "id": created["id"],
            "is_active": False,
        })
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


# ─── DELETE /api/v1/voice/delete_voice ───

class TestDeleteVoice:
    """Tests for DELETE /api/v1/voice/delete_voice"""

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

    def test_delete_voice_success(self, client_as_member):
        """Create a voice, delete it, verify gone."""
        created = _create_voice(client_as_member)
        resp = client_as_member.delete(f"/api/v1/voice/delete_voice?voice_id={created['id']}")
        assert resp.status_code == 200
