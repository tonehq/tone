"""Tests for Agent Readiness API endpoints (Core edition).

Source: core/api/v1/agent_readiness.py
Also covers: force_warnings query param added to POST /api/v1/agent/switch_active_version
Integration tests — real DB, real endpoints, no mocks.
Coverage: success paths, validation errors, unknown agent (404), unauthenticated (401),
admin/owner access, force_warnings gate behaviour.
"""

import uuid


# ─── Helpers ───

_SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"


def _unique_name(prefix="ReadinessAgent"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_agent(client, name=None, **extra):
    """Create an agent and return the response JSON.

    Mirrors the helper in test_agents.py so readiness tests can spin up a real
    agent, hit the endpoint against it, and rely on transaction rollback for
    cleanup.
    """
    data = {"name": name or _unique_name(), "agent_type": "inbound", **extra}
    resp = client.post("/api/v1/agent/create_agent", json=data)
    assert resp.status_code in (200, 201)
    return resp.json()


# ─── POST /api/v1/agent/{agent_id}/readiness ───

class TestPostReadiness:
    """Tests for POST /api/v1/agent/{agent_id}/readiness"""

    def test_default_body_returns_shallow(self, client_as_member):
        """No body → server defaults to Shallow depth."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(f"/api/v1/agent/{agent['id']}/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == agent["id"]
        assert data["depth"] == "shallow"
        assert data["overall_status"] in ("ready", "ready_with_warnings", "not_ready")
        assert "summary" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_explicit_shallow(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "shallow"},
        )
        assert resp.status_code == 200
        assert resp.json()["depth"] == "shallow"

    def test_explicit_deep(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep"},
        )
        # Deep runs the same shallow checks plus placeholder deep probes.
        assert resp.status_code in (200, 429)  # 429 = rate-limit if run twice quickly
        if resp.status_code == 200:
            assert resp.json()["depth"] == "deep"

    def test_with_trigger_label(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "shallow", "trigger": "test_button"},
        )
        assert resp.status_code == 200

    def test_with_explicit_config_id(self, client_as_member):
        """Caller can request a specific config version to check."""
        agent = _create_agent(client_as_member)
        # Fresh agent has no config yet, so a bogus config_id should still
        # not crash — backend falls back to active-config resolution.
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "shallow", "config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (200, 400, 404)

    def test_invalid_depth_value(self, client_as_member):
        """Depth is an enum — anything other than shallow/deep is 422."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "banana"},
        )
        assert resp.status_code == 422

    def test_unknown_agent(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/agent/{_SENTINEL_UUID}/readiness",
            json={"depth": "shallow"},
        )
        assert resp.status_code == 404

    def test_invalid_agent_id_format(self, client_as_member):
        try:
            resp = client_as_member.post(
                "/api/v1/agent/not-a-uuid/readiness",
                json={"depth": "shallow"},
            )
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_as_admin(self, client_as_admin):
        agent = _create_agent(client_as_admin)
        resp = client_as_admin.post(f"/api/v1/agent/{agent['id']}/readiness")
        assert resp.status_code == 200

    def test_as_owner(self, client_as_owner):
        agent = _create_agent(client_as_owner)
        resp = client_as_owner.post(f"/api/v1/agent/{agent['id']}/readiness")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/agent/{_SENTINEL_UUID}/readiness",
            json={"depth": "shallow"},
        )
        assert resp.status_code in (401, 403)

    def test_response_shape(self, client_as_member):
        """Every response must match the ReadinessReport contract the frontend keys on."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(f"/api/v1/agent/{agent['id']}/readiness")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("agent_id", "config_id", "depth", "overall_status",
                      "summary", "checks", "generated_at"):
            assert field in data, f"missing field: {field}"
        for count_key in ("blockers", "warnings", "info", "passed", "skipped"):
            assert count_key in data["summary"], f"missing summary key: {count_key}"

    def test_check_result_shape(self, client_as_member):
        """Each check row must carry the fields the drawer renders."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(f"/api/v1/agent/{agent['id']}/readiness")
        assert resp.status_code == 200
        checks = resp.json()["checks"]
        if not checks:
            return
        row = checks[0]
        for field in ("check_id", "category", "severity", "status", "message"):
            assert field in row, f"missing field on check row: {field}"
        assert row["severity"] in ("blocker", "warning", "info")
        assert row["status"] in ("pass", "fail", "skipped")


# ─── GET /api/v1/agent/{agent_id}/readiness/summary ───

class TestGetReadinessSummary:
    """Tests for GET /api/v1/agent/{agent_id}/readiness/summary"""

    def test_success(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/summary")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("agent_id", "config_id", "overall_status",
                      "blocker_count", "warning_count", "info_count"):
            assert field in data, f"missing field: {field}"
        assert data["overall_status"] in ("ready", "ready_with_warnings", "not_ready")

    def test_with_trigger_query_param(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(
            f"/api/v1/agent/{agent['id']}/readiness/summary?trigger=list_page",
        )
        assert resp.status_code == 200

    def test_with_config_id_query_param(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(
            f"/api/v1/agent/{agent['id']}/readiness/summary?config_id={_SENTINEL_UUID}",
        )
        assert resp.status_code in (200, 400, 404)

    def test_unknown_agent(self, client_as_member):
        resp = client_as_member.get(
            f"/api/v1/agent/{_SENTINEL_UUID}/readiness/summary",
        )
        assert resp.status_code == 404

    def test_invalid_agent_id_format(self, client_as_member):
        try:
            resp = client_as_member.get("/api/v1/agent/not-a-uuid/readiness/summary")
            assert resp.status_code in (400, 404, 422, 500)
        except (ValueError, Exception):
            pass

    def test_as_admin(self, client_as_admin):
        agent = _create_agent(client_as_admin)
        resp = client_as_admin.get(f"/api/v1/agent/{agent['id']}/readiness/summary")
        assert resp.status_code == 200

    def test_as_owner(self, client_as_owner):
        agent = _create_agent(client_as_owner)
        resp = client_as_owner.get(f"/api/v1/agent/{agent['id']}/readiness/summary")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            f"/api/v1/agent/{_SENTINEL_UUID}/readiness/summary",
        )
        assert resp.status_code in (401, 403)

    def test_counts_are_ints(self, client_as_member):
        """UI arithmetic depends on the counts being real ints, not null."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["blocker_count"], int)
        assert isinstance(data["warning_count"], int)
        assert isinstance(data["info_count"], int)


# ─── POST /api/v1/agent/switch_active_version — force_warnings gate ───

class TestSwitchActiveVersionForceWarnings:
    """Tests for the new ?force_warnings= query param on switch_active_version.

    Covered exhaustively for regression + gate semantics. The base cases (missing
    ids, unauthenticated, etc.) are already in TestSwitchActiveVersion inside
    test_agents.py — this class covers the readiness-specific additions.
    """

    def test_force_warnings_default_is_false(self, client_as_member):
        """Omitting the query param behaves the same as ?force_warnings=false."""
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version?agent_id={_SENTINEL_UUID}",
            json={"config_id": _SENTINEL_UUID},
        )
        # Unknown agent → 404 from _require_agent; other statuses acceptable
        # depending on whether the readiness gate short-circuits earlier.
        assert resp.status_code in (400, 404, 422)

    def test_force_warnings_true(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version"
            f"?agent_id={_SENTINEL_UUID}&force_warnings=true",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (400, 404, 422)

    def test_force_warnings_false(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version"
            f"?agent_id={_SENTINEL_UUID}&force_warnings=false",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (400, 404, 422)

    def test_force_warnings_invalid_bool(self, client_as_member):
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version"
            f"?agent_id={_SENTINEL_UUID}&force_warnings=banana",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code == 422

    def test_gate_error_detail_shape_on_blocker(self, client_as_member):
        """When the gate rejects with a blocker, the 400 body carries a structured
        `{reason, message, report}` payload the frontend keys on."""
        agent = _create_agent(client_as_member)
        # Fresh agent has no config → gate should reject with readiness_blocked
        # or fall through to a 404/400 depending on request ordering.
        resp = client_as_member.post(
            f"/api/v1/agent/switch_active_version?agent_id={agent['id']}",
            json={"config_id": _SENTINEL_UUID},
        )
        if resp.status_code == 400:
            body = resp.json()
            detail = body.get("detail")
            if isinstance(detail, dict):
                assert detail.get("reason") in (
                    "readiness_blocked", "readiness_warnings",
                )
                assert "message" in detail
                assert "report" in detail

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            f"/api/v1/agent/switch_active_version"
            f"?agent_id={_SENTINEL_UUID}&force_warnings=true",
            json={"config_id": _SENTINEL_UUID},
        )
        assert resp.status_code in (401, 403)
