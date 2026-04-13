"""Tests for Agent Configs API endpoints (Core edition).

Source: core/api/v1/agent_configs.py
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
        "agent_id": 10,
        "system_prompt": "You are a helpful assistant.",
        "llm_model": "gpt-4",
    }


@pytest.fixture
def valid_payload():
    return {
        "agent_id": 10,
        "system_prompt": "You are a helpful assistant.",
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
        assert resp.json()["agent_id"] == 10
        mock_service_cls.return_value.upsert_agent_config.assert_called_once_with(valid_payload)

    @patch("core.api.v1.agent_configs.AgentConfigService")
    def test_success_with_extra_fields(self, mock_service_cls, client_as_member, sample_agent_config):
        payload = {"agent_id": 10, "system_prompt": "Hello", "llm_model": "gpt-4"}
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
            json={"agent_id": 10},
        )
        assert resp.status_code == 400
        assert "system_prompt" in resp.json()["detail"].lower()

    def test_empty_system_prompt(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": 10, "system_prompt": ""},
        )
        assert resp.status_code == 400
        assert "system_prompt" in resp.json()["detail"].lower()

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": 10, "system_prompt": "Hello"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agent_configs.AgentConfigService")
    def test_service_error(self, mock_service_cls, client_as_member, valid_payload):
        mock_service_cls.return_value.upsert_agent_config.side_effect = Exception("DB error")
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json=valid_payload,
        )
        assert resp.status_code == 500
