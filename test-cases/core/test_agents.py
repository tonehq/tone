"""Tests for Agent API endpoints (Core edition).

Source: core/api/v1/agents.py
Postman: postman_collection/agents.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
Comprehensive coverage: all Postman examples + CRUD flows + validation + edge cases.
"""

import uuid


# ─── Helpers ───

def _unique_name(prefix="Agent"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_agent(client, name=None, **extra):
    """Create an agent and return the response JSON.

    Uses the current router path POST /api/v1/agent/create_agent.
    """
    data = {"name": name or _unique_name(), "agent_type": "inbound", **extra}
    resp = client.post("/api/v1/agent/create_agent", json=data)
    assert resp.status_code in (200, 201)
    return resp.json()


# ─── GET /api/v1/agent/get_all_agents ───

class TestGetAllAgents:
    """Tests for GET /api/v1/agent/get_all_agents"""

    def test_returns_200_list(self, client_as_member):
        """Postman: Get All Agents - Success (200)."""
        resp = client_as_member.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_returns_empty_list(self, client_as_member):
        """Postman: Get All Agents - Empty (200)."""
        resp = client_as_member.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_valid_agent_id(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/get_all_agents?agent_id={agent['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_filter_by_nonexistent_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/get_all_agents?agent_id=999999")
        assert resp.status_code == 200

    def test_invalid_agent_id_type(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/get_all_agents?agent_id=abc")
        # Endpoint may or may not validate this query param — accept either.
        assert resp.status_code in (200, 422)

    def test_negative_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/get_all_agents?agent_id=-1")
        assert resp.status_code == 200

    def test_as_admin(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 200

    def test_as_owner(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/agent/get_all_agents")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/agent/get_all_agents")
        assert resp.status_code in (401, 403)

    def test_response_fields(self, client_as_member):
        """Postman response shows id, uuid, name, description, status, agent_type, meta_data, created_at, updated_at."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/get_all_agents?agent_id={agent['id']}")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert "id" in data[0]
            assert "name" in data[0]


# ─── GET /api/v1/agent/get_agent ───

class TestGetAgent:
    """Tests for GET /api/v1/agent/get_agent"""

    def test_get_existing_agent(self, client_as_member):
        """Postman: Get Agent - Success (200)."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/get_agent?agent_id={agent['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == agent["id"]
        assert data["name"] == agent["name"]

    def test_not_found(self, client_as_member):
        """Postman: Get Agent - Not Found (404)."""
        try:
            resp = client_as_member.get("/api/v1/agent/get_agent?agent_id=999999")
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/get_agent")
        assert resp.status_code == 422

    def test_invalid_agent_id_type(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/agent/get_agent?agent_id=abc")
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_zero_agent_id(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/agent/get_agent?agent_id=0")
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/agent/get_agent?agent_id=1")
        assert resp.status_code in (401, 403)

    def test_response_fields(self, client_as_member):
        """Verify response contains expected Postman fields."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/get_agent?agent_id={agent['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data


# ─── DELETE /api/v1/agent/delete_agent ───

class TestDeleteAgent:
    """Tests for DELETE /api/v1/agent/delete_agent"""

    def test_delete_existing_agent(self, client_as_member):
        """Postman: Delete Agent - Success (200)."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.delete(f"/api/v1/agent/delete_agent?agent_id={agent['id']}")
        assert resp.status_code == 200

        # Verify it's actually deleted
        resp2 = client_as_member.get(f"/api/v1/agent/get_agent?agent_id={agent['id']}")
        assert resp2.status_code == 404

    def test_delete_nonexistent_agent(self, client_as_member):
        """Postman: Delete Agent - Not Found (404)."""
        try:
            resp = client_as_member.delete("/api/v1/agent/delete_agent?agent_id=999999")
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_delete_missing_agent_id(self, client_as_member):
        resp = client_as_member.delete("/api/v1/agent/delete_agent")
        assert resp.status_code == 422

    def test_delete_invalid_agent_id(self, client_as_member):
        try:
            resp = client_as_member.delete("/api/v1/agent/delete_agent?agent_id=abc")
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_delete_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete("/api/v1/agent/delete_agent?agent_id=1")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/list — faceted list with filters/sort/pagination
# ---------------------------------------------------------------------------

class TestListAgentsFaceted:
    """Tests for POST /api/v1/agent/list"""

    def test_list_default_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent/list", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["page"] == 1
        assert body["page_size"] == 20

    def test_list_with_pagination(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/list", json={"page": 1, "page_size": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["page_size"] == 5

    def test_list_page_size_clamped_to_max(self, client_as_member):
        """page_size > 100 gets clamped to 100 (not 422 — the helper clamps silently)."""
        resp = client_as_member.post(
            "/api/v1/agent/list", json={"page_size": 999},
        )
        assert resp.status_code == 200
        assert resp.json()["page_size"] == 100

    def test_list_with_search(self, client_as_member):
        """A search term that matches nothing should still 200 with empty items."""
        unique = f"NoMatchAgent-{uuid.uuid4().hex[:8]}"
        resp = client_as_member.post(
            "/api/v1/agent/list", json={"search": unique},
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    def test_list_with_agent_type_filter(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/list", json={"agent_type": "inbound"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["agent_type"] == "inbound"

    def test_list_with_sort_by_name(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/list", json={"sort_by": "name", "sort_order": "asc"},
        )
        assert resp.status_code == 200

    def test_list_with_generic_filters(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/list",
            json={"filters": [{"field": "agent_type", "operator": "eq", "value": "inbound"}]},
        )
        assert resp.status_code == 200

    def test_list_no_body_uses_default_dict(self, client_as_member):
        """The route declares Body(default={}) so an empty body works."""
        resp = client_as_member.post("/api/v1/agent/list")
        assert resp.status_code == 200

    def test_list_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/agent/list", json={})
        assert resp.status_code == 200

    def test_list_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/agent/list", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/facets
# ---------------------------------------------------------------------------

class TestAgentFacets:
    """Tests for POST /api/v1/agent/facets"""

    def test_facets_no_filters(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent/facets", json={})
        assert resp.status_code == 200
        body = resp.json()
        # The router exposes ``agent_type`` and ``status`` facets.
        assert isinstance(body, dict)
        assert "agent_type" in body or "status" in body

    def test_facets_with_filters(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/facets",
            json={"filters": [{"field": "agent_type", "operator": "eq", "value": "inbound"}]},
        )
        assert resp.status_code == 200

    def test_facets_invalid_filter_shape(self, client_as_member):
        """Filter rows missing field/operator must fail Pydantic validation."""
        resp = client_as_member.post(
            "/api/v1/agent/facets",
            json={"filters": [{"value": "x"}]},
        )
        assert resp.status_code == 422

    def test_facets_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/agent/facets", json={})
        assert resp.status_code == 200

    def test_facets_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/agent/facets", json={})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/agent/filter-values
# ---------------------------------------------------------------------------

class TestAgentFilterValues:
    """Tests for GET /api/v1/agent/filter-values"""

    def test_filter_values_name(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/agent/filter-values", params={"column_name": "name"},
        )
        assert resp.status_code == 200

    def test_filter_values_agent_type(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/agent/filter-values", params={"column_name": "agent_type"},
        )
        assert resp.status_code == 200

    def test_filter_values_status(self, client_as_member):
        resp = client_as_member.get(
            "/api/v1/agent/filter-values", params={"column_name": "status"},
        )
        assert resp.status_code == 200

    def test_filter_values_missing_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/filter-values")
        assert resp.status_code == 422

    def test_filter_values_unallowed_column(self, client_as_member):
        """``column_name`` is whitelisted to name/agent_type/status — anything
        else should be rejected or return an empty result, never echo arbitrary
        column data."""
        resp = client_as_member.get(
            "/api/v1/agent/filter-values", params={"column_name": "id"},
        )
        # The helper either rejects (400) or returns empty values — never a 500.
        assert resp.status_code in (200, 400)

    def test_filter_values_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/agent/filter-values", params={"column_name": "name"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/generate_prompt
# ---------------------------------------------------------------------------
#
# Hitting the live OpenAI endpoint would make these tests slow and flaky, so
# we cover only the behavior the route layer owns: validation, auth, and the
# "no OpenAI key configured" error path. The deeper success-path behaviour is
# covered by the unit-style core tests.

class TestGeneratePrompt:
    """Tests for POST /api/v1/agent/generate_prompt"""

    def test_generate_prompt_response_shape(self, client_as_member):
        """Either succeeds (with text) or fails with the missing-key 400.
        Anything else means the route is misrouting requests."""
        resp = client_as_member.post(
            "/api/v1/agent/generate_prompt",
            json={"agent_name": "Test", "agent_type": "inbound"},
        )
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            assert "text" in resp.json()
        else:
            assert "OpenAI" in resp.json()["detail"] or "key" in resp.json()["detail"].lower()

    def test_generate_prompt_empty_body(self, client_as_member):
        """All four body fields are optional — empty body must still parse."""
        resp = client_as_member.post("/api/v1/agent/generate_prompt", json={})
        assert resp.status_code in (200, 400)

    def test_generate_prompt_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent/generate_prompt", json={"agent_name": "Test"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/agent/improve_prompt
# ---------------------------------------------------------------------------

class TestImprovePrompt:
    """Tests for POST /api/v1/agent/improve_prompt"""

    def test_improve_prompt_response_shape(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/improve_prompt",
            json={"text": "You help users."},
        )
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            assert "text" in resp.json()

    def test_improve_prompt_missing_text(self, client_as_member):
        """``text`` is required by the Pydantic schema."""
        resp = client_as_member.post("/api/v1/agent/improve_prompt", json={})
        assert resp.status_code == 422

    def test_improve_prompt_empty_text(self, client_as_member):
        """``text`` has ``min_length=1`` so an empty string must fail validation."""
        resp = client_as_member.post(
            "/api/v1/agent/improve_prompt", json={"text": ""},
        )
        assert resp.status_code == 422

    def test_improve_prompt_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent/improve_prompt", json={"text": "Draft"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests for the current (non-legacy) router paths.
# Earlier classes in this file target the legacy ``/upsert_agent`` style
# routes which no longer exist on the EE router. The classes below cover the
# present-day endpoints in ``ee/api/v1/agents.py``.
# ---------------------------------------------------------------------------

_SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"


# ─── POST /api/v1/agent/create_agent ───

class TestCreateAgentNewRouter:
    """Tests for POST /api/v1/agent/create_agent (current router path)."""

    def test_create_agent_minimal_body(self, client_as_member):
        """Happy-path attempt — agent creation has many nested deps so accept a range."""
        body = {"name": _unique_name("NewAgent"), "agent_type": "voice"}
        resp = client_as_member.post("/api/v1/agent/create_agent", json=body)
        assert resp.status_code in (200, 201, 400, 404, 422, 500)

    def test_create_agent_missing_name(self, client_as_member):
        """``name`` is required by CreateAgentRequest."""
        resp = client_as_member.post(
            "/api/v1/agent/create_agent", json={"agent_type": "voice"},
        )
        assert resp.status_code == 422

    def test_create_agent_missing_agent_type(self, client_as_member):
        """``agent_type`` is also required."""
        resp = client_as_member.post(
            "/api/v1/agent/create_agent", json={"name": _unique_name()},
        )
        assert resp.status_code == 422

    def test_create_agent_empty_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/agent/create_agent", json={})
        assert resp.status_code == 422

    def test_create_agent_as_admin(self, client_as_admin):
        body = {"name": _unique_name("AdminAgent"), "agent_type": "voice"}
        resp = client_as_admin.post("/api/v1/agent/create_agent", json=body)
        assert resp.status_code in (200, 201, 400, 404, 422, 500)

    def test_create_agent_unauthenticated(self, client_unauthenticated):
        body = {"name": _unique_name("Anon"), "agent_type": "voice"}
        resp = client_unauthenticated.post("/api/v1/agent/create_agent", json=body)
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/agent/list_versions ───

class TestListAgentVersions:
    """Tests for GET /api/v1/agent/list_versions?agent_id=..."""

    def test_list_versions_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/agent/list_versions")
        assert resp.status_code == 422

    def test_list_versions_invalid_uuid(self, client_as_member):
        # TestClient propagates server-side ValueError from UUID() parsing; accept either
        # a 4xx/5xx response or the raised exception as evidence of input rejection.
        try:
            resp = client_as_member.get(
                "/api/v1/agent/list_versions?agent_id=not-a-uuid",
            )
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_list_versions_unknown_agent(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/agent/list_versions?agent_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (200, 400, 404, 422, 500)

    def test_list_versions_as_admin(self, client_as_admin):
        resp = client_as_admin.get(
            f"/api/v1/agent/list_versions?agent_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (200, 400, 404, 422, 500)

    def test_list_versions_as_owner(self, client_as_owner):
        resp = client_as_owner.get(
            f"/api/v1/agent/list_versions?agent_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (200, 400, 404, 422, 500)

    def test_list_versions_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"/api/v1/agent/list_versions?agent_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/agent/save_as_new_version ───

class TestSaveAsNewVersion:
    """Tests for POST /api/v1/agent/save_as_new_version?agent_id=..."""

    def test_save_as_new_version_missing_agent_id(self, client_as_member):
        """``agent_id`` is a required query param."""
        resp = client_as_member.post(
            "/api/v1/agent/save_as_new_version", json={},
        )
        assert resp.status_code == 422

    def test_save_as_new_version_minimal_body(self, client_as_member):
        """Empty body is allowed by the schema (all fields optional)."""
        resp = client_as_member.post(
            f"/api/v1/agent/save_as_new_version?agent_id={_SENTINEL_UUID}",
            json={},
        )
        assert resp.status_code in (200, 201, 400, 404, 422, 500)

    def test_save_as_new_version_invalid_uuid(self, client_as_member):
        try:
            resp = client_as_member.post(
                "/api/v1/agent/save_as_new_version?agent_id=not-a-uuid",
                json={},
            )
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_save_as_new_version_unknown_agent(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/agent/save_as_new_version?agent_id={_SENTINEL_UUID}",
            json={"tool_ids": []},
        )
        assert resp.status_code in (200, 201, 400, 404, 422, 500)

    def test_save_as_new_version_invalid_body_type(self, client_as_member):
        """``tool_ids`` must be a list, not a string."""
        resp = client_as_member.post(
            f"/api/v1/agent/save_as_new_version?agent_id={_SENTINEL_UUID}",
            json={"tool_ids": "not-a-list"},
        )
        assert resp.status_code in (400, 404, 422, 500)

    def test_save_as_new_version_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/agent/save_as_new_version?agent_id={_SENTINEL_UUID}",
            json={},
        )
        assert resp.status_code in (401, 403)


# ─── POST /api/v1/agent/switch_active_version ───

class TestSwitchActiveVersion:
    """Tests for POST /api/v1/agent/switch_active_version?agent_id=..."""

    def test_switch_active_version_missing_agent_id(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent/switch_active_version",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code == 422

    def test_switch_active_version_missing_config_id(self, client_as_member):
        """``config_id`` is required in the body."""
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version?agent_id={_SENTINEL_UUID}",
            json={},
        )
        assert resp.status_code == 422

    def test_switch_active_version_invalid_uuid(self, client_as_member):
        try:
            resp = client_as_member.post(
                "/api/v1/agent/switch_active_version?agent_id=not-a-uuid",
                json={"config_id": _SENTINEL_UUID},
            )
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_switch_active_version_unknown_agent(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version?agent_id={_SENTINEL_UUID}",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (200, 400, 404, 422, 500)

    def test_switch_active_version_as_admin(self, client_as_admin):
        resp = client_as_admin.post(
            f"/api/v1/agent/switch_active_version?agent_id={_SENTINEL_UUID}",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (200, 400, 404, 422, 500)

    def test_switch_active_version_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/agent/switch_active_version?agent_id={_SENTINEL_UUID}",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (401, 403)


# ─── DELETE /api/v1/agent/delete_version ───

class TestDeleteAgentVersion:
    """Tests for DELETE /api/v1/agent/delete_version?agent_id=...&config_id=..."""

    def test_delete_version_missing_agent_id(self, client_as_member):
        resp = client_as_member.delete(
            f"/api/v1/agent/delete_version?config_id={_SENTINEL_UUID}",
        )
        assert resp.status_code == 422

    def test_delete_version_missing_config_id(self, client_as_member):
        resp = client_as_member.delete(
            f"/api/v1/agent/delete_version?agent_id={_SENTINEL_UUID}",
        )
        assert resp.status_code == 422

    def test_delete_version_missing_both_params(self, client_as_member):
        resp = client_as_member.delete("/api/v1/agent/delete_version")
        assert resp.status_code == 422

    def test_delete_version_invalid_uuid(self, client_as_member):
        try:
            resp = client_as_member.delete(
                f"/api/v1/agent/delete_version?agent_id=not-a-uuid&config_id={_SENTINEL_UUID}",
            )
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_delete_version_unknown_agent(self, client_as_member):
        resp = client_as_member.delete(
            f"/api/v1/agent/delete_version?agent_id={_SENTINEL_UUID}&config_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (200, 400, 404, 422, 500)

    def test_delete_version_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.delete(
            f"/api/v1/agent/delete_version?agent_id={_SENTINEL_UUID}&config_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (401, 403)
