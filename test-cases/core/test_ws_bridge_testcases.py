"""Unit tests for the WS-bridge test-case fan-out plumbing (havana side).

Covers the two pure seams that carry a remote TestRun scenario through the bridge:
- ``ws_test_client._http_base`` (ws→http / wss→https derivation).
- ``ws_bridge_runner._remote_uri`` appending run_id + scenario_id.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import core.services.call_engines.ws_bridge_runner as r
import core.services.call_engines.ws_test_client as client
import core.services.call_engines.ws_test_client as _ws_client_mod
import core.services.outbound_call_service as ocs


class TestHttpBaseDerivation:
    def test_ws_becomes_http(self, monkeypatch):
        monkeypatch.setattr(client.settings, "WS_CALL_TARGET_URL", "ws://localhost:8000")
        assert client._http_base() == "http://localhost:8000"

    def test_wss_becomes_https(self, monkeypatch):
        monkeypatch.setattr(client.settings, "WS_CALL_TARGET_URL", "wss://staging-test.trytone.ai/")
        assert client._http_base() == "https://staging-test.trytone.ai"

    def test_empty_is_none(self, monkeypatch):
        monkeypatch.setattr(client.settings, "WS_CALL_TARGET_URL", "")
        assert client._http_base() is None


class TestRemoteUriCarriesScenario:
    def test_plain_uri_no_scenario(self, monkeypatch):
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "ws://remote")
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_AGENT_ID", "")
        uri = r._remote_uri("+13186201704", "ag-1")
        assert uri == "ws://remote/ws/test?phone_number=%2B13186201704&sample_rate=24000"
        assert "run_id" not in uri and "scenario_id" not in uri

    def test_uri_carries_run_and_scenario(self, monkeypatch):
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "ws://remote")
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_AGENT_ID", "")
        uri = r._remote_uri("+13186201704", "ag-1", "RUN-9", "SCEN-7")
        assert "run_id=RUN-9" in uri and "scenario_id=SCEN-7" in uri
        assert uri.startswith("ws://remote/ws/test?phone_number=%2B13186201704&sample_rate=24000")

    def test_partial_ids_are_ignored(self, monkeypatch):
        # Both must be present to be appended (a run without a scenario is meaningless).
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "ws://remote")
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_AGENT_ID", "")
        uri = r._remote_uri("+1", "ag-1", "RUN-9", None)
        assert "run_id" not in uri and "scenario_id" not in uri


class TestTrackedFanout:
    """The test-case fan-out: one row PER scenario, honoring the requested concurrency (not the
    scenario count) as the per-batch limit, each row tagged with run_id + scenario_id."""

    def test_fanout_one_row_per_scenario_respects_concurrency(self, monkeypatch):
        svc = ocs.OutboundCallService(MagicMock(), org_id=uuid4())
        agent = SimpleNamespace(id=uuid4())

        # Remote resolves the number to a run with 5 scenarios.
        monkeypatch.setattr(
            _ws_client_mod,
            "prepare_bridge_run",
            lambda num: {
                "run_id": "RUN-1",
                "scenarios": [{"scenario_id": f"S{i}"} for i in range(5)],
            },
        )
        # No env ceiling → resolve_batch_concurrency(2) == 2 (used as-is).
        monkeypatch.setattr(ocs, "get_env_outbound_ceiling", lambda: None)
        import core.services.outbound_capacity as cap
        monkeypatch.setattr(cap, "get_env_outbound_ceiling", lambda: None)

        captured = {}
        monkeypatch.setattr(svc, "_persist_and_enqueue_rows", lambda rows: captured.update(rows=rows))
        monkeypatch.setattr(svc, "dispatch_scheduled_call", lambda _id: None)

        svc._dial_parallel_ws(agent, "+1000", ["+13186201704"], max_concurrency=2, invalid=[])

        rows = captured["rows"]
        # 5 scenarios → 5 rows (one per case), NOT capped to the requested 2.
        assert len(rows) == 5
        # Per-batch limit is the REQUESTED concurrency (2), not the scenario count (5).
        assert {row.max_concurrency for row in rows} == {2}
        # One shared batch, each row carries its scenario + the run.
        assert len({row.batch_id for row in rows}) == 1
        assert sorted(row.metadata_["ws_scenario_id"] for row in rows) == [
            "S0", "S1", "S2", "S3", "S4",
        ]
        assert {row.metadata_["ws_run_id"] for row in rows} == {"RUN-1"}

    def test_tracked_fanout_not_capped_at_max_parallel(self, monkeypatch):
        # Regression: a tracked run with MORE scenarios than _MAX_PARALLEL_WS must create one row
        # PER scenario (throttled by batch_limit at dispatch), not truncate — else the dropped cases'
        # remote TestRun mappings stay 'pending' forever. Only the untracked load-test path is capped.
        svc = ocs.OutboundCallService(MagicMock(), org_id=uuid4())
        agent = SimpleNamespace(id=uuid4())
        n = svc._MAX_PARALLEL_WS + 5
        monkeypatch.setattr(
            _ws_client_mod,
            "prepare_bridge_run",
            lambda num: {
                "run_id": "RUN-1",
                "scenarios": [{"scenario_id": f"S{i}"} for i in range(n)],
            },
        )
        monkeypatch.setattr(ocs, "get_env_outbound_ceiling", lambda: None)
        import core.services.outbound_capacity as cap
        monkeypatch.setattr(cap, "get_env_outbound_ceiling", lambda: None)
        captured = {}
        monkeypatch.setattr(svc, "_persist_and_enqueue_rows", lambda rows: captured.update(rows=rows))
        monkeypatch.setattr(svc, "dispatch_scheduled_call", lambda _id: None)

        svc._dial_parallel_ws(agent, "+1000", ["+13186201704"], max_concurrency=2, invalid=[])

        rows = captured["rows"]
        assert len(rows) == n  # one row per scenario — NOT truncated to _MAX_PARALLEL_WS
        assert len({row.metadata_["ws_scenario_id"] for row in rows}) == n  # every case present
        assert {row.max_concurrency for row in rows} == {2}  # in-flight throttled per-batch

    def test_untracked_fanout_falls_back_to_count(self, monkeypatch):
        # Number with no remote scenarios → untracked load-test fan-out: N = requested, no metadata.
        svc = ocs.OutboundCallService(MagicMock(), org_id=uuid4())
        agent = SimpleNamespace(id=uuid4())
        monkeypatch.setattr(_ws_client_mod, "prepare_bridge_run", lambda num: None)
        captured = {}
        monkeypatch.setattr(svc, "_persist_and_enqueue_rows", lambda rows: captured.update(rows=rows))
        monkeypatch.setattr(svc, "dispatch_scheduled_call", lambda _id: None)

        svc._dial_parallel_ws(agent, "+1000", ["+19998887777"], max_concurrency=3, invalid=[])

        rows = captured["rows"]
        assert len(rows) == 3  # untracked: N = requested count
        assert all(not row.metadata_ for row in rows)  # no scenario metadata
        assert {row.max_concurrency for row in rows} == {3}  # admit-all (count)


class TestBridgeBodyCarriesCallIdentity:
    """The bridge threads FROM / TO / CALL SID (+ scheduled_call_id) onto the runner body so the
    call log — and therefore Call History — no longer shows "-" for these columns."""

    def test_run_bridge_body_has_from_to_stream_and_scheduled(self, monkeypatch):
        import core.bot as bot_mod

        captured = {}

        async def _fake_run_bot(transport, runner_args):
            captured["body"] = runner_args.body

        monkeypatch.setattr(r, "build_ws_bridge_transport", lambda uri, rate: object())
        monkeypatch.setattr(bot_mod, "run_bot", _fake_run_bot)

        asyncio.run(
            r._run_bridge(
                "call-abc",
                "ws://remote/ws/test?phone_number=%2B13186201704",
                "ag-1",
                scheduled_call_id="sc-9",
                to_number="+13186201704",
                from_number="+1000",
            )
        )

        body = captured["body"]
        assert body["direction"] == "outbound"
        assert body["transport_type"] == "websocket"
        assert body["scheduled_call_id"] == "sc-9"
        call_data = body["call_data"]
        assert call_data["from"] == "+1000"
        assert call_data["to"] == "+13186201704"
        # No real Twilio sid → the bridge's own call_id is the stream id (→ provider_call_id → CALL SID).
        assert call_data["stream_id"] == "call-abc"
