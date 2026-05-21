"""Tests for Tools API endpoints (Core edition).

Source: core/api/v1/tools.py
Postman: tools.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


PATCH_TARGET = "core.api.v1.tools.ToolService"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def create_tool_payload():
    """Postman: Create Tool request body."""
    return {
        "name": "Weather API",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"],
        },
        "url": "https://api.weather.com/v1/current",
        "method": "GET",
        "auth_type": "api_key",
        "auth_config": {"header_name": "X-API-Key", "api_key": "your-key"},
        "meta_data": {},
        "is_active": True,
    }


@pytest.fixture
def tool_response():
    """Postman: Create Tool response body."""
    return {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Weather API",
        "description": "Get current weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
        "url": "https://api.weather.com/v1/current",
        "method": "GET",
        "auth_type": "api_key",
        "auth_config": {"header_name": "X-API-Key"},
        "meta_data": {},
        "is_active": True,
        "is_template": False,
        "created_at": "2026-01-15T10:00:00",
        "updated_at": "2026-01-15T10:00:00",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/tool/create_tool
# ---------------------------------------------------------------------------

class TestCreateTool:
    """Tests for POST /api/v1/tool/create_tool"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member, create_tool_payload, tool_response):
        """Postman: Create Tool - Success (201)"""
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.create_tool.return_value = mock_tool
        mock_instance.tool_response.return_value = tool_response
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/create_tool", json=create_tool_payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Weather API"
        assert data["url"] == "https://api.weather.com/v1/current"
        assert data["method"] == "GET"
        assert data["auth_type"] == "api_key"
        assert data["is_active"] is True
        assert data["is_template"] is False
        mock_instance.create_tool.assert_called_once()

    @patch(PATCH_TARGET)
    def test_with_all_fields(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.create_tool.return_value = MagicMock()
        mock_instance.tool_response.return_value = {"id": 1}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/create_tool", json={
            "name": "Full Tool",
            "description": "Complete tool",
            "url": "https://example.com/api",
            "method": "GET",
            "parameters": {"key": "value"},
            "auth_type": "bearer",
            "auth_config": {"token": "abc"},
            "meta_data": {"category": "test"},
            "is_active": False,
        })

        assert resp.status_code == 201

    def test_missing_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/create_tool", json={
            "description": "A tool", "url": "https://example.com"
        })
        assert resp.status_code == 422

    def test_missing_description(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/create_tool", json={
            "name": "Tool", "url": "https://example.com"
        })
        assert resp.status_code == 422

    def test_missing_url(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/create_tool", json={
            "name": "Tool", "description": "A tool"
        })
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/tool/create_tool", json={
            "name": "Tool", "description": "A tool", "url": "https://example.com"
        })
        assert resp.status_code in (401, 403)

    @patch(PATCH_TARGET)
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.create_tool.side_effect = HTTPException(status_code=400, detail="Invalid")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/create_tool", json={
            "name": "Tool", "description": "A tool", "url": "https://example.com"
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/v1/tool/get_all_tools
# ---------------------------------------------------------------------------

class TestGetAllTools:
    """Tests for GET /api/v1/tool/get_all_tools"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get All Tools - Success (200)"""
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_tool.is_template = False
        mock_instance.get_tools.return_value = [mock_tool, MagicMock(is_template=False)]
        mock_instance.tool_response.side_effect = [
            {
                "id": 1,
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Weather API",
                "description": "Get current weather",
                "url": "https://api.weather.com/v1/current",
                "method": "GET",
                "auth_type": "api_key",
                "is_active": True,
                "is_template": False,
            },
            {"id": 2, "name": "Tool 2", "is_template": False},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_all_tools")

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch(PATCH_TARGET)
    def test_empty(self, mock_service_cls, client_as_member):
        """Postman: Get All Tools - Empty (200)"""
        mock_instance = MagicMock()
        mock_instance.get_tools.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_all_tools")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch(PATCH_TARGET)
    def test_filters_out_templates(self, mock_service_cls, client_as_member):
        """get_all_tools should not include template tools."""
        mock_instance = MagicMock()
        template_tool = MagicMock(is_template=True)
        regular_tool = MagicMock(is_template=False)
        mock_instance.get_tools.return_value = [template_tool, regular_tool]
        mock_instance.tool_response.return_value = {"id": 1, "name": "Regular"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_all_tools")

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_all_tools")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/tool/get_template_tools
# ---------------------------------------------------------------------------

class TestGetTemplateTools:
    """Tests for GET /api/v1/tool/get_template_tools"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Template Tools - Success (200)"""
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.get_template_tools.return_value = [mock_tool]
        mock_instance.tool_response.return_value = {
            "id": 10,
            "name": "Google Calendar - Create Event",
            "description": "Create a Google Calendar event",
            "is_template": True,
            "is_active": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_template_tools")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["is_template"] is True

    @patch(PATCH_TARGET)
    def test_empty(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_template_tools.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_template_tools")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_template_tools")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/tool/get_tool
# ---------------------------------------------------------------------------

class TestGetTool:
    """Tests for GET /api/v1/tool/get_tool"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Tool - Success (200)"""
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.get_tool.return_value = mock_tool
        mock_instance.tool_response.return_value = {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Weather API",
            "description": "Get current weather",
            "parameters": {},
            "url": "https://api.weather.com/v1/current",
            "method": "GET",
            "auth_type": "api_key",
            "auth_config": {},
            "meta_data": {},
            "oauth_connection_id": None,
            "is_active": True,
            "is_template": False,
            "created_at": "2026-01-15T10:00:00",
            "updated_at": "2026-01-15T10:00:00",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tool", params={"tool_id": 1})

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "Weather API"
        mock_instance.get_tool.assert_called_once_with(1)

    @patch(PATCH_TARGET)
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Get Tool - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.get_tool.side_effect = HTTPException(status_code=404, detail="Tool not found")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tool", params={"tool_id": 999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tool not found"

    def test_missing_tool_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/get_tool")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_tool", params={"tool_id": 1})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/tool/upsert_tool
# ---------------------------------------------------------------------------

class TestUpsertTool:
    """Tests for POST /api/v1/tool/upsert_tool"""

    @patch(PATCH_TARGET)
    def test_upsert_create_success(self, mock_service_cls, client_as_member):
        """Postman: Upsert Tool - Create (200)"""
        mock_instance = MagicMock()
        mock_instance.upsert_tool.return_value = MagicMock()
        mock_instance.tool_response.return_value = {
            "id": 1,
            "name": "Weather API",
            "description": "Get current weather for a city",
            "url": "https://api.weather.com/v1/current",
            "method": "GET",
            "auth_type": "none",
            "is_active": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "name": "Weather API",
            "description": "Get current weather for a city",
            "url": "https://api.weather.com/v1/current",
            "method": "GET",
            "auth_type": "none",
        })

        assert resp.status_code == 200
        assert resp.json()["name"] == "Weather API"
        mock_instance.upsert_tool.assert_called_once()

    @patch(PATCH_TARGET)
    def test_upsert_update_success(self, mock_service_cls, client_as_member):
        """Postman: Upsert Tool - Update (200)"""
        mock_instance = MagicMock()
        mock_instance.upsert_tool.return_value = MagicMock()
        mock_instance.tool_response.return_value = {
            "id": 1,
            "name": "Weather API v2",
            "description": "Updated description",
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "id": 1,
            "name": "Weather API v2",
            "description": "Updated description",
        })

        assert resp.status_code == 200
        assert resp.json()["name"] == "Weather API v2"

    @patch(PATCH_TARGET)
    def test_upsert_update_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_tool.side_effect = HTTPException(status_code=404, detail="Tool not found")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "id": 999,
            "name": "X",
        })
        assert resp.status_code == 404

    @patch(PATCH_TARGET)
    def test_upsert_create_missing_name(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_tool.side_effect = HTTPException(
            status_code=400, detail="name is required when creating a new tool"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "description": "A tool",
        })
        assert resp.status_code == 400

    @patch(PATCH_TARGET)
    def test_upsert_create_missing_description(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.upsert_tool.side_effect = HTTPException(
            status_code=400, detail="description is required when creating a new tool"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "name": "Tool",
        })
        assert resp.status_code == 400

    @patch(PATCH_TARGET)
    def test_upsert_built_in_tool_update_meta_data(self, mock_service_cls, client_as_member):
        """Built-in tools should only allow meta_data and is_active updates."""
        mock_instance = MagicMock()
        mock_instance.upsert_tool.return_value = MagicMock()
        mock_instance.tool_response.return_value = {
            "id": 1, "name": "send_sms", "tool_type": "built_in",
            "meta_data": {"account_sid": "AC123", "auth_token": "tok", "from_number": "+1234567890"},
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/upsert_tool", json={
            "id": 1,
            "meta_data": {"account_sid": "AC123", "auth_token": "tok", "from_number": "+1234567890"},
        })

        assert resp.status_code == 200
        assert resp.json()["tool_type"] == "built_in"
        assert resp.json()["meta_data"]["account_sid"] == "AC123"

    def test_upsert_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/tool/upsert_tool", json={
            "name": "Tool", "description": "A tool",
        })
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /api/v1/tool/update_tool
# ---------------------------------------------------------------------------

class TestUpdateTool:
    """Tests for PUT /api/v1/tool/update_tool"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Update Tool - Success (200)"""
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.update_tool.return_value = mock_tool
        mock_instance.tool_response.return_value = {
            "id": 1,
            "name": "Updated Weather API",
            "description": "Updated description",
            "is_active": False,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.put(
            "/api/v1/tool/update_tool",
            params={"tool_id": 1},
            json={
                "name": "Updated Weather API",
                "description": "Updated description",
                "is_active": False,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Weather API"
        assert data["is_active"] is False
        mock_instance.update_tool.assert_called_once_with(1, {
            "name": "Updated Weather API",
            "description": "Updated description",
            "is_active": False,
        })

    @patch(PATCH_TARGET)
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.update_tool.side_effect = HTTPException(status_code=404, detail="Not found")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.put(
            "/api/v1/tool/update_tool",
            params={"tool_id": 999},
            json={"name": "X"},
        )
        assert resp.status_code == 404

    def test_missing_tool_id(self, client_as_member):
        resp = client_as_member.put("/api/v1/tool/update_tool", json={"name": "X"})
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.put(
            "/api/v1/tool/update_tool", params={"tool_id": 1}, json={"name": "X"}
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/tool/delete_tool
# ---------------------------------------------------------------------------

class TestDeleteTool:
    """Tests for DELETE /api/v1/tool/delete_tool"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Delete Tool - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.delete_tool.return_value = {"message": "Tool deleted successfully"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete("/api/v1/tool/delete_tool", params={"tool_id": 1})

        assert resp.status_code == 200
        assert resp.json()["message"] == "Tool deleted successfully"
        mock_instance.delete_tool.assert_called_once_with(1)

    @patch(PATCH_TARGET)
    def test_not_found(self, mock_service_cls, client_as_member):
        """Postman: Delete Tool - Not Found (404)"""
        mock_instance = MagicMock()
        mock_instance.delete_tool.side_effect = HTTPException(status_code=404, detail="Tool not found")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete("/api/v1/tool/delete_tool", params={"tool_id": 999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tool not found"

    @patch(PATCH_TARGET)
    def test_delete_built_in_tool_rejected(self, mock_service_cls, client_as_member):
        """Built-in tools cannot be deleted."""
        mock_instance = MagicMock()
        mock_instance.delete_tool.side_effect = HTTPException(
            status_code=400, detail="Built-in tools cannot be deleted"
        )
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete("/api/v1/tool/delete_tool", params={"tool_id": 1})
        assert resp.status_code == 400
        assert "Built-in" in resp.json()["detail"]

    def test_missing_tool_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/tool/delete_tool")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/tool/delete_tool", params={"tool_id": 1})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/tool/attach_tool_to_agents
# ---------------------------------------------------------------------------

class TestAttachToolToAgents:
    """Tests for POST /api/v1/tool/attach_tool_to_agents"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Attach Tool To Agents - Success (200)"""
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": 1, "agent_ids": [1, 2, 3],
        })

        assert resp.status_code == 200
        assert "3 agent(s)" in resp.json()["message"]
        mock_instance.attach_tool_to_agents.assert_called_once_with([1, 2, 3], 1)

    def test_missing_tool_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "agent_ids": [1],
        })
        assert resp.status_code == 422

    def test_missing_agent_ids(self, client_as_member):
        resp = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": 1,
        })
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": 1, "agent_ids": [1],
        })
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# DELETE /api/v1/tool/detach_tool_from_agents
# ---------------------------------------------------------------------------

class TestDetachToolFromAgents:
    """Tests for DELETE /api/v1/tool/detach_tool_from_agents"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Detach Tool From Agents - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.detach_tool_from_agents.return_value = {
            "message": "Tool detached from 2 agent(s) successfully"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": 1, "agent_ids": [1, 2],
        })

        assert resp.status_code == 200
        mock_instance.detach_tool_from_agents.assert_called_once_with([1, 2], 1)

    def test_missing_tool_id(self, client_as_member):
        resp = client_as_member.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "agent_ids": [1],
        })
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": 1, "agent_ids": [1],
        })
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/tool/get_tools_by_agent
# ---------------------------------------------------------------------------

class TestGetToolsByAgent:
    """Tests for GET /api/v1/tool/get_tools_by_agent"""

    @patch(PATCH_TARGET)
    def test_success(self, mock_service_cls, client_as_member):
        """Postman: Get Tools By Agent - Success (200)"""
        mock_instance = MagicMock()
        mock_instance.get_tools_by_agent.return_value = [MagicMock()]
        mock_instance.tool_response.return_value = {
            "id": 1,
            "name": "Weather API",
            "description": "Get current weather",
            "is_active": True,
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tools_by_agent", params={"agent_id": 1})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Weather API"
        mock_instance.get_tools_by_agent.assert_called_once_with(1)

    @patch(PATCH_TARGET)
    def test_empty(self, mock_service_cls, client_as_member):
        """Postman: Get Tools By Agent - Empty (200)"""
        mock_instance = MagicMock()
        mock_instance.get_tools_by_agent.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tools_by_agent", params={"agent_id": 1})

        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/get_tools_by_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_tools_by_agent", params={"agent_id": 1})
        assert resp.status_code in (401, 403)
