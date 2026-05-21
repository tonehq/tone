"""Tests for MCP Servers API endpoints (Core edition).

Source: core/api/v1/mcp_servers.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_mcp_server():
    return {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "My MCP Server",
        "server_url": "https://mcp.example.com/mcp",
        "transport_type": "streamable_http",
        "status": "active",
        "tools_count": 5,
        "created_at": "2026-01-15T10:00:00",
    }


@pytest.fixture
def sample_mcp_servers(sample_mcp_server):
    return [
        sample_mcp_server,
        {
            "id": 2,
            "name": "Second MCP Server",
            "server_url": "https://mcp2.example.com/mcp",
            "transport_type": "streamable_http",
            "status": "active",
            "tools_count": 3,
        },
    ]


@pytest.fixture
def sample_tools():
    return {
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather for a city",
                "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}},
            }
        ]
    }


# ---------------------------------------------------------------------------
# POST /api/v1/mcp-server/upsert_mcp_server
# ---------------------------------------------------------------------------

class TestUpsertMcpServer:
    """Tests for POST /api/v1/mcp-server/upsert_mcp_server"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_create_success(self, mock_service_cls, client_as_member, sample_mcp_server):
        mock_svc = mock_service_cls.return_value
        mock_svc.upsert_mcp_server = AsyncMock(return_value=MagicMock())
        mock_svc.mcp_server_response.return_value = sample_mcp_server
        resp = client_as_member.post(
            "/api/v1/mcp-server/upsert_mcp_server",
            json={
                "name": "My MCP Server",
                "server_url": "https://mcp.example.com/mcp",
                "transport_type": "streamable_http",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My MCP Server"
        assert data["id"] == 1

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_update_success(self, mock_service_cls, client_as_member, sample_mcp_server):
        mock_svc = mock_service_cls.return_value
        updated = {**sample_mcp_server, "name": "Updated Server"}
        mock_svc.upsert_mcp_server = AsyncMock(return_value=MagicMock())
        mock_svc.mcp_server_response.return_value = updated
        resp = client_as_member.post(
            "/api/v1/mcp-server/upsert_mcp_server",
            json={"id": 1, "name": "Updated Server"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Server"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/mcp-server/upsert_mcp_server",
            json={"name": "Server", "server_url": "https://example.com/mcp"},
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.upsert_mcp_server = AsyncMock(
            side_effect=HTTPException(status_code=500, detail="DB error")
        )
        resp = client_as_member.post(
            "/api/v1/mcp-server/upsert_mcp_server",
            json={"name": "Server", "server_url": "https://example.com/mcp"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/mcp-server/validate_mcp_server
# ---------------------------------------------------------------------------

class TestValidateMcpServer:
    """Tests for POST /api/v1/mcp-server/validate_mcp_server"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.validate_mcp_connection = AsyncMock(return_value={
            "valid": True,
            "tools": [{"name": "get_weather", "description": "Get weather for a city", "input_schema": {}}],
        })
        resp = client_as_member.post(
            "/api/v1/mcp-server/validate_mcp_server",
            json={"server_url": "https://mcp.example.com/mcp", "transport_type": "streamable_http"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert len(data["tools"]) >= 1

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_missing_server_url(self, mock_service_cls, client_as_member):
        resp = client_as_member.post(
            "/api/v1/mcp-server/validate_mcp_server",
            json={"transport_type": "streamable_http"},
        )
        assert resp.status_code == 400
        assert "server_url is required" in resp.json()["detail"]

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/mcp-server/validate_mcp_server",
            json={"server_url": "https://mcp.example.com/mcp"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/mcp-server/get_all_mcp_servers
# ---------------------------------------------------------------------------

class TestGetAllMcpServers:
    """Tests for GET /api/v1/mcp-server/get_all_mcp_servers"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member, sample_mcp_servers):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_servers.return_value = sample_mcp_servers
        mock_svc.mcp_server_response.side_effect = lambda s: s
        resp = client_as_member.get("/api/v1/mcp-server/get_all_mcp_servers")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_servers.return_value = []
        resp = client_as_member.get("/api/v1/mcp-server/get_all_mcp_servers")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_all_mcp_servers")
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_servers.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.get("/api/v1/mcp-server/get_all_mcp_servers")
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/mcp-server/get_mcp_server
# ---------------------------------------------------------------------------

class TestGetMcpServer:
    """Tests for GET /api/v1/mcp-server/get_mcp_server"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member, sample_mcp_server):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_server.return_value = MagicMock()
        mock_svc.mcp_server_response.return_value = sample_mcp_server
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server", params={"mcp_server_id": 1})
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_server.side_effect = HTTPException(status_code=404, detail="MCP server not found")
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server", params={"mcp_server_id": 999})
        assert resp.status_code == 404

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_server", params={"mcp_server_id": 1})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/mcp-server/discover_tools
# ---------------------------------------------------------------------------

class TestDiscoverTools:
    """Tests for GET /api/v1/mcp-server/discover_tools"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member, sample_tools):
        mock_svc = mock_service_cls.return_value
        mock_svc.discover_tools = AsyncMock(return_value=sample_tools)
        resp = client_as_member.get("/api/v1/mcp-server/discover_tools", params={"mcp_server_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert len(data["tools"]) >= 1
        assert data["tools"][0]["name"] == "get_weather"

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/discover_tools")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/discover_tools", params={"mcp_server_id": 1})
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.discover_tools = AsyncMock(
            side_effect=HTTPException(status_code=500, detail="Connection failed")
        )
        resp = client_as_member.get("/api/v1/mcp-server/discover_tools", params={"mcp_server_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/mcp-server/get_mcp_tools
# ---------------------------------------------------------------------------

class TestGetMcpTools:
    """Tests for GET /api/v1/mcp-server/get_mcp_tools"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member, sample_tools):
        mock_svc = mock_service_cls.return_value
        mock_svc.discover_tools = AsyncMock(return_value=sample_tools)
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_tools", params={"mcp_server_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "get_weather"
        assert data[0]["description"] == "Get weather for a city"
        # Should only have name and description (no input_schema)
        assert "input_schema" not in data[0]

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_tools")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_tools", params={"mcp_server_id": 1})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/mcp-server/delete_mcp_server
# ---------------------------------------------------------------------------

class TestDeleteMcpServer:
    """Tests for DELETE /api/v1/mcp-server/delete_mcp_server"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.delete_mcp_server.return_value = {"message": "MCP server deleted successfully"}
        resp = client_as_member.delete("/api/v1/mcp-server/delete_mcp_server", params={"mcp_server_id": 1})
        assert resp.status_code == 200
        assert "message" in resp.json()
        mock_svc.delete_mcp_server.assert_called_once_with(1)

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/mcp-server/delete_mcp_server")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/mcp-server/delete_mcp_server", params={"mcp_server_id": 1})
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.delete_mcp_server.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.delete("/api/v1/mcp-server/delete_mcp_server", params={"mcp_server_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/mcp-server/attach_mcp_server_to_agents
# ---------------------------------------------------------------------------

class TestAttachMcpServerToAgents:
    """Tests for POST /api/v1/mcp-server/attach_mcp_server_to_agents"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.attach_to_agents.return_value = None
        resp = client_as_member.post(
            "/api/v1/mcp-server/attach_mcp_server_to_agents",
            json={"mcp_server_id": 1, "agent_ids": [1, 2], "selected_tools": ["get_weather", "send_email"]},
        )
        assert resp.status_code == 200
        assert "2 agent(s)" in resp.json()["message"]
        mock_svc.attach_to_agents.assert_called_once_with(1, [1, 2], ["get_weather", "send_email"])

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_without_selected_tools(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.attach_to_agents.return_value = None
        resp = client_as_member.post(
            "/api/v1/mcp-server/attach_mcp_server_to_agents",
            json={"mcp_server_id": 1, "agent_ids": [1]},
        )
        assert resp.status_code == 200
        assert "1 agent(s)" in resp.json()["message"]

    def test_missing_fields(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/mcp-server/attach_mcp_server_to_agents",
            json={"mcp_server_id": 1},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/mcp-server/attach_mcp_server_to_agents",
            json={"mcp_server_id": 1, "agent_ids": [1]},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/mcp-server/detach_mcp_server_from_agents
# ---------------------------------------------------------------------------

class TestDetachMcpServerFromAgents:
    """Tests for DELETE /api/v1/mcp-server/detach_mcp_server_from_agents"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.detach_from_agents.return_value = {"message": "MCP server detached from 1 agent(s) successfully"}
        resp = client_as_member.delete(
            "/api/v1/mcp-server/detach_mcp_server_from_agents",
            json={"mcp_server_id": 1, "agent_ids": [1]},
        )
        assert resp.status_code == 200

    def test_missing_fields(self, client_as_member):
        resp = client_as_member.delete(
            "/api/v1/mcp-server/detach_mcp_server_from_agents",
            json={"mcp_server_id": 1},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/mcp-server/detach_mcp_server_from_agents",
            json={"mcp_server_id": 1, "agent_ids": [1]},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /api/v1/mcp-server/update_agent_mcp_server
# ---------------------------------------------------------------------------

class TestUpdateAgentMcpServer:
    """Tests for PUT /api/v1/mcp-server/update_agent_mcp_server"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.update_agent_mcp_server.return_value = {"message": "Agent MCP server updated successfully"}
        resp = client_as_member.put(
            "/api/v1/mcp-server/update_agent_mcp_server",
            json={"mcp_server_id": 1, "agent_id": 1, "selected_tools": ["get_weather"]},
        )
        assert resp.status_code == 200
        mock_svc.update_agent_mcp_server.assert_called_once_with(1, 1, ["get_weather"])

    def test_missing_fields(self, client_as_member):
        resp = client_as_member.put(
            "/api/v1/mcp-server/update_agent_mcp_server",
            json={"mcp_server_id": 1},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.put(
            "/api/v1/mcp-server/update_agent_mcp_server",
            json={"mcp_server_id": 1, "agent_id": 1, "selected_tools": ["get_weather"]},
        )
        assert resp.status_code in (401, 403)

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.update_agent_mcp_server.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = client_as_member.put(
            "/api/v1/mcp-server/update_agent_mcp_server",
            json={"mcp_server_id": 1, "agent_id": 1, "selected_tools": ["get_weather"]},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/mcp-server/get_mcp_servers_by_agent
# ---------------------------------------------------------------------------

class TestGetMcpServersByAgent:
    """Tests for GET /api/v1/mcp-server/get_mcp_servers_by_agent"""

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_servers_by_agent.return_value = [
            {"id": 1, "name": "My MCP Server", "server_url": "https://mcp.example.com/mcp", "selected_tools": ["get_weather"]},
        ]
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent", params={"agent_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "My MCP Server"

    @patch("ee.api.v1.mcp_servers.McpServerService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_svc = mock_service_cls.return_value
        mock_svc.get_mcp_servers_by_agent.return_value = []
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent", params={"agent_id": 999})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_servers_by_agent", params={"agent_id": 1})
        assert resp.status_code in (401, 403)
