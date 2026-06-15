"""Tests for Agents API endpoints (Core edition).

Source: core/api/v1/agents.py
Postman: agents.postman_collection.json
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

from core.internal.capabilities import is_ee_enabled

# main.py mounts the EE agents router under ``/api/v1/agent`` whenever the
# license check passes (or is skipped). Helpers/services patched at the wrong
# import site silently no-op, so resolve the active module first.
_AGENTS_MODULE = "ee.api.v1.agents" if is_ee_enabled() else "core.api.v1.agents"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_agent():
    return {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Sales Agent",
        "description": "Handles sales inquiries",
        "status": "active",
        "agent_type": "inbound",
        "meta_data": {},
        "created_at": "2026-01-15T10:00:00",
        "updated_at": "2026-01-15T10:00:00",
    }


@pytest.fixture
def sample_agents(sample_agent):
    return [
        sample_agent,
        {
            "id": 2,
            "uuid": "660e8400-e29b-41d4-a716-446655440001",
            "name": "Support Agent",
            "description": "Handles support tickets",
            "status": "active",
            "agent_type": "inbound",
            "meta_data": {},
            "created_at": "2026-01-15T10:00:00",
            "updated_at": "2026-01-15T10:00:00",
        },
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
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Sales Agent"
        mock_service_cls.return_value.get_all_agents.assert_called_once_with(agent_id=None)

    @patch("core.api.v1.agents.AgentService")
    def test_with_agent_id_filter(self, mock_service_cls, client_as_member, sample_agent):
        mock_service_cls.return_value.get_all_agents.return_value = [sample_agent]
        resp = client_as_member.get("/api/v1/agent/get_all_agents", params={"agent_id": 1})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        mock_service_cls.return_value.get_all_agents.assert_called_once_with(agent_id=1)

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
        mock_service_cls.return_value.get_all_agents.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/agent/get_all_agents")
        assert resp.status_code in (500, 422, 400)


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
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "Sales Agent"

    @patch("core.api.v1.agents.AgentService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.return_value = []
        resp = client_as_member.get("/api/v1/agent/get_agent", params={"agent_id": 999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Agent not found"

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/get_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/agent/get_agent", params={"agent_id": 1})
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.get("/api/v1/agent/get_agent", params={"agent_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/upsert_agent
# ---------------------------------------------------------------------------

class TestUpsertAgent:
    """Tests for POST /api/v1/agent/upsert_agent"""

    @patch("core.api.v1.agents.AgentService")
    def test_success_create(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent.return_value = {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Sales Agent",
            "description": "Handles sales inquiries",
            "status": "active",
            "agent_type": "inbound",
        }
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent",
            json={
                "name": "Sales Agent",
                "description": "Handles sales inquiries",
                "status": "active",
                "agent_type": "inbound",
                "meta_data": {},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Sales Agent"
        mock_service_cls.return_value.upsert_agent.assert_called_once()

    @patch("core.api.v1.agents.AgentService")
    def test_success_update(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent.return_value = {
            "id": 1, "name": "Updated Agent"
        }
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent",
            json={"id": 1, "name": "Updated Agent"},
        )
        assert resp.status_code == 200

    def test_missing_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent", json={"description": "no name"}
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_empty_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent", json={"name": ""}
        )
        assert resp.status_code == 400

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent/upsert_agent", json={"name": "Agent"}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.upsert_agent.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.post(
            "/api/v1/agent/upsert_agent", json={"name": "Agent"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# DELETE /api/v1/agent/delete_agent
# ---------------------------------------------------------------------------

class TestDeleteAgent:
    """Tests for DELETE /api/v1/agent/delete_agent"""

    @patch("core.api.v1.agents.AgentService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.return_value = {
            "message": "Agent deleted successfully"
        }
        resp = client_as_member.delete("/api/v1/agent/delete_agent", params={"agent_id": 1})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Agent deleted successfully"
        mock_service_cls.return_value.delete_agent.assert_called_once_with(1)

    @patch("core.api.v1.agents.AgentService")
    def test_not_found(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.side_effect = HTTPException(
            status_code=404, detail="Agent not found"
        )
        resp = client_as_member.delete("/api/v1/agent/delete_agent", params={"agent_id": 999})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Agent not found"

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/agent/delete_agent")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            "/api/v1/agent/delete_agent", params={"agent_id": 1}
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.delete_agent.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.delete("/api/v1/agent/delete_agent", params={"agent_id": 1})
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/duplicate_agent
# ---------------------------------------------------------------------------

class TestDuplicateAgent:
    """Tests for POST /api/v1/agent/duplicate_agent"""

    @patch("core.api.v1.agents.AgentService")
    def test_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.duplicate_agent.return_value = {
            "id": 2, "name": "Sales Agent Copy", "status": "active"
        }
        resp = client_as_member.post(
            "/api/v1/agent/duplicate_agent",
            json={"agent_id": 1, "name": "Sales Agent Copy"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 2
        assert data["name"] == "Sales Agent Copy"
        mock_service_cls.return_value.duplicate_agent.assert_called_once_with(
            agent_id=1, new_name="Sales Agent Copy", created_by=ANY,
        )

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/duplicate_agent",
            json={"name": "Sales Agent Copy"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "agent_id is required"

    def test_missing_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/duplicate_agent",
            json={"agent_id": 1},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "name is required"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent/duplicate_agent",
            json={"agent_id": 1, "name": "Copy"},
        )
        assert resp.status_code in (401, 403)

    @patch("core.api.v1.agents.AgentService")
    def test_service_error(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.duplicate_agent.side_effect = HTTPException(
            status_code=500, detail="DB error"
        )
        resp = client_as_member.post(
            "/api/v1/agent/duplicate_agent",
            json={"agent_id": 1, "name": "Copy"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/list — faceted list with filters/sort/pagination
# ---------------------------------------------------------------------------

class TestListAgents:
    """Tests for POST /api/v1/agent/list"""

    @patch(f"{_AGENTS_MODULE}.list_agents_for_org")
    def test_success_empty_body_uses_defaults(self, mock_list, client_as_member):
        mock_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        resp = client_as_member.post("/api/v1/agent/list", json={})
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}
        # The route should forward the empty body to the shared list helper.
        args, _ = mock_list.call_args
        assert args[2] == {}

    @patch(f"{_AGENTS_MODULE}.list_agents_for_org")
    def test_success_with_search_and_filters(self, mock_list, client_as_member, sample_agent):
        mock_list.return_value = {
            "items": [sample_agent], "total": 1, "page": 1, "page_size": 20,
        }
        body = {
            "page": 1,
            "page_size": 20,
            "search": "sales",
            "is_active": True,
            "agent_type": "inbound",
            "filters": [{"field": "agent_type", "operator": "eq", "value": "inbound"}],
            "sort_by": "name",
            "sort_order": "asc",
        }
        resp = client_as_member.post("/api/v1/agent/list", json=body)
        assert resp.status_code == 200
        assert resp.json()["items"][0]["name"] == "Sales Agent"
        args, _ = mock_list.call_args
        assert args[2] == body

    @patch(f"{_AGENTS_MODULE}.list_agents_for_org")
    def test_no_body_defaults_to_empty_dict(self, mock_list, client_as_member):
        """The route declares ``Body(default={})`` so omitting the body still works."""
        mock_list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        resp = client_as_member.post("/api/v1/agent/list")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/agent/list", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/facets — per-value facet counts
# ---------------------------------------------------------------------------

class TestAgentFacets:
    """Tests for POST /api/v1/agent/facets"""

    @patch(f"{_AGENTS_MODULE}.agent_facets_for_org")
    def test_success_no_filters(self, mock_facets, client_as_member):
        mock_facets.return_value = {
            "agent_type": {"inbound": 4, "outbound": 1},
            "status": {"active": 3, "inactive": 2},
        }
        resp = client_as_member.post("/api/v1/agent/facets", json={})
        assert resp.status_code == 200
        assert resp.json()["agent_type"]["inbound"] == 4
        args, _ = mock_facets.call_args
        # The helper is called with filters=None when the body has no filters.
        assert args[2] is None

    @patch(f"{_AGENTS_MODULE}.agent_facets_for_org")
    def test_success_with_filters(self, mock_facets, client_as_member):
        mock_facets.return_value = {"agent_type": {"inbound": 1}}
        resp = client_as_member.post(
            "/api/v1/agent/facets",
            json={"filters": [{"field": "status", "operator": "eq", "value": "active"}]},
        )
        assert resp.status_code == 200
        args, _ = mock_facets.call_args
        assert args[2] == [{"field": "status", "operator": "eq", "value": "active"}]

    def test_invalid_filter_shape(self, client_as_member):
        """Filter rows missing field/operator must fail Pydantic validation."""
        resp = client_as_member.post(
            "/api/v1/agent/facets",
            json={"filters": [{"value": "active"}]},
        )
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/agent/facets", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/agent/filter-values — distinct values for autocomplete
# ---------------------------------------------------------------------------

class TestAgentFilterValues:
    """Tests for GET /api/v1/agent/filter-values"""

    @patch(f"{_AGENTS_MODULE}.agent_filter_values_for_org")
    def test_success(self, mock_values, client_as_member):
        mock_values.return_value = {"values": ["Sales Agent", "Support Agent"]}
        resp = client_as_member.get(
            "/api/v1/agent/filter-values", params={"column_name": "name"},
        )
        assert resp.status_code == 200
        assert resp.json()["values"] == ["Sales Agent", "Support Agent"]
        args, _ = mock_values.call_args
        assert args[2] == "name"

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/filter-values")
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/agent/filter-values", params={"column_name": "name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/generate_prompt — AI prompt generation
# ---------------------------------------------------------------------------

class TestGeneratePrompt:
    """Tests for POST /api/v1/agent/generate_prompt"""

    @patch(f"{_AGENTS_MODULE}._ai_service")
    def test_success(self, mock_ai_service, client_as_member):
        svc = MagicMock()
        svc.generate_system_prompt.return_value = "You are a helpful agent."
        mock_ai_service.return_value = svc

        resp = client_as_member.post(
            "/api/v1/agent/generate_prompt",
            json={
                "agent_name": "Sales",
                "agent_description": "Handles sales",
                "agent_type": "inbound",
                "instruction": "Be friendly",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {"text": "You are a helpful agent."}
        svc.generate_system_prompt.assert_called_once_with(
            agent_name="Sales",
            agent_description="Handles sales",
            agent_type="inbound",
            instruction="Be friendly",
        )

    @patch(f"{_AGENTS_MODULE}._ai_service")
    def test_success_with_empty_body(self, mock_ai_service, client_as_member):
        """All four body fields are optional — missing ones must be coerced to ''."""
        svc = MagicMock()
        svc.generate_system_prompt.return_value = "Generic prompt."
        mock_ai_service.return_value = svc

        resp = client_as_member.post("/api/v1/agent/generate_prompt", json={})
        assert resp.status_code == 200
        svc.generate_system_prompt.assert_called_once_with(
            agent_name="", agent_description="", agent_type="", instruction="",
        )

    def test_no_openai_key_configured(self, client_as_member):
        """When no OpenAI key is configured, ``_ai_service`` raises 400."""
        with patch(
            "core.services.ai_generation_service.resolve_openai_api_key",
            return_value=None,
        ):
            resp = client_as_member.post("/api/v1/agent/generate_prompt", json={})
        assert resp.status_code == 400
        assert "OpenAI" in resp.json()["detail"]

    @patch(f"{_AGENTS_MODULE}._ai_service")
    def test_prompt_truncated_error_returns_400(self, mock_ai_service, client_as_member):
        """``PromptTruncatedError`` from the AI service is translated to 400."""
        from core.services.ai_generation_service import PromptTruncatedError

        svc = MagicMock()
        svc.generate_system_prompt.side_effect = PromptTruncatedError("Output was truncated")
        mock_ai_service.return_value = svc

        resp = client_as_member.post("/api/v1/agent/generate_prompt", json={})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Output was truncated"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/agent/generate_prompt", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/improve_prompt — AI prompt improvement
# ---------------------------------------------------------------------------

class TestImprovePrompt:
    """Tests for POST /api/v1/agent/improve_prompt"""

    @patch(f"{_AGENTS_MODULE}._ai_service")
    def test_success(self, mock_ai_service, client_as_member):
        svc = MagicMock()
        svc.improve_system_prompt.return_value = "Polished version."
        mock_ai_service.return_value = svc

        resp = client_as_member.post(
            "/api/v1/agent/improve_prompt",
            json={
                "text": "Raw draft of the prompt",
                "agent_name": "Sales",
                "agent_description": "Handles sales",
                "agent_type": "inbound",
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {"text": "Polished version."}
        svc.improve_system_prompt.assert_called_once_with(
            text="Raw draft of the prompt",
            agent_name="Sales",
            agent_description="Handles sales",
            agent_type="inbound",
        )

    def test_missing_text(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent/improve_prompt", json={})
        assert resp.status_code == 422

    def test_empty_text(self, client_as_member):
        """``text`` has ``min_length=1`` — empty string must fail validation."""
        resp = client_as_member.post(
            "/api/v1/agent/improve_prompt", json={"text": ""},
        )
        assert resp.status_code == 422

    @patch(f"{_AGENTS_MODULE}._ai_service")
    def test_optional_fields_default_to_empty_string(self, mock_ai_service, client_as_member):
        svc = MagicMock()
        svc.improve_system_prompt.return_value = "ok"
        mock_ai_service.return_value = svc

        resp = client_as_member.post(
            "/api/v1/agent/improve_prompt", json={"text": "Draft"},
        )
        assert resp.status_code == 200
        svc.improve_system_prompt.assert_called_once_with(
            text="Draft", agent_name="", agent_description="", agent_type="",
        )

    @patch(f"{_AGENTS_MODULE}._ai_service")
    def test_prompt_truncated_error_returns_400(self, mock_ai_service, client_as_member):
        from core.services.ai_generation_service import PromptTruncatedError

        svc = MagicMock()
        svc.improve_system_prompt.side_effect = PromptTruncatedError("Truncated")
        mock_ai_service.return_value = svc

        resp = client_as_member.post(
            "/api/v1/agent/improve_prompt", json={"text": "Draft"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Truncated"

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent/improve_prompt", json={"text": "Draft"},
        )
        assert resp.status_code in (401, 403)
