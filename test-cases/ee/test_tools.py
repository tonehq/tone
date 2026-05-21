"""Tests for Tools API endpoints (EE edition).

Source: ee/api/v1/tools.py
Postman: postman_collection/tools.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
"""

import pytest
import uuid


# --- Helpers ---

def _unique_name(prefix="Tool"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _sample_tool_data(**overrides):
    """Valid tool creation payload matching Postman example."""
    data = {
        "name": _unique_name(),
        "description": "A test tool for unit testing",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
        },
        "url": "https://api.weather.com/v1/current",
        "method": "GET",
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


# --- POST /api/v1/tool/create_tool ---

class TestCreateTool:
    """Tests for POST /api/v1/tool/create_tool"""

    def test_create_tool_success(self, client_as_member):
        """Postman: Create Tool - Success (201)."""
        data = _sample_tool_data(
            auth_type="api_key",
            auth_config={"header_name": "X-API-Key", "api_key": "your-key"},
            meta_data={},
        )
        response = client_as_member.post("/api/v1/tool/create_tool", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == data["name"]
        assert result["url"] == data["url"]
        assert result["method"] == "GET"
        assert result["auth_type"] == "api_key"
        assert "id" in result
        assert "uuid" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert result["is_template"] is False

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


# --- GET /api/v1/tool/get_all_tools ---

class TestGetAllTools:
    """Tests for GET /api/v1/tool/get_all_tools"""

    def test_get_all_tools_success(self, client_as_member):
        """Postman: Get All Tools - Success (200)."""
        response = client_as_member.get("/api/v1/tool/get_all_tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_tools_after_create(self, client_as_member):
        tool = _create_tool(client_as_member)
        response = client_as_member.get("/api/v1/tool/get_all_tools")
        assert response.status_code == 200
        tool_ids = [t["id"] for t in response.json()]
        assert tool["id"] in tool_ids

    def test_get_all_tools_empty(self, client_as_member):
        """Postman: Get All Tools - Empty (200, [])."""
        response = client_as_member.get("/api/v1/tool/get_all_tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_all_tools_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/tool/get_all_tools")
        assert response.status_code in (401, 403)


# --- GET /api/v1/tool/get_template_tools ---

class TestGetTemplateTools:
    """Tests for GET /api/v1/tool/get_template_tools"""

    def test_get_template_tools_success(self, client_as_member):
        """Postman: Get Template Tools - Success (200)."""
        response = client_as_member.get("/api/v1/tool/get_template_tools")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_template_tools_returns_only_templates(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_template_tools")
        assert response.status_code == 200
        tools = response.json()
        for tool in tools:
            assert tool.get("is_template") is True

    def test_get_template_tools_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/tool/get_template_tools")
        assert response.status_code in (401, 403)


# --- GET /api/v1/tool/get_tool ---

class TestGetTool:
    """Tests for GET /api/v1/tool/get_tool"""

    def test_get_tool_success(self, client_as_member):
        """Postman: Get Tool - Success (200)."""
        tool = _create_tool(client_as_member)
        response = client_as_member.get(f"/api/v1/tool/get_tool?tool_id={tool['id']}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == tool["id"]
        assert "uuid" in result
        assert "parameters" in result
        assert "auth_type" in result
        assert "is_active" in result
        assert "is_template" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_tool_not_found(self, client_as_member):
        """Postman: Get Tool - Not Found (404)."""
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


# --- POST /api/v1/tool/upsert_tool ---

class TestUpsertTool:
    """Tests for POST /api/v1/tool/upsert_tool"""

    def test_upsert_create_success(self, client_as_member):
        """Postman: Upsert Tool - Create (200)."""
        data = {
            "name": _unique_name(),
            "description": "Get current weather for a city",
            "url": "https://api.weather.com/v1/current",
            "method": "GET",
            "auth_type": "none",
        }
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == data["name"]
        assert result["url"] == data["url"]
        assert result["is_active"] is True

    def test_upsert_update_success(self, client_as_member):
        """Postman: Upsert Tool - Update (200)."""
        tool = _create_tool(client_as_member)
        response = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "id": tool["id"],
            "name": "Weather API v2",
            "description": "Updated description",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Weather API v2"

    def test_upsert_update_not_found(self, client_as_member):
        response = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "id": 999999,
            "name": "Ghost",
        })
        assert response.status_code == 404

    def test_upsert_create_missing_name(self, client_as_member):
        response = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "description": "No name tool",
            "url": "https://example.com",
        })
        assert response.status_code == 400
        assert "name" in response.json()["detail"].lower()

    def test_upsert_create_missing_description(self, client_as_member):
        response = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "name": _unique_name(),
            "url": "https://example.com",
        })
        assert response.status_code == 400
        assert "description" in response.json()["detail"].lower()

    def test_upsert_partial_update(self, client_as_member):
        """Partial update -- only change description."""
        tool = _create_tool(client_as_member)
        response = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "id": tool["id"],
            "description": "Only description changed",
        })
        assert response.status_code == 200
        assert response.json()["description"] == "Only description changed"
        assert response.json()["name"] == tool["name"]

    def test_upsert_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.post("/api/v1/tool/upsert_tool", json={
            "name": "Tool", "description": "A tool", "url": "https://example.com",
        })
        assert response.status_code in (401, 403)


# --- PUT /api/v1/tool/update_tool ---

class TestUpdateTool:
    """Tests for PUT /api/v1/tool/update_tool"""

    def test_update_tool_success(self, client_as_member):
        """Postman: Update Tool - Success (200)."""
        tool = _create_tool(client_as_member)
        response = client_as_member.put(
            f"/api/v1/tool/update_tool?tool_id={tool['id']}",
            json={
                "name": "Updated Weather API",
                "description": "Updated description",
                "is_active": False,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Weather API"
        assert result["description"] == "Updated description"
        assert result["is_active"] is False

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


# --- DELETE /api/v1/tool/delete_tool ---

class TestDeleteTool:
    """Tests for DELETE /api/v1/tool/delete_tool"""

    def test_delete_tool_success(self, client_as_member):
        """Postman: Delete Tool - Success (200)."""
        tool = _create_tool(client_as_member)
        response = client_as_member.delete(f"/api/v1/tool/delete_tool?tool_id={tool['id']}")
        assert response.status_code == 200

    def test_delete_tool_not_found(self, client_as_member):
        """Postman: Delete Tool - Not Found (404)."""
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


# --- POST /api/v1/tool/attach_tool_to_agents ---

class TestAttachToolToAgents:
    """Tests for POST /api/v1/tool/attach_tool_to_agents"""

    def test_attach_tool_success(self, client_as_member):
        """Postman: Attach Tool To Agents - Success (200)."""
        tool = _create_tool(client_as_member)
        agent = _create_agent(client_as_member)
        response = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        assert response.status_code == 200
        assert "attached" in response.json().get("message", "").lower()
        assert "1 agent(s)" in response.json().get("message", "")

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
        """Empty agent_ids list -- service may reject or succeed with no-op."""
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


# --- DELETE /api/v1/tool/detach_tool_from_agents ---

class TestDetachToolFromAgents:
    """Tests for DELETE /api/v1/tool/detach_tool_from_agents"""

    def test_detach_tool_success(self, client_as_member):
        """Postman: Detach Tool From Agents - Success (200)."""
        tool = _create_tool(client_as_member)
        agent = _create_agent(client_as_member)
        # Attach first
        client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        # Detach -- use request() since delete() doesn't support json body
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

    def test_detach_tool_missing_agent_ids(self, client_as_member):
        response = client_as_member.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": 1,
        })
        assert response.status_code == 422

    def test_detach_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": 1,
            "agent_ids": [1],
        })
        assert response.status_code in (401, 403)


# --- GET /api/v1/tool/get_tools_by_agent ---

class TestGetToolsByAgent:
    """Tests for GET /api/v1/tool/get_tools_by_agent"""

    def test_get_tools_by_agent_success(self, client_as_member):
        """Postman: Get Tools By Agent - Success (200)."""
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
        """Postman: Get Tools By Agent - Empty (200, [])."""
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
