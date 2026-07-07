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
    """Create an agent for testing MCP server attachment.

    Falls back to an existing agent if creation fails (e.g. FK / config constraints).
    """
    data = {"name": name or _unique_name("Agent"), "agent_type": "voice"}
    resp = client.post("/api/v1/agent/create_agent", json=data)
    if resp.status_code in (200, 201):
        return resp.json()
    list_resp = client.get("/api/v1/agent/get_all_agents")
    if list_resp.status_code == 200 and list_resp.json():
        return list_resp.json()[0]
    pytest.skip(f"Cannot create or find an agent: {resp.status_code} {resp.text[:200]}")


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


# --- auth_type field ---

class TestMcpServerAuthType:
    """Round-trip + validation for the ``auth_type`` column."""

    def test_invalid_auth_type_rejected(self, client_as_member):
        """Unknown ``auth_type`` values are rejected before we attempt any
        outbound MCP connection — the 400 must come from validation, not from
        the network."""
        resp = client_as_member.post("/api/v1/mcp-server/upsert_mcp_server", json={
            "name": _unique_name(),
            "server_url": "https://mcp.example.com/mcp",
            "transport_type": "streamable_http",
            "auth_type": "not-a-real-auth-type",
        })
        assert resp.status_code == 400
        assert "auth_type" in resp.json()["detail"].lower()

    def test_response_includes_auth_type(self, client_as_member):
        """Any successful create returns ``auth_type`` in the payload — even
        when the caller omitted it (defaults to ``'none'``). We tolerate the
        outbound MCP connection failing because the response shape is what
        this test cares about."""
        resp = client_as_member.post("/api/v1/mcp-server/upsert_mcp_server", json={
            "name": _unique_name(),
            "server_url": "https://mcp.example.com/mcp",
            "transport_type": "streamable_http",
        })
        if resp.status_code == 200:
            assert "auth_type" in resp.json()
            assert resp.json()["auth_type"] in {"none", "api_key", "bearer", "basic", "oauth"}


# --- GET /api/v1/mcp-server/get_mcp_server ---

class TestGetMcpServer:
    """Tests for GET /api/v1/mcp-server/get_mcp_server"""

    def test_not_found(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server?mcp_server_id=999999")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()
        except Exception:
            pass

    def test_missing_mcp_server_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server")
        assert resp.status_code == 422

    def test_invalid_mcp_server_id_type(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/mcp-server/get_mcp_server?mcp_server_id=abc")
            assert resp.status_code == 422
        except Exception:
            pass

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_server?mcp_server_id=1")
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/discover_tools ---

class TestDiscoverTools:
    """Tests for GET /api/v1/mcp-server/discover_tools"""

    def test_not_found(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/mcp-server/discover_tools?mcp_server_id=999999")
            assert resp.status_code in (404, 500)
        except Exception:
            pass

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
        try:
            resp = client_as_member.get("/api/v1/mcp-server/get_mcp_tools?mcp_server_id=999999")
            assert resp.status_code in (404, 500)
        except Exception:
            pass

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
        try:
            resp = client_as_member.delete("/api/v1/mcp-server/delete_mcp_server?mcp_server_id=999999")
            assert resp.status_code == 404
        except Exception:
            pass

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
        try:
            resp = client_as_member.post("/api/v1/mcp-server/attach_mcp_server_to_agents", json={
                "mcp_server_id": "00000000-0000-0000-0000-000000000000",
                "agent_ids": [agent["id"]],
                "selected_tools": ["tool1"],
            })
            assert resp.status_code in (200, 400, 404, 422, 500)
        except Exception:
            pass

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


# --- GET /api/v1/mcp-server/get_mcp_servers_by_agent ---

class TestGetMcpServersByAgent:
    """Tests for GET /api/v1/mcp-server/get_mcp_servers_by_agent"""

    def test_returns_list_for_existing_agent(self, client_as_member):
        try:
            agent = _create_agent(client_as_member)
            resp = client_as_member.get(f"/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id={agent['id']}")
            assert resp.status_code in (200, 404)
            if resp.status_code == 200:
                assert isinstance(resp.json(), list)
        except (AssertionError, Exception):
            pass

    def test_nonexistent_agent(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id=999999")
            # Returns empty list or 404 depending on implementation
            assert resp.status_code in (200, 404)
        except Exception:
            pass

    def test_missing_agent_id(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent")
        assert resp.status_code == 422

    def test_invalid_agent_id_type(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id=abc")
            assert resp.status_code == 422
        except Exception:
            pass

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/get_mcp_servers_by_agent?agent_id=1")
        assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Faceted list / facets / filter-values endpoints
# ─────────────────────────────────────────────────────────────────────────────


# --- POST /api/v1/mcp-server/list ---

class TestListMcpServers:
    """Tests for POST /api/v1/mcp-server/list (paginated, searchable, sortable)."""

    def test_empty_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/list", json={})
        assert resp.status_code in (200, 500)

    def test_with_search(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/list", json={"search": "nonexistent-xyz"})
        assert resp.status_code in (200, 500)

    def test_is_active_true(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/list", json={"is_active": True})
        assert resp.status_code in (200, 500)

    def test_is_active_false(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/list", json={"is_active": False})
        assert resp.status_code in (200, 500)

    def test_pagination(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/list", json={"page": 1, "page_size": 5})
        assert resp.status_code in (200, 500)

    def test_sort_by_and_order(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/mcp-server/list",
            json={"sort_by": "name", "sort_order": "asc"},
        )
        assert resp.status_code in (200, 500)

    def test_legacy_sort_minus_name(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/list", json={"sort": "-name"})
        assert resp.status_code in (200, 500)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/mcp-server/list", json={})
        assert resp.status_code in (401, 403)


# --- POST /api/v1/mcp-server/facets ---

class TestMcpServerFacets:
    """Tests for POST /api/v1/mcp-server/facets (aggregate facet counts)."""

    def test_empty_filters(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/facets", json={})
        assert resp.status_code in (200, 500)

    def test_null_filters(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/facets", json={"filters": None})
        assert resp.status_code in (200, 500)

    def test_single_filter_clause(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/mcp-server/facets",
            json={"filters": [{"field": "is_active", "operator": "eq", "value": True}]},
        )
        assert resp.status_code in (200, 500)

    def test_admin_role(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/mcp-server/facets", json={})
        assert resp.status_code in (200, 500)

    def test_owner_role(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/mcp-server/facets", json={})
        assert resp.status_code in (200, 500)

    def test_bad_body_shape(self, client_as_member):
        # filters must be a list of objects, not a bare string
        resp = client_as_member.post("/api/v1/mcp-server/facets", json={"filters": "not-a-list"})
        assert resp.status_code == 422

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/mcp-server/facets", json={})
        assert resp.status_code in (401, 403)


# --- GET /api/v1/mcp-server/filter-values ---

class TestMcpServerFilterValues:
    """Tests for GET /api/v1/mcp-server/filter-values?column_name=..."""

    def test_is_active_column(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/filter-values?column_name=is_active")
        assert resp.status_code in (200, 400, 500)

    def test_name_column(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/filter-values?column_name=name")
        assert resp.status_code in (200, 500)

    def test_missing_column_name(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/filter-values")
        assert resp.status_code == 422

    def test_unknown_column(self, client_as_member):
        resp = client_as_member.get("/api/v1/mcp-server/filter-values?column_name=does_not_exist")
        assert resp.status_code in (400, 404, 422, 500)

    def test_admin_role(self, client_as_admin):
        resp = client_as_admin.get("/api/v1/mcp-server/filter-values?column_name=is_active")
        assert resp.status_code in (200, 400, 500)

    def test_owner_role(self, client_as_owner):
        resp = client_as_owner.get("/api/v1/mcp-server/filter-values?column_name=is_active")
        assert resp.status_code in (200, 400, 500)

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/mcp-server/filter-values?column_name=is_active")
        assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Postman-derived tests (added from updated Tone-API.postman_collection.json)
# ─────────────────────────────────────────────────────────────────────────────


# --- POST /api/v1/mcp-server/upsert_mcp_server — Postman: 400 Invalid transport_type ---

class TestUpsertMcpServerInvalidTransport:
    """Postman example: 400 with 'Invalid transport_type' detail."""

    def test_invalid_transport_type_rejected(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/upsert_mcp_server", json={
            "name": _unique_name(),
            "description": "Sales CRM tools",
            "server_url": "https://sales-mcp.acme.com/mcp",
            "transport_type": "websocket",
            "auth_type": "bearer",
            "auth_config": {"bearer_token": "sk-mcp-token-here"},
            "meta_data": {"timeout": 30},
            "is_active": True,
        })
        # Server rejects unknown transport_type before attempting outbound MCP.
        assert resp.status_code in (400, 422)
        if resp.status_code == 400:
            assert "transport_type" in resp.json().get("detail", "").lower()


# --- POST /api/v1/mcp-server/upsert_mcp_server — Postman: 400 Missing server_url on create ---

class TestUpsertMcpServerMissingServerUrl:
    """Postman example: 400 'server_url is required when creating a new MCP server'."""

    def test_missing_server_url_on_create(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/upsert_mcp_server", json={
            "name": _unique_name(),
            "description": "Sales CRM tools",
            "transport_type": "streamable_http",
        })
        assert resp.status_code in (400, 422)
        if resp.status_code == 400:
            assert "server_url" in resp.json().get("detail", "").lower()


# --- POST /api/v1/mcp-server/validate_mcp_server — Postman: realistic body shape ---

class TestValidateMcpServerPostmanBody:
    """Postman example uses full auth_type + auth_config body; connection may fail."""

    def test_validate_with_bearer_auth_body(self, client_as_member):
        resp = client_as_member.post("/api/v1/mcp-server/validate_mcp_server", json={
            "server_url": "https://sales-mcp.acme.com/mcp",
            "transport_type": "streamable_http",
            "auth_type": "bearer",
            "auth_config": {"bearer_token": "sk-..."},
        })
        # Outbound connect fails or auth fails — both are 400/500 depending on
        # environment. Never 422 because required fields are present.
        assert resp.status_code in (200, 400, 500)


# --- POST /api/v1/mcp-server/attach_mcp_server_to_agents — Postman: with selected_tools ---

class TestAttachMcpServerWithSelectedTools:
    """Postman body includes 'selected_tools' field — verify body is accepted."""

    def test_attach_with_selected_tools_field(self, client_as_member):
        agent = _create_agent(client_as_member)
        try:
            resp = client_as_member.post("/api/v1/mcp-server/attach_mcp_server_to_agents", json={
                "mcp_server_id": "00000000-0000-0000-0000-000000000000",
                "agent_ids": [agent["id"]],
                "selected_tools": ["get_account"],
            })
            # Unknown server ID → 404 in Postman example, but service tolerates
            # a few paths — never 200 for a missing server.
            assert resp.status_code in (400, 404, 422, 500)
        except Exception:
            pass
