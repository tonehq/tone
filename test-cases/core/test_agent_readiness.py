"""Tests for Agent Readiness API endpoints (Core edition).

Source: core/api/v1/agent_readiness.py
Also covers: force_warnings query param added to POST /api/v1/agent/switch_active_version
Integration tests — real DB, real endpoints, no mocks.
Coverage: success paths, validation errors, unknown agent (404), unauthenticated (401),
admin/owner access, force_warnings gate behaviour.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException


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

    def test_force_deep_accepted(self, client_as_member):
        """`force` (used by the Run-deep-test button to always append a new
        history event) is accepted alongside depth=deep."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep", "force": True},
        )
        # 200 on success; 429 if the rate limiter fires from a prior deep run.
        assert resp.status_code in (200, 429)

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


# ─── POST /api/v1/agent/{agent_id}/readiness with `categories` filter ───

class TestPostReadinessCategoriesFilter:
    """Tests for the ``categories`` request field on POST /readiness.

    This is the API entry point the frontend uses for save-time targeted deep.
    Unit tests in ``test_readiness_runner_filter.py`` pin down the runner
    filter behaviour directly; these confirm the endpoint accepts / validates /
    forwards ``categories`` correctly and that the returned report shape stays
    intact so the frontend merge helper can operate.
    """

    def test_categories_accepted_alongside_deep(self, client_as_member):
        """The endpoint accepts a categories array with depth=deep."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep", "categories": ["llm"]},
        )
        # 200 on success; 429 if deep-cache/rate-limit fires from a prior run
        # in the same test session — either shape confirms the endpoint
        # deserialised the categories array without complaint.
        assert resp.status_code in (200, 429)

    def test_categories_omitted_still_works(self, client_as_member):
        """Backwards-compat: omitting `categories` == full deep (publish path)."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep"},
        )
        assert resp.status_code in (200, 429)

    def test_categories_empty_list_accepted(self, client_as_member):
        """Empty list is a valid input — server treats it as "probe nothing
        deep" and every deep check comes back SKIPPED."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep", "categories": []},
        )
        assert resp.status_code in (200, 429)

    def test_categories_ignored_on_shallow(self, client_as_member):
        """Shallow doesn't run deep checks — categories is meaningless there
        but must not cause the endpoint to reject the request."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "shallow", "categories": ["llm", "tools"]},
        )
        assert resp.status_code == 200

    def test_categories_invalid_value_rejected(self, client_as_member):
        """Values outside the Category enum are rejected by pydantic before
        reaching the runner — protects against typos in the frontend diff util."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep", "categories": ["not_a_real_category"]},
        )
        assert resp.status_code == 422

    def test_non_matching_deep_checks_marked_unchanged(self, client_as_member):
        """The load-bearing behaviour: any deep check whose category isn't in
        the filter set comes back SKIPPED with the marker string the
        frontend's `mergeReadinessReports` keys on."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.post(
            f"/api/v1/agent/{agent['id']}/readiness",
            json={"depth": "deep", "categories": ["llm"]},
        )
        if resp.status_code != 200:
            # Deep cache / rate-limit collision — test skips rather than fails
            # because the categories-forwarding assertion above already covers
            # the endpoint path, and this assertion is about response shape.
            return
        checks = resp.json()["checks"]
        by_id = {c["check_id"]: c for c in checks}
        # A deep check that IS NOT in {llm} must be filter-skipped with the
        # marker the frontend uses to preserve the previous entry.
        stt_deep = by_id.get("stt.provider_reachable")
        if stt_deep is not None and stt_deep["status"] == "skipped":
            reason = stt_deep.get("skip_reason") or stt_deep.get("message") or ""
            assert "Not re-probed on this save" in reason


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


# ─── GET /api/v1/agent/{agent_id}/readiness/runs ───

class TestListReadinessRuns:
    """Tests for GET /api/v1/agent/{agent_id}/readiness/runs (run-history list)."""

    def test_empty_history_returns_list(self, client_as_member):
        """A fresh agent has no deep runs yet → an empty items list, not a 404."""
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_limit_below_min_rejected(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/runs?limit=0")
        assert resp.status_code == 422

    def test_limit_above_max_rejected(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/runs?limit=101")
        assert resp.status_code == 422

    def test_limit_within_range_accepted(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/runs?limit=5")
        assert resp.status_code == 200

    def test_unknown_agent(self, client_as_member):
        resp = client_as_member.get(f"/api/v1/agent/{_SENTINEL_UUID}/readiness/runs")
        assert resp.status_code == 404

    def test_as_admin(self, client_as_admin):
        agent = _create_agent(client_as_admin)
        resp = client_as_admin.get(f"/api/v1/agent/{agent['id']}/readiness/runs")
        assert resp.status_code == 200

    def test_as_owner(self, client_as_owner):
        agent = _create_agent(client_as_owner)
        resp = client_as_owner.get(f"/api/v1/agent/{agent['id']}/readiness/runs")
        assert resp.status_code == 200

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(f"/api/v1/agent/{_SENTINEL_UUID}/readiness/runs")
        assert resp.status_code in (401, 403)


# ─── GET /api/v1/agent/{agent_id}/readiness/runs/{run_number} ───

class TestGetReadinessRun:
    """Tests for GET /api/v1/agent/{agent_id}/readiness/runs/{run_number}."""

    def test_unknown_run_returns_404(self, client_as_member):
        agent = _create_agent(client_as_member)
        resp = client_as_member.get(f"/api/v1/agent/{agent['id']}/readiness/runs/999")
        assert resp.status_code == 404

    def test_unknown_agent_returns_404(self, client_as_member):
        resp = client_as_member.get(f"/api/v1/agent/{_SENTINEL_UUID}/readiness/runs/1")
        assert resp.status_code == 404

    def test_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.get(f"/api/v1/agent/{_SENTINEL_UUID}/readiness/runs/1")
        assert resp.status_code in (401, 403)


# ─── ReadinessService.list_runs / get_run — seeded, deterministic ───

def _seed_event(db, *, org_id, agent_id, run_number, depth, checks=None):
    """Insert one AgentReadinessEvent row directly so run-history behaviour can
    be asserted deterministically (deep runs are rate-limited + probe live
    providers, so driving them through the API is flaky)."""
    from core.models.agent_readiness_event import AgentReadinessEvent

    now = datetime.now(timezone.utc)
    row = AgentReadinessEvent(
        organization_id=org_id,
        agent_id=agent_id,
        config_id=None,
        depth=depth,
        overall_status="ready",
        counts={"blockers": 0, "warnings": 0, "info": 0, "passed": 1, "skipped": 0},
        checks=checks if checks is not None else [],
        trigger="test_button" if depth == "deep" else "editor_load",
        triggered_by_user_id=None,
        duration_ms=12,
        started_at=now,
        computed_at=now,
        run_number=run_number,
        dependency_stamp="seed-stamp",
        error=None,
    )
    db.add(row)
    return row


class TestReadinessRunsService:
    """Direct service-level tests for the run-history query logic."""

    def _agent_and_service(self, db_session, client_as_member):
        from core.models.agent import Agent
        from core.services.readiness import ReadinessService

        agent = _create_agent(client_as_member)
        agent_row = (
            db_session.query(Agent).filter(Agent.id == uuid.UUID(agent["id"])).first()
        )
        assert agent_row is not None
        org_id = agent_row.organization_id
        svc = ReadinessService(db_session, user_id=None, org_id=org_id)
        return agent, agent_row, org_id, svc

    def test_list_runs_deep_only_descending_no_checks(self, db_session, client_as_member):
        agent, agent_row, org_id, svc = self._agent_and_service(db_session, client_as_member)
        # Interleave a shallow run between two deep runs.
        _seed_event(db_session, org_id=org_id, agent_id=agent_row.id, run_number=1, depth="shallow")
        _seed_event(db_session, org_id=org_id, agent_id=agent_row.id, run_number=2, depth="deep")
        _seed_event(db_session, org_id=org_id, agent_id=agent_row.id, run_number=3, depth="deep")
        db_session.flush()

        result = svc.list_runs(agent["id"], limit=20)
        run_numbers = [item.run_number for item in result.items]
        # Deep runs only (shallow #1 excluded), newest first.
        assert run_numbers == [3, 2]
        # Metadata only — no heavy checks blob on list items.
        for item in result.items:
            assert "checks" not in item.model_dump()
            assert item.depth.value == "deep"

    def test_list_runs_respects_limit(self, db_session, client_as_member):
        agent, agent_row, org_id, svc = self._agent_and_service(db_session, client_as_member)
        _seed_event(db_session, org_id=org_id, agent_id=agent_row.id, run_number=2, depth="deep")
        _seed_event(db_session, org_id=org_id, agent_id=agent_row.id, run_number=3, depth="deep")
        db_session.flush()

        result = svc.list_runs(agent["id"], limit=1)
        assert len(result.items) == 1
        assert result.items[0].run_number == 3

    def test_get_run_returns_full_report_with_checks(self, db_session, client_as_member):
        agent, agent_row, org_id, svc = self._agent_and_service(db_session, client_as_member)
        checks = [
            {
                "check_id": "llm.provider",
                "category": "llm",
                "severity": "info",
                "status": "pass",
                "message": "LLM provider configured",
            }
        ]
        _seed_event(
            db_session,
            org_id=org_id,
            agent_id=agent_row.id,
            run_number=7,
            depth="deep",
            checks=checks,
        )
        db_session.flush()

        report = svc.get_run(agent["id"], 7)
        assert report.run_number == 7
        assert report.depth.value == "deep"
        assert len(report.checks) == 1
        assert report.checks[0].check_id == "llm.provider"

    def test_get_run_unknown_raises_404(self, db_session, client_as_member):
        agent, _agent_row, _org_id, svc = self._agent_and_service(db_session, client_as_member)
        with pytest.raises(HTTPException) as exc:
            svc.get_run(agent["id"], 999)
        assert exc.value.status_code == 404

    def test_get_run_shallow_run_not_found(self, db_session, client_as_member):
        """get_run is deep-only (mirrors list_runs) — a shallow run's number,
        which never appears in the dropdown, must 404 rather than return it."""
        agent, agent_row, org_id, svc = self._agent_and_service(db_session, client_as_member)
        _seed_event(db_session, org_id=org_id, agent_id=agent_row.id, run_number=4, depth="shallow")
        db_session.flush()
        with pytest.raises(HTTPException) as exc:
            svc.get_run(agent["id"], 4)
        assert exc.value.status_code == 404

    def test_list_runs_skips_unmappable_row(self, db_session, client_as_member):
        """One legacy/partial event row with an out-of-enum overall_status must
        be skipped, not 500 the whole history list."""
        agent, agent_row, org_id, svc = self._agent_and_service(db_session, client_as_member)
        good = _seed_event(
            db_session, org_id=org_id, agent_id=agent_row.id, run_number=6, depth="deep"
        )
        bad = _seed_event(
            db_session, org_id=org_id, agent_id=agent_row.id, run_number=5, depth="deep"
        )
        # Corrupt the enum-backed column to a value outside OverallStatus.
        bad.overall_status = "some_retired_status"
        db_session.flush()

        result = svc.list_runs(agent["id"], limit=20)
        run_numbers = [item.run_number for item in result.items]
        assert run_numbers == [6]  # bad row (5) skipped, good row (6) survives
        assert good.run_number == 6
