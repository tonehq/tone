"""Tests for Agent Configs API endpoints (Core edition).

Source: core/api/v1/agent_configs.py
Postman: agent_configs.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_agent_config():
    return {
        "id": 1,
        "agent_id": 1,
        "system_prompt": "You are a helpful sales assistant.",
        "llm_model_id": 1,
        "stt_model_id": 2,
        "tts_model_id": 3,
        "tts_voice_id": 1,
        "temperature": 0.7,
        "max_tokens": 1024,
        "language": "en",
        "created_at": "2026-01-15T10:00:00",
        "updated_at": "2026-01-15T10:00:00",
    }


@pytest.fixture
def valid_payload():
    return {
        "agent_id": 1,
        "system_prompt": "You are a helpful sales assistant.",
        "llm_model_id": 1,
        "stt_model_id": 2,
        "tts_model_id": 3,
        "tts_voice_id": 1,
        "temperature": 0.7,
        "max_tokens": 1024,
        "language": "en",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/agent_config/upsert_agent_config
# ---------------------------------------------------------------------------

class TestUpsertAgentConfig:
    """Tests for POST /api/v1/agent_config/upsert_agent_config"""

    @patch("core.api.v1.agent_configs.AgentConfigService")
    def test_success(self, mock_service_cls, client_as_member, valid_payload, sample_agent_config):
        mock_service_cls.return_value.upsert_agent_config.return_value = sample_agent_config
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json=valid_payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == 1
        assert data["system_prompt"] == "You are a helpful sales assistant."
        assert data["llm_model_id"] == 1
        assert data["temperature"] == 0.7
        mock_service_cls.return_value.upsert_agent_config.assert_called_once_with(valid_payload)

    @patch("core.api.v1.agent_configs.AgentConfigService")
    def test_success_with_extra_fields(self, mock_service_cls, client_as_member, sample_agent_config):
        payload = {
            "agent_id": 1,
            "system_prompt": "Hello",
            "llm_model_id": 1,
            "extra_field": "value",
        }
        mock_service_cls.return_value.upsert_agent_config.return_value = sample_agent_config
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json=payload,
        )
        assert resp.status_code == 200

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"system_prompt": "You are helpful."},
        )
        assert resp.status_code == 400
        assert "agent_id" in resp.json()["detail"].lower()

    def test_missing_system_prompt(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": 1},
        )
        assert resp.status_code == 400
        assert "system_prompt" in resp.json()["detail"].lower()

    def test_empty_system_prompt(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": 1, "system_prompt": ""},
        )
        assert resp.status_code == 400
        assert "system_prompt" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": 1, "system_prompt": "Hello"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agent_configs.AgentConfigService")
    def test_service_error(self, mock_service_cls, client_as_member, valid_payload):
        mock_service_cls.return_value.upsert_agent_config.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json=valid_payload,
        )
        assert resp.status_code in (500, 422, 400)
