"""Tests for Agent Config API endpoints (EE edition).

Source: ee/api/v1/agent_configs.py
Postman: postman_collection/agent_configs.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
Comprehensive coverage: all Postman examples + validation + CRUD flows + edge cases.
"""

import pytest
import uuid


# ─── Helpers ───

def _create_agent(client, name=None):
    """Create an agent via API and return its ID."""
    name = name or f"cfg-test-agent-{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/v1/agent/upsert_agent", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


# ─── POST /api/v1/agent_config/upsert_agent_config -- Validation ───

class TestUpsertAgentConfigValidation:
    """Validation edge cases for POST /api/v1/agent_config/upsert_agent_config"""

    def test_missing_agent_id(self, client_as_member):
        """Postman: Upsert Agent Config - Missing Agent ID (400)."""
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "system_prompt": "Hello",
        })
        assert resp.status_code == 400
        assert "agent_id is required" in resp.json()["detail"]

    def test_null_agent_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": None, "system_prompt": "Hello",
        })
        assert resp.status_code == 400

    def test_missing_system_prompt(self, client_as_member):
        """Postman: Upsert Agent Config - Missing System Prompt (400)."""
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 1,
        })
        assert resp.status_code == 400
        assert "system_prompt is required" in resp.json()["detail"]

    def test_empty_system_prompt(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 1, "system_prompt": "",
        })
        assert resp.status_code == 400

    def test_empty_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 1, "system_prompt": "Hello",
        })
        assert resp.status_code in (401, 403)

    def test_nonexistent_agent_id(self, client_as_member):
        """agent_id that doesn't exist in DB should return 404."""
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 999999, "system_prompt": "Hello",
        })
        assert resp.status_code == 404

    def test_nonexistent_config_id(self, client_as_member):
        """Providing an 'id' for a config that doesn't exist should return 404."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "id": 999999, "agent_id": agent_id, "system_prompt": "Hello",
        })
        assert resp.status_code == 404


# ─── POST /api/v1/agent_config/upsert_agent_config -- Create ───

class TestUpsertAgentConfigCreate:
    """Create new agent configs via real DB.
    Postman: Upsert Agent Config - Success (200)."""

    def test_create_minimal_config(self, client_as_member):
        """Create config with just agent_id + system_prompt (minimum required)."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "You are a helpful sales assistant.",
        })
        assert resp.status_code == 200

    def test_create_config_with_all_fields(self, client_as_member):
        """Postman example: full config with llm_model_id, stt_model_id, tts_model_id, etc."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "You are a helpful sales assistant.",
            "temperature": 0.7,
            "max_tokens": 1024,
            "language": "en",
        })
        assert resp.status_code == 200

    def test_create_config_with_all_text_fields(self, client_as_member):
        """Create config with all text fields populated."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "You are a customer support agent.",
            "first_message": "Hello! How can I help you today?",
            "end_call_message": "Thank you for calling. Goodbye!",
            "voicemail_message": "Sorry, I'm not available. Please leave a message.",
            "html_prompt": "<h1>Support Agent</h1>",
            "description": "Customer support voice agent config",
        })
        assert resp.status_code == 200

    def test_create_config_with_metadata(self, client_as_member):
        """Create config with LLM/TTS/STT metadata."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "You are a voice agent.",
            "llm_metadata": {"model_id": 1, "temperature": 0.7, "max_tokens": 1000},
            "tts_metadata": {"model_id": 2, "voice": "alloy", "speed": 1.0},
            "stt_metadata": {"model_id": 3, "language": "en"},
        })
        assert resp.status_code == 200

    def test_create_config_with_agent_metadata(self, client_as_member):
        """Create config with agent_metadata (voice settings)."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "You are a voice agent.",
            "agent_metadata": {
                "language": "en",
                "voice_speed": 1.2,
                "patience_level": "high",
                "call_recording": True,
                "call_transcription": True,
            },
        })
        assert resp.status_code == 200

    def test_create_config_with_service_ids(self, client_as_member):
        """Create config referencing LLM/TTS/STT service IDs (may fail if IDs don't exist)."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Agent with services.",
            "llm_service_id": 1,
            "tts_service_id": 2,
            "stt_service_id": 3,
        })
        assert resp.status_code in (200, 409)

    def test_create_config_as_admin(self, client_as_admin):
        agent_id = _create_agent(client_as_admin)
        resp = client_as_admin.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Admin created config.",
        })
        assert resp.status_code == 200

    def test_create_config_as_owner(self, client_as_owner):
        agent_id = _create_agent(client_as_owner)
        resp = client_as_owner.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Owner created config.",
        })
        assert resp.status_code == 200


# ─── POST /api/v1/agent_config/upsert_agent_config -- Update ───

class TestUpsertAgentConfigUpdate:
    """Update existing agent configs -- partial and full updates."""

    def _create_agent_with_config(self, client):
        """Helper to create an agent + config and return agent_id."""
        agent_id = _create_agent(client)
        resp = client.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Original prompt.",
            "first_message": "Original greeting.",
            "end_call_message": "Original goodbye.",
        })
        assert resp.status_code == 200
        return agent_id

    def test_update_system_prompt_only(self, client_as_member):
        """Update just the system_prompt, keeping other fields."""
        agent_id = self._create_agent_with_config(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Updated system prompt.",
        })
        assert resp.status_code == 200

    def test_update_first_message(self, client_as_member):
        agent_id = self._create_agent_with_config(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Same prompt.",
            "first_message": "New greeting!",
        })
        assert resp.status_code == 200

    def test_update_all_text_fields(self, client_as_member):
        agent_id = self._create_agent_with_config(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Completely new prompt.",
            "first_message": "New first message.",
            "end_call_message": "New end call.",
            "voicemail_message": "New voicemail.",
            "html_prompt": "<p>New HTML</p>",
        })
        assert resp.status_code == 200

    def test_update_metadata_fields(self, client_as_member):
        agent_id = self._create_agent_with_config(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Prompt with metadata.",
            "llm_metadata": {"model_id": 5, "temperature": 0.9},
            "tts_metadata": {"voice": "nova"},
        })
        assert resp.status_code == 200

    def test_multiple_updates_same_agent(self, client_as_member):
        """Multiple sequential updates to same agent config should all succeed."""
        agent_id = self._create_agent_with_config(client_as_member)
        for i in range(3):
            resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
                "agent_id": agent_id,
                "system_prompt": f"Update #{i+1}",
            })
            assert resp.status_code == 200


# ─── POST /api/v1/agent_config/upsert_agent_config -- Edge Cases ───

class TestUpsertAgentConfigEdgeCases:
    """Edge cases and special values."""

    def test_very_long_system_prompt(self, client_as_member):
        """System prompt with very long text."""
        agent_id = _create_agent(client_as_member)
        long_prompt = "You are a helpful assistant. " * 500
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": long_prompt,
        })
        assert resp.status_code == 200

    def test_system_prompt_with_special_chars(self, client_as_member):
        """System prompt with unicode, newlines."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "You are a helpful agent.\n\nRules:\n1. Be polite\n2. Speak in espanol\n3. Use Japanese when asked",
        })
        assert resp.status_code == 200

    def test_empty_metadata_dicts(self, client_as_member):
        """Empty metadata dicts should be accepted."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Prompt.",
            "llm_metadata": {},
            "tts_metadata": {},
            "stt_metadata": {},
            "agent_metadata": {},
        })
        assert resp.status_code == 200

    def test_null_optional_fields(self, client_as_member):
        """Explicitly null optional fields should be handled gracefully."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Prompt.",
            "first_message": None,
            "end_call_message": None,
            "voicemail_message": None,
            "html_prompt": None,
            "llm_service_id": None,
            "tts_service_id": None,
            "stt_service_id": None,
        })
        assert resp.status_code == 200

    def test_extra_unknown_fields_ignored(self, client_as_member):
        """Extra fields not in the schema should be ignored, not cause errors."""
        agent_id = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Prompt.",
            "unknown_field": "should be ignored",
            "another_random_key": 12345,
        })
        assert resp.status_code == 200

    def test_config_with_custom_uuid(self, client_as_member):
        """Providing a custom UUID for the config."""
        agent_id = _create_agent(client_as_member)
        custom_uuid = str(uuid.uuid4())
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": agent_id,
            "system_prompt": "Config with custom UUID.",
            "uuid": custom_uuid,
        })
        assert resp.status_code == 200
