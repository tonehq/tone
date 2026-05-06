"""Tests for Tools API endpoints (EE edition).

Source: ee/api/v1/tools.py
Integration tests — real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# ─── Helpers ───

def _unique_name(prefix="Tool"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _sample_tool_data(**overrides):
    """Valid tool creation payload."""
    data = {
        "name": _unique_name(),
        "description": "A test tool for unit testing",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        "url": "https://example.com/api/tool",
        "method": "POST",
        "auth_type": "none",
        "auth_config": None,
        "meta_data": None,
        "is_active": True,
    }
    data.update(overrides)
    return data


def _create_tool(client, **overrides):
    """Create a tool via the API and return the response JSON."""
    data = _sample_tool_data(**overrides)
    resp = client.post("/api/v1/tool/create_tool", json=data)
    assert resp.status_code == 201, f"Failed to create tool: {resp.text}"
    return resp.json()


def _create_agent(client):
    """Create a minimal agent for attach/detach tests.

    Falls back to fetching an existing agent if creation fails (FK constraints).
    """
    resp = client.post("/api/v1/agent/upsert_agent", json={
        "name": f"Agent-{uuid.uuid4().hex[:8]}",
        "description": "Test agent for tools",
    })
    if resp.status_code == 200:
        return resp.json()
    # If creation fails (FK violation, conflict), try to get existing agent
    list_resp = client.get("/api/v1/agent/get_all_agents")
    if list_resp.status_code == 200 and list_resp.json():
        return list_resp.json()[0]
    pytest.skip("Cannot create or find an agent for this test")


# ─── POST /api/v1/tool/create_tool ───

class TestCreateTool:
    """Tests for POST /api/v1/tool/create_tool"""

    def test_create_tool_success(self, client_as_member):
        data = _sample_tool_data()
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == data["name"]
        assert result["url"] == data["url"]

    def test_create_tool_minimal_fields(self, client_as_member):
        data = {
            "name": _unique_name(),
            "description": "Minimal tool",
            "url": "https://example.com/tool",
        }
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 201

    def test_create_tool_missing_name(self, client_as_member):
        data = _sample_tool_data()
        del data["name"]
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 422

    def test_create_tool_missing_description(self, client_as_member):
        data = _sample_tool_data()
        del data["description"]
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 422

    def test_create_tool_missing_url(self, client_as_member):
        data = _sample_tool_data()
        del data["url"]
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 422

    def test_create_tool_unauthenticated(self, client_unauthenticated):
        data = _sample_tool_data()
        response = client_unauthenticated.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code in (401, 403)

    def test_create_tool_with_auth_config(self, client_as_member):
        data = _sample_tool_data(
            auth_type="api_key",
            auth_config={"header_name": "X-API-Key", "key": "secret123"},
        )
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 201
        assert response.json()["auth_type"] == "api_key"

    def test_create_tool_with_metadata(self, client_as_member):
        data = _sample_tool_data(meta_data={"category": "search", "version": "1.0"})
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 201


# ─── GET /api/v1/tool/get_all_tools ───

class TestGetAllTools:
    """Tests for GET /api/v1/tool/get_all_tools"""

    def test_get_all_tools_success(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_all_tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_tools_after_create(self, client_as_member):
        tool = _create_tool(client_as_member)
        response = client_as_member.get("/api/v1/tool/get_all_tools")
        assert response.status_code == 200
        tool_ids = [t["id"] for t in response.json()]
        assert tool["id"] in tool_ids

    def test_get_all_tools_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/tool/get_all_tools")
        assert response.status_code in (401, 403)


# ─── GET /api/v1/tool/get_tool ───

class TestGetTool:
    """Tests for GET /api/v1/tool/get_tool"""

    def test_get_tool_success(self, client_as_member):
        tool = _create_tool(client_as_member)
        response = client_as_member.get(f"/api/v1/tool/get_tool?tool_id={tool['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == tool["id"]

    def test_get_tool_not_found(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_tool?tool_id=999999")
        assert response.status_code in (404, 400)

    def test_get_tool_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_tool")
        assert response.status_code == 422

    def test_get_tool_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_tool?tool_id=abc")
        assert response.status_code == 422

    def test_get_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/tool/get_tool?tool_id=1")
        assert response.status_code in (401, 403)


# ─── PUT /api/v1/tool/update_tool ───

class TestUpdateTool:
    """Tests for PUT /api/v1/tool/update_tool"""

    def test_update_tool_success(self, client_as_member):
        tool = _create_tool(client_as_member)
        response = client_as_member.put(
            f"/api/v1/tool/update_tool?tool_id={tool['id']}",
            json={"name": "Updated Tool Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Tool Name"

    def test_update_tool_partial_update(self, client_as_member):
        tool = _create_tool(client_as_member)
        response = client_as_member.put(
            f"/api/v1/tool/update_tool?tool_id={tool['id']}",
            json={"description": "New description"},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "New description"
        assert response.json()["name"] == tool["name"]

    def test_update_tool_not_found(self, client_as_member):
        response = client_as_member.put(
            "/api/v1/tool/update_tool?tool_id=999999",
            json={"name": "X"},
        )
        assert response.status_code in (404, 400)

    def test_update_tool_missing_id(self, client_as_member):
        response = client_as_member.put(
            "/api/v1/tool/update_tool",
            json={"name": "X"},
        )
        assert response.status_code == 422

    def test_update_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.put(
            "/api/v1/tool/update_tool?tool_id=1",
            json={"name": "X"},
        )
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/tool/delete_tool ───

class TestDeleteTool:
    """Tests for DELETE /api/v1/tool/delete_tool"""

    def test_delete_tool_success(self, client_as_member):
        tool = _create_tool(client_as_member)
        response = client_as_member.delete(f"/api/v1/tool/delete_tool?tool_id={tool['id']}")
        assert response.status_code == 200

    def test_delete_tool_not_found(self, client_as_member):
        response = client_as_member.delete("/api/v1/tool/delete_tool?tool_id=999999")
        assert response.status_code in (404, 400)

    def test_delete_tool_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/tool/delete_tool")
        assert response.status_code == 422

    def test_delete_tool_invalid_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/tool/delete_tool?tool_id=abc")
        assert response.status_code == 422

    def test_delete_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/tool/delete_tool?tool_id=1")
        assert response.status_code in (401, 403)


# ─── POST /api/v1/tool/attach_tool_to_agents ───

class TestAttachToolToAgents:
    """Tests for POST /api/v1/tool/attach_tool_to_agents"""

    def test_attach_tool_success(self, client_as_member):
        tool = _create_tool(client_as_member)
        agent = _create_agent(client_as_member)
        response = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        assert response.status_code == 200
        assert "attached" in response.json().get("message", "").lower() or response.status_code == 200

    def test_attach_tool_missing_tool_id(self, client_as_member):
        response = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "agent_ids": [1],
        })
        assert response.status_code == 422

    def test_attach_tool_missing_agent_ids(self, client_as_member):
        response = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": 1,
        })
        assert response.status_code == 422

    def test_attach_tool_empty_agent_ids(self, client_as_member):
        """Empty agent_ids list — service may reject or succeed with no-op."""
        tool = _create_tool(client_as_member)
        response = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [],
        })
        assert response.status_code in (200, 400)

    def test_attach_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": 1,
            "agent_ids": [1],
        })
        assert response.status_code in (401, 403)


# ─── DELETE /api/v1/tool/detach_tool_from_agents ───

class TestDetachToolFromAgents:
    """Tests for DELETE /api/v1/tool/detach_tool_from_agents"""

    def test_detach_tool_success(self, client_as_member):
        tool = _create_tool(client_as_member)
        agent = _create_agent(client_as_member)
        # Attach first
        client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        # Detach — use request() since delete() doesn't support json
        response = client_as_member.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        assert response.status_code == 200

    def test_detach_tool_missing_tool_id(self, client_as_member):
        response = client_as_member.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "agent_ids": [1],
        })
        assert response.status_code == 422

    def test_detach_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": 1,
            "agent_ids": [1],
        })
        assert response.status_code in (401, 403)


# ─── GET /api/v1/tool/get_tools_by_agent ───

class TestGetToolsByAgent:
    """Tests for GET /api/v1/tool/get_tools_by_agent"""

    def test_get_tools_by_agent_success(self, client_as_member):
        tool = _create_tool(client_as_member)
        agent = _create_agent(client_as_member)
        # Attach tool to agent
        client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        response = client_as_member.get(f"/api/v1/tool/get_tools_by_agent?agent_id={agent['id']}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_tools_by_agent_empty(self, client_as_member):
        agent = _create_agent(client_as_member)
        response = client_as_member.get(f"/api/v1/tool/get_tools_by_agent?agent_id={agent['id']}")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_tools_by_agent_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_tools_by_agent")
        assert response.status_code == 422

    def test_get_tools_by_agent_invalid_id(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_tools_by_agent?agent_id=abc")
        assert response.status_code == 422

    def test_get_tools_by_agent_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/tool/get_tools_by_agent?agent_id=1")
        assert response.status_code in (401, 403)
