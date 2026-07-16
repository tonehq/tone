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
