"""Tests for Agents API endpoints (Core edition).

Source: core/api/v1/agents.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_agent():
    return {
        "id": 1,
        "name": "Test Agent",
        "created_by": 1,
        "agent_config": {"system_prompt": "You are helpful."},
    }


@pytest.fixture
def sample_agents(sample_agent):
    return [
        sample_agent,
        {"id": 2, "name": "Second Agent", "created_by": 1, "agent_config": {}},
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/agent/get_all_agents
# ---------------------------------------------------------------------------

class TestGetAllAgents:
    """Tests for GET /api/v1/agent/get_all_agents"""

    @patch("core.api.v1.agents.AgentService")
    def test_success(self, mock_service_cls, client_as_member, sample_agents):
        mock_service_cls.return_value.get_all_agents.return_value = sample_agents
        resp = client_as_member.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        mock_service_cls.return_value.get_all_agents.assert_called_once_with(
            agent_id=None, created_by=ANY,
        )

    @patch("core.api.v1.agents.AgentService")
    def test_with_agent_id_filter(self, mock_service_cls, client_as_member, sample_agent):
        mock_service_cls.return_value.get_all_agents.return_value = [sample_agent]
        resp = client_as_member.get("/api/v1/agent/get_all_agents", params={"agent_id": 1})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_service_cls.return_value.get_all_agents.assert_called_once_with(
            agent_id=1, created_by=ANY,
        )

    @patch("core.api.v1.agents.AgentService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.return_value = []
        resp = client_as_member.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/agent/get_all_agents")
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.side_effect = Exception("DB error")
        resp = client_as_member.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/agent/get_agent
# ---------------------------------------------------------------------------

class TestGetAgent:
    """Tests for GET /api/v1/agent/get_agent"""

    @patch("core.api.v1.agents.AgentService")
    def test_success(self, mock_service_cls, client_as_member, sample_agent):
        mock_service_cls.return_value.get_all_agents.return_value = [sample_agent]
        resp = client_as_member.get("/api/v1/agent/get_agent", params={"agent_id": 1})
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    @patch("core.api.v1.agents.AgentService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.return_value = []
        resp = client_as_member.get("/api/v1/agent/get_agent", params={"agent_id": 999})
        assert resp.status_code == 404

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/get_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/agent/get_agent", params={"agent_id": 1})
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.side_effect = Exception("DB error")
        resp = client_as_member.get("/api/v1/agent/get_agent", params={"agent_id": 1})
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /api/v1/agent/delete_agent
# ---------------------------------------------------------------------------

class TestDeleteAgent:
    """Tests for DELETE /api/v1/agent/delete_agent"""

    @patch("core.api.v1.agents.AgentService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.return_value = {"message": "deleted"}
        resp = client_as_member.delete("/api/v1/agent/delete_agent", params={"agent_id": 1})
        assert resp.status_code == 200
        mock_service_cls.return_value.delete_agent.assert_called_once_with(1)

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/agent/delete_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/agent/delete_agent", params={"agent_id": 1})
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.side_effect = Exception("DB error")
        resp = client_as_member.delete("/api/v1/agent/delete_agent", params={"agent_id": 1})
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/agent/upsert_agent
# ---------------------------------------------------------------------------

class TestUpsertAgent:
    """Tests for POST /api/v1/agent/upsert_agent"""

    @patch("core.api.v1.agents.AgentService")
    def test_success_create(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent.return_value = {"id": 1, "name": "New Agent"}
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent",
            json={"name": "New Agent"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.upsert_agent.assert_called_once_with(
            {"name": "New Agent"}, created_by=ANY,
        )

    @patch("core.api.v1.agents.AgentService")
    def test_success_update(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent.return_value = {"id": 1, "name": "Updated"}
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent",
            json={"id": 1, "name": "Updated"},
        )
        assert resp.status_code == 200

    def test_missing_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent/upsert_agent", json={"description": "no name"})
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_empty_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent/upsert_agent", json={"name": ""})
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent/upsert_agent", json={"name": "Agent"}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent.side_effect = Exception("DB error")
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent", json={"name": "Agent"}
        )
        assert resp.status_code == 500
