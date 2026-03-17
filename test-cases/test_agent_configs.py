"""Tests for Agent Config API endpoints.

Source: core/api/v1/agent_configs.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── Fixtures ───

@pytest.fixture
def sample_agent_config_data():
    return {
        "agent_id": 1,
        "system_prompt": "You are a helpful assistant.",
        "llm_service_id": 1,
        "tts_service_id": 2,
        "stt_service_id": 3,
    }


# ─── POST /api/v1/agent_config/upsert_agent_config — Upsert Agent Config ───

class TestUpsertAgentConfig:
    """Tests for POST /api/v1/agent_config/upsert_agent_config"""

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_create_success(self, mock_service_cls, client_as_member, sample_agent_config_data):
        mock_service_cls.return_value.upsert_agent_config.return_value = {"id": 1, **sample_agent_config_data}
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json=sample_agent_config_data)
        assert response.status_code == 200

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_update_success(self, mock_service_cls, client_as_member):
        data = {"id": 1, "agent_id": 1, "system_prompt": "Updated prompt."}
        mock_service_cls.return_value.upsert_agent_config.return_value = data
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_missing_agent_id(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "system_prompt": "Hello"
        })
        assert response.status_code == 400
        assert "agent_id is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_missing_system_prompt(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 1
        })
        assert response.status_code == 400
        assert "system_prompt is required" in response.json()["detail"]

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_empty_system_prompt(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 1, "system_prompt": ""
        })
        assert response.status_code == 400

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={})
        assert response.status_code == 400

    def test_upsert_config_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 1, "system_prompt": "Hello"
        })
        assert response.status_code in (401, 403)

    @patch("ee.api.v1.agent_configs.AgentConfigService")
    def test_upsert_config_agent_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent_config.side_effect = HTTPException(
            status_code=404, detail="Agent not found"
        )
        response = client_as_member.post("/api/v1/agent_config/upsert_agent_config", json={
            "agent_id": 999, "system_prompt": "Hello"
        })
        assert response.status_code == 404
