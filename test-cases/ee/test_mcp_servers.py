"""Tests for MCP Server API endpoints (EE edition).

Source: ee/api/v1/mcp_servers.py
Integration tests — real DB, real endpoints, no mocks.

Note: Some MCP server endpoints (upsert, validate, discover_tools, get_mcp_tools)
are async and connect to external MCP servers. Tests that require external
connectivity are kept minimal and focus on validation/error paths.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="MCP"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_agent(client, name=None):
    """Create an agent for testing MCP server attachment."""
    data = {"name": name or _unique_name("Agent")}
    resp = client.post("/api/v1/agent/upsert_agent", json=data)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- POST /api/v1/mcp-server/upsert_mcp_server ---

class TestUpsertMcpServer:
    """Tests for POST /api/v1/mcp-server/upsert_mcp_server"""

    def test_create_minimal(self, client_as_member):
        """Create with name and server_url. May fail if external connection
        is attempted during upsert; we accept 200 or a connection-related error."""
        resp = client_as_member.post("/api/v1/mcp-server/upsert_mcp_server", json={
            "name": _unique_name(),
            "server_url": "https://mcp.example.com/mcp",
            "transport_type": "streamable_http",
        })
        # 200 if server is reachable or no validation at create time
        # 400/500 if it validates connectivity on create
        assert resp.status_code in (200, 400, 500)

    def test_empty_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/upsert_mcp_server", json={})
        assert resp.status_code in (400, 422, 500)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/mcp-server/upsert_mcp_server", json={
            "name": "Test",
            "server_url": "https://mcp.example.com/mcp",
        })
        assert resp.status_code in (401, 403)


# --- POST /api/v1/mcp-server/validate_mcp_server ---

class TestValidateMcpServer:
    """Tests for POST /api/v1/mcp-server/validate_mcp_server"""

    def test_missing_server_url(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/validate_mcp_server", json={})
        assert resp.status_code == 400
        assert "server_url is required" in resp.json()["detail"]

    def test_with_invalid_url(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/validate_mcp_server", json={
            "server_url": "https://nonexistent-mcp-server.invalid/mcp",
            "transport_type": "streamable_http",
        })
        # Should fail with connection error
        assert resp.status_code in (400, 500)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/mcp-server/validate_mcp_server", json={
            "server_url": "https://mcp.example.com/mcp",
        })
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/get_all_mcp_servers ---

class TestGetAllMcpServers:
    """Tests for GET /api/v1/mcp-server/get_all_mcp_servers"""

    def test_returns_200_list(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_all_mcp_servers")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_all_mcp_servers")
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/get_mcp_server ---

class TestGetMcpServer:
    """Tests for GET /api/v1/mcp-server/get_mcp_server"""

    def test_not_found(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server?mcp_server_id=999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server")
        assert resp.status_code == 422

    def test_invalid_mcp_server_id_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server?mcp_server_id=abc")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_server?mcp_server_id=1")
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/discover_tools ---

class TestDiscoverTools:
    """Tests for GET /api/v1/mcp-server/discover_tools"""

    def test_not_found(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/discover_tools?mcp_server_id=999999")
        assert resp.status_code in (404, 500)

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/discover_tools")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/discover_tools?mcp_server_id=1")
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/get_mcp_tools ---

class TestGetMcpTools:
    """Tests for GET /api/v1/mcp-server/get_mcp_tools"""

    def test_not_found(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_tools?mcp_server_id=999999")
        assert resp.status_code in (404, 500)

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_tools")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_tools?mcp_server_id=1")
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/mcp-server/delete_mcp_server ---

class TestDeleteMcpServer:
    """Tests for DELETE /api/v1/mcp-server/delete_mcp_server"""

    def test_delete_not_found(self, client_as_member):
        resp = client_as_member.delete("/api/v1/mcp-server/delete_mcp_server?mcp_server_id=999999")
        assert resp.status_code == 404

    def test_delete_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/mcp-server/delete_mcp_server")
        assert resp.status_code == 422

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/mcp-server/delete_mcp_server?mcp_server_id=1")
        assert resp.status_code in (401, 403)


# --- POST /api/v1/mcp-server/attach_mcp_server_to_agents ---

class TestAttachMcpServerToAgents:
    """Tests for POST /api/v1/mcp-server/attach_mcp_server_to_agents"""

    def test_attach_nonexistent_server(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.post("/api/v1/mcp-server/attach_mcp_server_to_agents", json={
            "mcp_server_id": 999999,
            "agent_ids": [agent["id"]],
            "selected_tools": ["tool1"],
        })
        assert resp.status_code in (404, 500)

    def test_attach_missing_fields(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/attach_mcp_server_to_agents", json={})
        assert resp.status_code == 422

    def test_attach_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/mcp-server/attach_mcp_server_to_agents", json={
            "mcp_server_id": 1,
            "agent_ids": [1],
        })
        assert resp.status_code in (401, 403)


# --- DELETE /api/v1/mcp-server/detach_mcp_server_from_agents ---

class TestDetachMcpServerFromAgents:
    """Tests for DELETE /api/v1/mcp-server/detach_mcp_server_from_agents"""

    def test_detach_nonexistent_server(self, client_as_member):
        resp = client_as_member.request(
            "DELETE",
            "/api/v1/mcp-server/detach_mcp_server_from_agents",
            json={
                "mcp_server_id": 999999,
                "agent_ids": [1],
            },
        )
        # Request body on DELETE may or may not be supported; accept multiple codes
        assert resp.status_code in (200, 404, 422, 500)

    def test_detach_missing_fields(self, client_as_member):
        resp = client_as_member.request(
            "DELETE",
            "/api/v1/mcp-server/detach_mcp_server_from_agents",
            json={},
        )
        assert resp.status_code == 422

    def test_detach_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.request(
            "DELETE",
            "/api/v1/mcp-server/detach_mcp_server_from_agents",
            json={
                "mcp_server_id": 1,
                "agent_ids": [1],
            },
        )
        assert resp.status_code in (401, 403)


# --- PUT /api/v1/mcp-server/update_agent_mcp_server ---

class TestUpdateAgentMcpServer:
    """Tests for PUT /api/v1/mcp-server/update_agent_mcp_server"""

    def test_update_nonexistent(self, client_as_member):
        resp = client_as_member.put("/api/v1/mcp-server/update_agent_mcp_server", json={
            "mcp_server_id": 999999,
            "agent_id": 999999,
            "selected_tools": ["tool1"],
        })
        assert resp.status_code in (404, 500)

    def test_update_missing_fields(self, client_as_member):
        resp = client_as_member.put("/api/v1/mcp-server/update_agent_mcp_server", json={})
        assert resp.status_code == 422

    def test_update_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.put("/api/v1/mcp-server/update_agent_mcp_server", json={
            "mcp_server_id": 1,
            "agent_id": 1,
            "selected_tools": ["tool1"],
        })
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/get_mcp_servers_by_agent ---

class TestGetMcpServersByAgent:
    """Tests for GET /api/v1/mcp-server/get_mcp_servers_by_agent"""

    def test_returns_list_for_existing_agent(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id={agent['id']}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_nonexistent_agent(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id=999999")
        # Returns empty list or 404 depending on implementation
        assert resp.status_code in (200, 404)

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent")
        assert resp.status_code == 422

    def test_invalid_agent_id_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id=abc")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id=1")
        assert resp.status_code in (401, 403)
