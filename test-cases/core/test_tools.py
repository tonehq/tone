"""Tests for Tools API endpoints (Core edition).

Source: core/api/v1/tools.py
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# POST /api/v1/tool/create_tool
# ---------------------------------------------------------------------------
class TestCreateTool:
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.create_tool.return_value = mock_tool
        mock_instance.tool_response.return_value = {
            "id": 1, "name": "My Tool", "url": "https://example.com/api"
        }
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/create_tool", json={
            "name": "My Tool",
            "description": "A test tool",
            "url": "https://example.com/api",
        })

        assert resp.status_code == 201
        assert resp.json()["name"] == "My Tool"
        mock_instance.create_tool.assert_called_once()

    @patch("ee.api.v1.tools.ToolService")
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

    @patch("ee.api.v1.tools.ToolService")
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
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_tools.return_value = [MagicMock(), MagicMock()]
        mock_instance.tool_response.side_effect = [
            {"id": 1, "name": "Tool 1"},
            {"id": 2, "name": "Tool 2"},
        ]
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_all_tools")

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @patch("ee.api.v1.tools.ToolService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_tools.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_all_tools")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_all_tools")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/tool/get_tool
# ---------------------------------------------------------------------------
class TestGetTool:
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.get_tool.return_value = mock_tool
        mock_instance.tool_response.return_value = {"id": 1, "name": "Tool"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tool", params={"tool_id": 1})

        assert resp.status_code == 200
        assert resp.json()["id"] == 1
        mock_instance.get_tool.assert_called_once_with(1)

    @patch("ee.api.v1.tools.ToolService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_tool.side_effect = HTTPException(status_code=404, detail="Not found")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tool", params={"tool_id": 999})
        assert resp.status_code == 404

    def test_missing_tool_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/get_tool")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_tool", params={"tool_id": 1})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /api/v1/tool/update_tool
# ---------------------------------------------------------------------------
class TestUpdateTool:
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_tool = MagicMock()
        mock_instance.update_tool.return_value = mock_tool
        mock_instance.tool_response.return_value = {"id": 1, "name": "Updated"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.put(
            "/api/v1/tool/update_tool",
            params={"tool_id": 1},
            json={"name": "Updated"},
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        mock_instance.update_tool.assert_called_once_with(1, {"name": "Updated"})

    @patch("ee.api.v1.tools.ToolService")
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
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_tool.return_value = {"message": "Deleted"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete("/api/v1/tool/delete_tool", params={"tool_id": 1})

        assert resp.status_code == 200
        mock_instance.delete_tool.assert_called_once_with(1)

    @patch("ee.api.v1.tools.ToolService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.delete_tool.side_effect = HTTPException(status_code=404, detail="Not found")
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.delete("/api/v1/tool/delete_tool", params={"tool_id": 999})
        assert resp.status_code == 404

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
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.post("/api/v1/tool/attach_tool_to_agents", json={
            "tool_id": 1, "agent_ids": [10, 20],
        })

        assert resp.status_code == 200
        assert "2 agent(s)" in resp.json()["message"]
        mock_instance.attach_tool_to_agents.assert_called_once_with([10, 20], 1)

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
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.detach_tool_from_agents.return_value = {"message": "Detached"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.request("DELETE", "/api/v1/tool/detach_tool_from_agents", json={
            "tool_id": 1, "agent_ids": [10],
        })

        assert resp.status_code == 200
        mock_instance.detach_tool_from_agents.assert_called_once_with([10], 1)

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
    @patch("ee.api.v1.tools.ToolService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_tools_by_agent.return_value = [MagicMock()]
        mock_instance.tool_response.return_value = {"id": 1, "name": "Tool"}
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tools_by_agent", params={"agent_id": 10})

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_instance.get_tools_by_agent.assert_called_once_with(10)

    @patch("ee.api.v1.tools.ToolService")
    def test_empty(self, mock_service_cls, client_as_member):
        mock_instance = MagicMock()
        mock_instance.get_tools_by_agent.return_value = []
        mock_service_cls.return_value = mock_instance

        resp = client_as_member.get("/api/v1/tool/get_tools_by_agent", params={"agent_id": 10})

        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/tool/get_tools_by_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/tool/get_tools_by_agent", params={"agent_id": 1})
        assert resp.status_code in (401, 403)
