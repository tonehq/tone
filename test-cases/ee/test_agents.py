"""Tests for Agent API endpoints.

Source: core/api/v1/agents.py
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# ─── Fixtures ───

@pytest.fixture
def sample_agent_data():
    return {
        "name": "Test Agent",
        "description": "A test voice agent",
    }


@pytest.fixture
def mock_agent_response():
    return {
        "id": 1,
        "name": "Test Agent",
        "description": "A test voice agent",
        "agent_config": {},
        "service_providers": {},
    }


# ─── GET /api/v1/agent/get_all_agents — Get All Agents ───

class TestGetAllAgents:
    """Tests for GET /api/v1/agent/get_all_agents"""

    @patch("ee.api.v1.agents.AgentService")
    def test_get_all_agents_success(self, mock_service_cls, client_as_member, mock_agent_response):
        mock_service_cls.return_value.get_all_agents.return_value = [mock_agent_response]
        response = client_as_member.get("/api/v1/agent/get_all_agents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agents.AgentService")
    def test_get_all_agents_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.return_value = []
        response = client_as_member.get("/api/v1/agent/get_all_agents")
        assert response.status_code == 200
        assert response.json() == []

    @patch("ee.api.v1.agents.AgentService")
    def test_get_all_agents_with_agent_id_filter(self, mock_service_cls, client_as_member, mock_agent_response):
        mock_service_cls.return_value.get_all_agents.return_value = [mock_agent_response]
        response = client_as_member.get("/api/v1/agent/get_all_agents?agent_id=1")
        assert response.status_code == 200

    def test_get_all_agents_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent/get_all_agents")
        assert response.status_code in (401, 403)

    def test_get_all_agents_invalid_agent_id_type(self, client_as_member):
        response = client_as_member.get("/api/v1/agent/get_all_agents?agent_id=abc")
        assert response.status_code == 422


# ─── GET /api/v1/agent/get_agent — Get Agent ───

class TestGetAgent:
    """Tests for GET /api/v1/agent/get_agent"""

    @patch("ee.api.v1.agents.AgentService")
    def test_get_agent_success(self, mock_service_cls, client_as_member, mock_agent_response):
        mock_service_cls.return_value.get_all_agents.return_value = [mock_agent_response]
        response = client_as_member.get("/api/v1/agent/get_agent?agent_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agents.AgentService")
    def test_get_agent_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.return_value = []
        response = client_as_member.get("/api/v1/agent/get_agent?agent_id=999")
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    def test_get_agent_missing_agent_id(self, client_as_member):
        response = client_as_member.get("/api/v1/agent/get_agent")
        assert response.status_code == 422

    def test_get_agent_invalid_agent_id_type(self, client_as_member):
        response = client_as_member.get("/api/v1/agent/get_agent?agent_id=abc")
        assert response.status_code == 422

    def test_get_agent_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent/get_agent?agent_id=1")
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/agent/delete_agent — Delete Agent ───

class TestDeleteAgent:
    """Tests for DELETE /api/v1/agent/delete_agent"""

    @patch("ee.api.v1.agents.AgentService")
    def test_delete_agent_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.return_value = {"message": "deleted"}
        response = client_as_member.delete("/api/v1/agent/delete_agent?agent_id=1")
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    def test_delete_agent_missing_agent_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/agent/delete_agent")
        assert response.status_code == 422

    def test_delete_agent_invalid_agent_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/agent/delete_agent?agent_id=abc")
        assert response.status_code == 422

    @patch("ee.api.v1.agents.AgentService")
    def test_delete_agent_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.side_effect = HTTPException(
            status_code=404, detail="Agent not found"
        )
        response = client_as_member.delete("/api/v1/agent/delete_agent?agent_id=999")
        assert response.status_code == 404

    def test_delete_agent_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/agent/delete_agent?agent_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/agent/upsert_agent — Upsert Agent ───

class TestUpsertAgent:
    """Tests for POST /api/v1/agent/upsert_agent"""

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_create_success(self, mock_service_cls, client_as_member, sample_agent_data):
        mock_service_cls.return_value.upsert_agent.return_value = {"id": 1, **sample_agent_data}
        response = client_as_member.post("/api/v1/agent/upsert_agent", json=sample_agent_data)
        assert response.status_code == 200
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_update_success(self, mock_service_cls, client_as_member):
        data = {"id": 1, "name": "Updated Agent"}
        mock_service_cls.return_value.upsert_agent.return_value = data
        response = client_as_member.post("/api/v1/agent/upsert_agent", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_missing_name(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent/upsert_agent", json={"description": "no name"})
        assert response.status_code == 400
        assert "name is required" in response.json()["detail"]

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_empty_name(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent/upsert_agent", json={"name": ""})
        assert response.status_code == 400

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/agent/upsert_agent", json={})
        assert response.status_code == 400

    def test_upsert_agent_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/agent/upsert_agent", json={"name": "Test"})
        assert response.status_code in (401, 403)

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_with_agent_type(self, mock_service_cls, client_as_member, sample_agent_data):
        data = {**sample_agent_data, "agent_type": "inbound"}
        mock_service_cls.return_value.upsert_agent.return_value = {"id": 1, **data}
        response = client_as_member.post("/api/v1/agent/upsert_agent", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_with_channel_data(self, mock_service_cls, client_as_member, sample_agent_data):
        data = {**sample_agent_data, "channel_type": "twilio", "channel_name": "Main"}
        mock_service_cls.return_value.upsert_agent.return_value = {"id": 1, **data}
        response = client_as_member.post("/api/v1/agent/upsert_agent", json=data)
        assert response.status_code == 200

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_conflict(self, mock_service_cls, client_as_member, sample_agent_data):
        mock_service_cls.return_value.upsert_agent.side_effect = HTTPException(
            status_code=409, detail="Agent name already exists"
        )
        response = client_as_member.post("/api/v1/agent/upsert_agent", json=sample_agent_data)
        assert response.status_code == 409

    @patch("ee.api.v1.agents.AgentService")
    def test_upsert_agent_service_error(self, mock_service_cls, client_as_member, sample_agent_data):
        mock_service_cls.return_value.upsert_agent.side_effect = HTTPException(
            status_code=500, detail="Internal error"
        )
        response = client_as_member.post("/api/v1/agent/upsert_agent", json=sample_agent_data)
        assert response.status_code == 500
