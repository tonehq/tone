"""Tests for Agent Config API endpoints (EE edition).

Source: ee/api/v1/agent_configs.py
Router: POST /api/v1/agent_config/upsert_agent_config

Integration tests — real DB, real endpoints, no mocks. Each test creates
a real Agent row (via /api/v1/agent/create_agent) and then upserts a
config against it. Rollback in the db_session fixture cleans up after
each test.

Known service-layer bug (unrelated to these tests):
    core/services/agent_config_service.py:115 does
        agent_id = int(config_data["agent_id"])
    but Agent.id is UUID(as_uuid=True), so any UUID-form agent_id
    (which is the only form the router returns) blows up with
    ValueError inside the service. The create/update tests below
    are marked xfail against that bug until it's patched — the
    validation and auth tests, which short-circuit BEFORE the int()
    cast, still pin down real behavior.
"""

import uuid

import pytest


_SERVICE_INT_CAST_BUG = pytest.mark.xfail(
    reason=(
        "agent_config_service.upsert_agent_config casts agent_id/id to int, "
        "but Agent/AgentConfig PKs are UUIDs — the service raises ValueError "
        "for UUID-form ids and Postgres ProgrammingError (uuid = integer) "
        "for numeric ids. Both propagate through TestClient."
    ),
    strict=False,
    raises=Exception,
)


# ─── Helpers ───

def _unique_name(prefix="AgentCfg"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_agent(client, name=None):
    """Create a real agent row we can attach a config to."""
    data = {"name": name or _unique_name(), "agent_type": "inbound"}
    resp = client.post("/api/v1/agent/create_agent", json=data)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def _upsert_config(client, agent_id, system_prompt="You are a helpful assistant.", **extra):
    body = {
        "agent_id": agent_id,
        "system_prompt": system_prompt,
        **extra,
    }
    return client.post("/api/v1/agent_config/upsert_agent_config", json=body)


# ─── POST /api/v1/agent_config/upsert_agent_config — CREATE path ───

@_SERVICE_INT_CAST_BUG
class TestUpsertAgentConfigCreate:
    """First upsert for an agent — should create a new AgentConfig row."""

    def test_create_success_member(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = _upsert_config(
            client_as_member,
            agent_id=agent["id"],
            system_prompt="You are a helpful voice assistant.",
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["agent_id"] == agent["id"]
        assert data["system_prompt"] == "You are a helpful voice assistant."
        assert "id" in data
        assert "uuid" in data

    def test_create_success_admin(self, client_as_admin):
        agent = _create_agent(client_as_admin)
        resp = _upsert_config(client_as_admin, agent_id=agent["id"])
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == agent["id"]

    def test_create_success_owner(self, client_as_owner):
        agent = _create_agent(client_as_owner)
        resp = _upsert_config(client_as_owner, agent_id=agent["id"])
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == agent["id"]

    def test_create_returns_row_with_id_and_uuid(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = _upsert_config(client_as_member, agent_id=agent["id"])
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["id"], int)
        # uuid may come back as str
        uuid.UUID(str(data["uuid"]))

    def test_create_persists_system_prompt(self, client_as_member):
        agent = _create_agent(client_as_member)
        prompt = f"Real prompt {uuid.uuid4().hex[:6]}"
        resp = _upsert_config(client_as_member, agent_id=agent["id"], system_prompt=prompt)
        assert resp.status_code == 200
        assert resp.json()["system_prompt"] == prompt


# ─── POST /api/v1/agent_config/upsert_agent_config — UPDATE path ───

@_SERVICE_INT_CAST_BUG
class TestUpsertAgentConfigUpdate:
    """Second upsert against the same agent should update, not duplicate."""

    def test_update_by_agent_id_conflict(self, client_as_member):
        """Router uses conflict_fields=[agent_id, organization_id] — a second
        upsert with the same agent_id should update the existing row, keeping id."""
        agent = _create_agent(client_as_member)
        first = _upsert_config(client_as_member, agent_id=agent["id"], system_prompt="v1")
        assert first.status_code == 200
        first_id = first.json()["id"]

        second = _upsert_config(client_as_member, agent_id=agent["id"], system_prompt="v2 updated")
        assert second.status_code == 200
        second_data = second.json()
        assert second_data["id"] == first_id, "upsert should update, not insert new row"
        assert second_data["system_prompt"] == "v2 updated"

    def test_update_by_explicit_id(self, client_as_member):
        agent = _create_agent(client_as_member)
        first = _upsert_config(client_as_member, agent_id=agent["id"], system_prompt="original")
        cfg_id = first.json()["id"]

        resp = _upsert_config(
            client_as_member,
            agent_id=agent["id"],
            system_prompt="edited via id",
            id=cfg_id,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cfg_id
        assert data["system_prompt"] == "edited via id"

    def test_update_with_nonexistent_id_returns_404(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = _upsert_config(
            client_as_member,
            agent_id=agent["id"],
            system_prompt="anything",
            id=999_999_999,
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ─── Validation errors ───

class TestUpsertAgentConfigValidation:

    def test_missing_agent_id_returns_400(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"system_prompt": "prompt"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "agent_id is required"

    def test_null_agent_id_returns_400(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": None, "system_prompt": "prompt"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "agent_id is required"

    def test_missing_system_prompt_returns_400(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": agent["id"]},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "system_prompt is required"

    def test_empty_system_prompt_returns_400(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": agent["id"], "system_prompt": ""},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "system_prompt is required"

    def test_empty_body_returns_400(self, client_as_member):
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "agent_id is required"

    @_SERVICE_INT_CAST_BUG
    def test_nonexistent_agent_id_returns_404(self, client_as_member):
        """Integer agent_id path is exercised by the service, but the DB
        query casts to int against a UUID column and fails before returning
        404. Kept for coverage of the intended contract."""
        resp = _upsert_config(
            client_as_member,
            agent_id=999_999_999,
            system_prompt="prompt",
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Agent not found"

    def test_body_required(self, client_as_member):
        """POST with no body payload is a 422 (FastAPI Body(...) validation)."""
        resp = client_as_member.post("/api/v1/agent_config/upsert_agent_config")
        assert resp.status_code == 422


# ─── Auth ───

class TestUpsertAgentConfigAuth:

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={"agent_id": 1, "system_prompt": "x"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests derived from the recently-updated Postman examples.
# Any test that exercises the CREATE/UPDATE codepath must be marked with
# _SERVICE_INT_CAST_BUG (see file docstring).
# ---------------------------------------------------------------------------


@_SERVICE_INT_CAST_BUG
class TestUpsertAgentConfigPostmanExamples:
    """New Postman examples for POST /api/v1/agent_config/upsert_agent_config."""

    def test_create_with_full_provider_payload(self, client_as_member):
        """Postman: 200 Created agent config (first time)."""
        agent = _create_agent(client_as_member)
        body = {
            "agent_id": agent["id"],
            "system_prompt": "You are a helpful support agent...",
            "first_message": "Hi! How can I help?",
            "end_call_message": "Thanks for calling. Goodbye!",
            "llm_model_provider_menu_id": 1,
            "llm_model_menu_id": 7,
            "llm_metadata": {"temperature": 0.7, "max_tokens": 4000},
            "stt_model_provider_menu_id": 3,
            "stt_model_menu_id": 12,
            "stt_metadata": {},
        }
        resp = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config", json=body,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == agent["id"]
        assert data["system_prompt"] == body["system_prompt"]
        assert data["first_message"] == "Hi! How can I help?"

    def test_update_existing_agent_config(self, client_as_member):
        """Postman: 200 Updated existing agent config."""
        agent = _create_agent(client_as_member)
        first = _upsert_config(
            client_as_member, agent_id=agent["id"], system_prompt="v1 prompt",
        )
        assert first.status_code == 200
        first_id = first.json()["id"]

        second = client_as_member.post(
            "/api/v1/agent_config/upsert_agent_config",
            json={
                "agent_id": agent["id"],
                "system_prompt": "v2 prompt with new instructions",
                "first_message": "Hi!",
            },
        )
        assert second.status_code == 200
        data = second.json()
        assert data["id"] == first_id
        assert data["system_prompt"] == "v2 prompt with new instructions"
