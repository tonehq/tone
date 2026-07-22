"""Unit tests for the outbound call_engines abstraction.

Source: core/services/call_engines/{__init__,base,twilio_engine}.py
Twilio SDK is fully mocked — no live API calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.services.call_engines import CallEngine, TwilioCallEngine, get_call_engine


class TestFactory:
    def test_returns_twilio_engine(self):
        engine = get_call_engine("twilio", org_id="org-1")
        assert isinstance(engine, TwilioCallEngine)
        assert isinstance(engine, CallEngine)
        assert engine.provider_name == "twilio"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            get_call_engine("livekit")


class TestGenerateTwiml:
    def test_wraps_stream_with_escaped_params(self):
        engine = get_call_engine("twilio")
        xml = engine.generate_twiml(
            "wss://pod-1.example/ws",
            {"agent_id": "a1", "direction": "outbound", "from": "+1 & <x>", "to": ""},
        )
        assert xml.startswith("<?xml")
        assert "<Connect>" in xml and "<Stream" in xml
        assert 'name="agent_id" value="a1"' in xml
        assert 'name="direction" value="outbound"' in xml
        assert 'name="to"' not in xml  # empty value skipped
        assert "&amp;" in xml and "&lt;x&gt;" in xml  # escaping works


@patch("core.services.call_engines.twilio_engine.get_twilio_credentials",
       return_value={"account_sid": "AC", "auth_token": "tok"})
@patch("core.services.call_engines.twilio_engine.Client")
class TestInitiateAndEnd:
    def test_immediate_has_no_status_callback(self, MockClient, _creds):
        inst = MockClient.return_value
        inst.calls.create.return_value = MagicMock(sid="CA123", status="queued")

        engine = get_call_engine("twilio", org_id="org-1")
        info = engine.initiate_call("+15550000000", "+15551111111", agent_id="ag-1",
                                    callback_base_url="https://api.example/")

        kwargs = inst.calls.create.call_args.kwargs
        assert kwargs["to"] == "+15550000000"
        assert kwargs["from_"] == "+15551111111"
        assert "agent_id=ag-1" in kwargs["url"] and "direction=outbound" in kwargs["url"]
        assert "scheduled_call_id" not in kwargs["url"]
        assert "status_callback" not in kwargs  # immediate calls set no callback
        assert kwargs["timeout"] == 45
        assert info.call_id == "CA123" and info.provider == "twilio"

    def test_scheduled_sets_status_callback(self, MockClient, _creds):
        inst = MockClient.return_value
        inst.calls.create.return_value = MagicMock(sid="CA9", status="queued")

        engine = get_call_engine("twilio", org_id="org-1")
        engine.initiate_call("+15550000000", "+15551111111", agent_id="ag-1",
                             callback_base_url="https://api.example", scheduled_call_id="sc-1")

        kwargs = inst.calls.create.call_args.kwargs
        assert "scheduled_call_id=sc-1" in kwargs["url"]
        assert kwargs["status_callback"] == "https://api.example/twilio/outbound-status?scheduled_call_id=sc-1"
        assert kwargs["status_callback_event"] == ["initiated", "ringing", "answered", "completed"]

    def test_initiate_requires_public_base(self, MockClient, _creds):
        engine = get_call_engine("twilio", org_id="org-1")
        with pytest.raises(ValueError):
            engine.initiate_call("+15550000000", "+15551111111", agent_id="ag-1", callback_base_url="")

    def test_end_call_updates_completed(self, MockClient, _creds):
        inst = MockClient.return_value
        engine = get_call_engine("twilio", org_id="org-1")
        assert engine.end_call("CA123") is True
        inst.calls.assert_called_with("CA123")
        inst.calls.return_value.update.assert_called_with(status="completed")


@patch("core.services.call_engines.twilio_engine.get_twilio_credentials", return_value={})
def test_missing_credentials_raises(_creds):
    engine = get_call_engine("twilio", org_id="org-1")
    with pytest.raises(ValueError):
        engine.initiate_call("+15550000000", "+15551111111", agent_id="ag-1",
                             callback_base_url="https://api.example")


from contextlib import contextmanager
from types import SimpleNamespace


@contextmanager
def _fake_db_ctx():
    yield MagicMock()


def _patch_outbound_picker(monkeypatch, pod, base):
    """Patch get_db_context + PodPicker.for_outbound so initiate_call resolves a pod without a DB."""
    import core.database.session as sess
    import core.services.pod_picker as pp
    monkeypatch.setattr(sess, "get_db_context", _fake_db_ctx)
    picker = MagicMock()
    picker.pick.return_value = pod
    picker.internal_base_for.return_value = base
    monkeypatch.setattr(pp.PodPicker, "for_outbound", classmethod(lambda cls, db: picker))
    return picker


class TestWebSocketEngine:
    """The websocket trigger engine — now a hand-off to an outbound voice pod (no in-process bridge)."""

    def test_factory_returns_websocket_engine(self):
        from core.services.call_engines import WebSocketCallEngine
        engine = get_call_engine("websocket", org_id="org-1")
        assert isinstance(engine, WebSocketCallEngine)
        assert isinstance(engine, CallEngine)
        assert engine.provider_name == "websocket"

    def test_generate_twiml_not_supported(self):
        engine = get_call_engine("websocket")
        with pytest.raises(NotImplementedError):
            engine.generate_twiml("wss://x/ws", {})

    def test_initiate_hands_off_to_picked_pod(self, monkeypatch):
        # Picks an outbound pod, POSTs its internal ws-bridge-start route, returns the pod's call_id.
        import core.services.call_engines.websocket_engine as we
        pod = SimpleNamespace(name="staging-tone-outbound-call-worker-0")
        _patch_outbound_picker(monkeypatch, pod, "http://pod0.hl.staging.svc:8080")

        resp = MagicMock(status_code=200)
        resp.json.return_value = {"call_id": "WSX"}
        posted = {}
        def fake_post(url, **kw):
            posted["url"] = url
            posted["json"] = kw.get("json")
            return resp
        monkeypatch.setattr(we.httpx, "post", fake_post)

        info = get_call_engine("websocket").initiate_call(
            "+19894742667", "+1", agent_id="ag-1", callback_base_url="", scheduled_call_id="sc-1",
        )
        assert info.provider == "websocket" and info.status == "dialing" and info.call_id == "WSX"
        assert posted["url"] == "http://pod0.hl.staging.svc:8080/internal/ws-bridge/start"
        assert posted["json"]["agent_id"] == "ag-1"
        assert posted["json"]["to_number"] == "+19894742667"
        assert posted["json"]["scheduled_call_id"] == "sc-1"

    def test_initiate_no_pod_raises_no_capacity(self, monkeypatch):
        from core.services.call_engines.websocket_engine import NoOutboundCapacity
        _patch_outbound_picker(monkeypatch, None, None)  # no live pod
        with pytest.raises(NoOutboundCapacity):
            get_call_engine("websocket").initiate_call("+1", "+1", agent_id="ag-1", callback_base_url="")

    def test_initiate_429_raises_no_capacity(self, monkeypatch):
        # A pod is picked but it's already at MAX_CONCURRENT_CALLS (429) -> caller must queue.
        import core.services.call_engines.websocket_engine as we
        from core.services.call_engines.websocket_engine import NoOutboundCapacity
        pod = SimpleNamespace(name="staging-tone-outbound-call-worker-1")
        _patch_outbound_picker(monkeypatch, pod, "http://pod1.hl.staging.svc:8080")
        monkeypatch.setattr(we.httpx, "post", lambda url, **kw: MagicMock(status_code=429))
        with pytest.raises(NoOutboundCapacity):
            get_call_engine("websocket").initiate_call("+1", "+1", agent_id="ag-1", callback_base_url="")

    def test_initiate_transport_error_raises_no_capacity(self, monkeypatch):
        # Picked pod is unreachable (connect/read timeout) — transient, so queue + retry, not fail.
        import core.services.call_engines.websocket_engine as we
        from core.services.call_engines.websocket_engine import NoOutboundCapacity
        pod = SimpleNamespace(name="staging-tone-outbound-call-worker-2")
        _patch_outbound_picker(monkeypatch, pod, "http://pod2.hl.staging.svc:8080")

        def boom(url, **kw):
            raise we.httpx.ConnectError("connection refused")
        monkeypatch.setattr(we.httpx, "post", boom)
        with pytest.raises(NoOutboundCapacity):
            get_call_engine("websocket").initiate_call("+1", "+1", agent_id="ag-1", callback_base_url="")

    def test_initiate_5xx_raises_no_capacity(self, monkeypatch):
        # Pod-side failure (500 from ws-bridge-start) — retryable, so hold the row like a 429.
        import core.services.call_engines.websocket_engine as we
        from core.services.call_engines.websocket_engine import NoOutboundCapacity
        pod = SimpleNamespace(name="staging-tone-outbound-call-worker-3")
        _patch_outbound_picker(monkeypatch, pod, "http://pod3.hl.staging.svc:8080")
        monkeypatch.setattr(we.httpx, "post", lambda url, **kw: MagicMock(status_code=500))
        with pytest.raises(NoOutboundCapacity):
            get_call_engine("websocket").initiate_call("+1", "+1", agent_id="ag-1", callback_base_url="")

    def test_initiate_4xx_is_not_queued(self, monkeypatch):
        # A 4xx (bad token / not a voice pod / bad request) is a genuine config error, not capacity —
        # it must NOT be swallowed as NoOutboundCapacity so the row fails loudly instead of looping.
        import core.services.call_engines.websocket_engine as we
        from core.services.call_engines.websocket_engine import NoOutboundCapacity
        pod = SimpleNamespace(name="staging-tone-outbound-call-worker-4")
        _patch_outbound_picker(monkeypatch, pod, "http://pod4.hl.staging.svc:8080")

        resp = MagicMock(status_code=403)
        resp.raise_for_status.side_effect = we.httpx.HTTPStatusError(
            "forbidden", request=MagicMock(), response=resp
        )
        monkeypatch.setattr(we.httpx, "post", lambda url, **kw: resp)
        # Raises the raw HTTPStatusError (marked failed downstream), NOT NoOutboundCapacity.
        with pytest.raises(we.httpx.HTTPStatusError):
            get_call_engine("websocket").initiate_call("+1", "+1", agent_id="ag-1", callback_base_url="")
        assert not issubclass(we.httpx.HTTPStatusError, NoOutboundCapacity)


class TestWsBridgeRunner:
    """The pod-local runner that ACTUALLY runs the bridge (on the outbound voice pod)."""

    def test_remote_uri_by_to_number(self, monkeypatch):
        import core.services.call_engines.ws_bridge_runner as r
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "wss://remote.example")
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_AGENT_ID", "")
        assert r._remote_uri("+19894742667", "ag-1") == (
            "wss://remote.example/ws/test?phone_number=%2B19894742667&sample_rate=24000"
        )

    def test_remote_uri_falls_back_to_agent_id(self, monkeypatch):
        import core.services.call_engines.ws_bridge_runner as r
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "wss://remote.example")
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_AGENT_ID", "remote-agent")
        assert r._remote_uri("", "ag-1") == (
            "wss://remote.example/ws/test?agent_id=remote-agent&sample_rate=24000"
        )

    def test_remote_uri_unconfigured_raises(self, monkeypatch):
        import core.services.call_engines.ws_bridge_runner as r
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "")
        with pytest.raises(ValueError):
            r._remote_uri("+1", "ag-1")

    def test_start_local_bridge_enforces_cap(self, monkeypatch):
        # At MAX_CONCURRENT_CALLS the pod refuses (AtCapacity) so the originator queues.
        import core.services.call_engines.ws_bridge_runner as r
        monkeypatch.setattr(r.settings, "WS_CALL_TARGET_URL", "wss://remote.example")
        monkeypatch.setattr(r.settings, "MAX_CONCURRENT_CALLS", 1)
        monkeypatch.setattr(r, "_bridge_thread", lambda *a, **k: None)  # don't open a real socket
        r._SESSIONS.clear()
        try:
            cid = r.start_local_bridge(agent_id="ag-1", to_number="+1")
            assert cid and r.active_count() == 1
            with pytest.raises(r.AtCapacity):
                r.start_local_bridge(agent_id="ag-1", to_number="+1")
        finally:
            r._SESSIONS.clear()
