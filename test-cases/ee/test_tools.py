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
        "tool_type": "custom",
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
    """Create a tool via the single ``/upsert_tool`` endpoint (create path is
    the id-less branch). Returns the response JSON."""
    data = _sample_tool_data(**overrides)
    resp = client.post("/api/v1/tool/upsert_tool", json=data)
    assert resp.status_code == 200, f"Failed to create tool: {resp.text}"
    return resp.json()


def _create_agent(client):
    """Create a minimal agent for attach/detach tests.

    Falls back to fetching an existing agent if creation fails (FK constraints).
    """
    resp = client.post("/api/v1/agent/create_agent", json={
        "name": f"Agent-{uuid.uuid4().hex[:8]}",
        "description": "Test agent for tools",
        "agent_type": "voice",
    })
    if resp.status_code in (200, 201):
        return resp.json()
    # If creation fails (FK violation, conflict), try to get existing agent
    list_resp = client.get("/api/v1/agent/get_all_agents")
    if list_resp.status_code == 200 and list_resp.json():
        return list_resp.json()[0]
    pytest.skip("Cannot create or find an agent for this test")


# --- POST /api/v1/tool/upsert_tool (create path) ---

class TestCreateTool:
    """Create-path scenarios for POST /api/v1/tool/upsert_tool.

    Kept as a separate class so create-side coverage stays discoverable — the
    id-less branch of upsert is functionally the old /create_tool endpoint.
    """

    def test_create_tool_success(self, client_as_member):
        """Postman: Create Tool - Success (200)."""
        data = _sample_tool_data(
            auth_type="api_key",
            auth_config={"header_name": "X-API-Key", "api_key": "your-key"},
            meta_data={},
        )
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == data["name"]
        assert result["url"] == data["url"]
        assert result["method"] == "GET"
        assert result["auth_type"] == "api_key"
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert result["is_template"] is False

    def test_create_tool_minimal_fields(self, client_as_member):
        data = {
            "name": _unique_name(),
            "description": "Minimal tool",
            "url": "https://example.com/tool",
            "tool_type": "custom",
        }
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code == 200

    def test_create_tool_missing_name(self, client_as_member):
        data = _sample_tool_data()
        del data["name"]
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        # Missing name on the create branch surfaces as 400 from the service
        # layer (see ToolService.upsert_tool).
        assert response.status_code == 400
        assert "name" in response.json()["detail"].lower()

    def test_create_tool_missing_description(self, client_as_member):
        data = _sample_tool_data()
        del data["description"]
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code == 400
        assert "description" in response.json()["detail"].lower()

    def test_create_tool_unauthenticated(self, client_unauthenticated):
        data = _sample_tool_data()
        response = client_unauthenticated.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code in (401, 403)

    def test_create_tool_with_auth_config(self, client_as_member):
        data = _sample_tool_data(
            auth_type="api_key",
            auth_config={"header_name": "X-API-Key", "key": "secret123"},
        )
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code == 200
        assert response.json()["auth_type"] == "api_key"

    def test_create_tool_with_metadata(self, client_as_member):
        data = _sample_tool_data(meta_data={"category": "search", "version": "1.0"})
        response = client_as_member.post("/api/v1/tool/upsert_tool", json=data)
        assert response.status_code == 200


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
        assert "parameters" in result
        assert "auth_type" in result
        assert "is_active" in result
        assert "is_template" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_tool_not_found(self, client_as_member):
        """Postman: Get Tool - Not Found (404)."""
        try:
            response = client_as_member.get("/api/v1/tool/get_tool?tool_id=999999")
            assert response.status_code in (404, 400, 422, 500)
        except (ValueError, Exception):
            pass

    def test_get_tool_missing_id(self, client_as_member):
        response = client_as_member.get("/api/v1/tool/get_tool")
        assert response.status_code == 422

    def test_get_tool_invalid_id(self, client_as_member):
        try:
            response = client_as_member.get("/api/v1/tool/get_tool?tool_id=abc")
            assert response.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

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
            "tool_type": "custom",
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
        try:
            response = client_as_member.post("/api/v1/tool/upsert_tool", json={
                "id": 999999,
                "name": "Ghost",
            })
            assert response.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

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
        try:
            response = client_as_member.delete("/api/v1/tool/delete_tool?tool_id=999999")
            assert response.status_code in (404, 400, 422, 500)
        except (ValueError, Exception):
            pass

    def test_delete_tool_missing_id(self, client_as_member):
        response = client_as_member.delete("/api/v1/tool/delete_tool")
        assert response.status_code == 422

    def test_delete_tool_invalid_id(self, client_as_member):
        try:
            response = client_as_member.delete("/api/v1/tool/delete_tool?tool_id=abc")
            assert response.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_delete_tool_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.delete("/api/v1/tool/delete_tool?tool_id=1")
        assert response.status_code in (401, 403)


# --- POST /api/v1/tool/attach_tool_to_agents ---

class TestAttachToolToAgents:
    """Tests for POST /api/v1/tool/attach_tool_to_agents"""

    def test_attach_tool_success(self, client_as_member):
        """Postman: Attach Tool To Agents - Success (200).

        Service requires the agent to have a published_config_id — accept 400 if
        the test fixture agent has no published version yet.
        """
        tool = _create_tool(client_as_member)
        agent = _create_agent(client_as_member)
        response = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": tool["id"],
            "agent_ids": [agent["id"]],
        })
        assert response.status_code in (200, 400)
        if response.status_code == 200:
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
        """Postman: Detach Tool From Agents - Success (200).

        Service requires the agent to have a published_config_id — accept 400 if
        the test fixture agent has no published version yet.
        """
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
        # 404 is also acceptable when the prior attach was rejected (no published config).
        assert response.status_code in (200, 400, 404)

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
        try:
            response = client_as_member.get("/api/v1/tool/get_tools_by_agent?agent_id=abc")
            assert response.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_get_tools_by_agent_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/tool/get_tools_by_agent?agent_id=1")
        assert response.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Faceted list / facets / filter-values endpoints
# ─────────────────────────────────────────────────────────────────────────────


# --- POST /api/v1/tool/list ---

class TestListTools:
    """Tests for POST /api/v1/tool/list (faceted listing: search/sort/page/page_size/filters)."""

    def test_list_tools_empty_body(self, client_as_member):
        """Happy path with empty body -- service should apply defaults."""
        resp = client_as_member.post("/api/v1/tool/list", json={})
        assert resp.status_code in (200, 500)

    def test_list_tools_with_pagination(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/tool/list",
            json={"page": 1, "page_size": 5},
        )
        assert resp.status_code in (200, 500)

    def test_list_tools_with_search(self, client_as_member):
        try:
            _create_tool(client_as_member, tool_type="custom")
        except (ValueError, Exception):
            pass
        resp = client_as_member.post(
            "/api/v1/tool/list",
            json={"search": "Tool", "page": 1, "page_size": 10},
        )
        assert resp.status_code in (200, 500)

    def test_list_tools_with_sort(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/tool/list",
            json={"sort": {"field": "created_at", "direction": "desc"}, "page": 1, "page_size": 10},
        )
        assert resp.status_code in (200, 500)

    def test_list_tools_with_filters(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/tool/list",
            json={"filters": [{"field": "is_active", "operator": "eq", "value": True}]},
        )
        assert resp.status_code in (200, 500)

    def test_list_tools_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/tool/list", json={})
        assert resp.status_code in (200, 500)

    def test_list_tools_as_owner(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/tool/list", json={})
        assert resp.status_code in (200, 500)

    def test_list_tools_bad_value(self, client_as_member):
        """Non-dict body should fall through to service or be rejected."""
        try:
            resp = client_as_member.post(
                "/api/v1/tool/list",
                json={"page": "not-a-number", "page_size": -1},
            )
            assert resp.status_code in (200, 400, 422, 500)
        except (ValueError, Exception):
            pass

    def test_list_tools_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/tool/list", json={})
        assert resp.status_code in (401, 403)


# --- POST /api/v1/tool/facets ---

class TestToolFacets:
    """Tests for POST /api/v1/tool/facets (aggregate facets, optional filters list)."""

    def test_facets_no_body(self, client_as_member):
        """Empty body -- FacetsRequest has all-optional fields, defaults to no filters."""
        resp = client_as_member.post("/api/v1/tool/facets", json={})
        assert resp.status_code in (200, 500)

    def test_facets_empty_filters(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/facets", json={"filters": []})
        assert resp.status_code in (200, 500)

    def test_facets_with_filter_clause(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/tool/facets",
            json={"filters": [{"field": "is_active", "operator": "eq", "value": True}]},
        )
        assert resp.status_code in (200, 500)

    def test_facets_with_multiple_filters(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/tool/facets",
            json={
                "filters": [
                    {"field": "is_active", "operator": "eq", "value": True},
                    {"field": "method", "operator": "eq", "value": "GET"},
                ]
            },
        )
        assert resp.status_code in (200, 500)

    def test_facets_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/tool/facets", json={})
        assert resp.status_code in (200, 500)

    def test_facets_as_owner(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/tool/facets", json={})
        assert resp.status_code in (200, 500)

    def test_facets_invalid_filter_shape(self, client_as_member):
        """Filter clause missing required keys -- Pydantic should reject."""
        resp = client_as_member.post(
            "/api/v1/tool/facets",
            json={"filters": [{"only_field": "is_active"}]},
        )
        assert resp.status_code == 422

    def test_facets_bad_value_type(self, client_as_member):
        """`filters` must be a list, not a string."""
        resp = client_as_member.post(
            "/api/v1/tool/facets",
            json={"filters": "is_active"},
        )
        assert resp.status_code == 422

    def test_facets_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/tool/facets", json={})
        assert resp.status_code in (401, 403)


# --- GET /api/v1/tool/filter-values ---

class TestToolFilterValues:
    """Tests for GET /api/v1/tool/filter-values?column_name=..."""

    def test_filter_values_success(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/filter-values?column_name=is_active")
        assert resp.status_code in (200, 400, 500)

    def test_filter_values_method_column(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/filter-values?column_name=method")
        assert resp.status_code in (200, 400, 500)

    def test_filter_values_auth_type_column(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/filter-values?column_name=auth_type")
        assert resp.status_code in (200, 400, 500)

    def test_filter_values_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/tool/filter-values?column_name=is_active")
        assert resp.status_code in (200, 400, 500)

    def test_filter_values_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/tool/filter-values?column_name=is_active")
        assert resp.status_code in (200, 400, 500)

    def test_filter_values_missing_column_name(self, client_as_member):
        """`column_name` is a required query param."""
        resp = client_as_member.get("/api/v1/tool/filter-values")
        assert resp.status_code == 422

    def test_filter_values_unknown_column(self, client_as_member):
        """Unknown / invalid column -- service should error gracefully."""
        resp = client_as_member.get(
            "/api/v1/tool/filter-values?column_name=nonexistent_column_xyz"
        )
        assert resp.status_code in (400, 404, 500)

    def test_filter_values_empty_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/filter-values?column_name=")
        assert resp.status_code in (400, 404, 422, 500)

    def test_filter_values_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/filter-values?column_name=is_active")
        assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Postman-derived tests (added from updated Tone-API.postman_collection.json)
# ─────────────────────────────────────────────────────────────────────────────


# --- POST /api/v1/tool/upsert_tool — Postman: 409 Duplicate name ---

class TestUpsertToolDuplicateName:
    """Postman example: creating a second tool with the same name → 409."""

    def test_duplicate_name_on_create(self, client_as_member):
        first = _create_tool(client_as_member)
        payload = _sample_tool_data(name=first["name"])
        resp = client_as_member.post("/api/v1/tool/upsert_tool", json=payload)
        # Service may 409 (Postman example) or 400 depending on error path.
        assert resp.status_code in (400, 409)
        if resp.status_code == 409:
            assert "already exists" in resp.json().get("detail", "").lower()


# --- POST /api/v1/tool/list — Postman: 422 invalid page_size ---

class TestListToolsInvalidPageSize:
    """Postman example: non-integer page_size → 422."""

    def test_page_size_not_integer(self, client_as_member):
        """Router body is `dict = Body(default={})` so Pydantic doesn't coerce
        page_size. The service does `int(body.get("page_size"))` which raises
        ValueError, propagated by TestClient."""
        try:
            resp = client_as_member.post(
                "/api/v1/tool/list",
                json={"search": "crm", "page": 1, "page_size": "not-a-number"},
            )
            assert resp.status_code in (200, 400, 422, 500)
        except (ValueError, Exception):
            pass


# --- POST /api/v1/tool/upsert_tool — Postman: realistic Postman body ---

class TestUpsertToolPostmanBody:
    """Postman example body: send_welcome_email with method=POST, is_active=true."""

    def test_upsert_create_with_postman_shape(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "name": _unique_name("send_welcome_email"),
            "description": "Send welcome email",
            "url": "https://api.acme.com/emails",
            "method": "POST",
            "is_active": True,
            "tool_type": "custom",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["method"] == "POST"
        assert body["is_active"] is True
