"""Unit tests for the provider-agnostic call terminator.

Source: core/services/call_termination/ (base, twilio, telnyx, default, __init__).
Mirrors the mocking style of test_call_engines.py (patch the client where it is
imported; assert on call args). Terminators/orchestration are async → asyncio.run.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

import core.services.call_termination as ct
from core.services.call_termination import get_call_terminator, terminate_call
from core.services.call_termination import sip as sip_mod
from core.services.call_termination import telnyx as telnyx_mod
from core.services.call_termination import twilio as twilio_mod
from core.services.call_termination.base import CallTerminator
from core.services.call_termination.default import LogOnlyTerminator
from core.services.call_termination.sip import SipTerminator
from core.services.call_termination.plivo import PlivoTerminator
from core.services.call_termination.telnyx import TelnyxTerminator
from core.services.call_termination.twilio import TwilioTerminator


class _FakeTerminator(CallTerminator):
    def __init__(self, result=True, raises=None):
        self._result = result
        self._raises = raises
        self.calls = 0

    @property
    def provider_name(self):
        return "fake"

    async def hangup(self, call_data, org_id):
        self.calls += 1
        if self._raises:
            raise self._raises
        return self._result


# ---- factory --------------------------------------------------------------------

class TestGetCallTerminator:
    def test_known_providers(self):
        assert isinstance(get_call_terminator("twilio"), TwilioTerminator)
        assert isinstance(get_call_terminator("telnyx"), TelnyxTerminator)
        assert isinstance(get_call_terminator("plivo"), PlivoTerminator)
        # SIP trunk calls run on the LiveKit transport.
        assert isinstance(get_call_terminator("livekit"), SipTerminator)
        assert isinstance(get_call_terminator("sip"), SipTerminator)

    @pytest.mark.parametrize("tt", ["exotel", "websocket", "test", "unknown"])
    def test_unknown_falls_back_to_log_only(self, tt):
        term = get_call_terminator(tt)
        assert isinstance(term, LogOnlyTerminator)
        assert term.provider_name == tt


# ---- Twilio terminator ----------------------------------------------------------

class TestTwilioTerminator:
    def test_delegates_to_engine_with_call_sid(self, monkeypatch):
        engine = MagicMock()
        engine.end_call.return_value = True
        monkeypatch.setattr(twilio_mod, "get_call_engine", lambda provider, org_id=None: engine)
        ok = asyncio.run(TwilioTerminator().hangup({"call_id": "CA123"}, "org-1"))
        assert ok is True
        engine.end_call.assert_called_once_with("CA123")

    def test_skips_when_no_call_id(self, monkeypatch):
        engine = MagicMock()
        monkeypatch.setattr(twilio_mod, "get_call_engine", lambda provider, org_id=None: engine)
        ok = asyncio.run(TwilioTerminator().hangup({}, "org-1"))
        assert ok is False
        engine.end_call.assert_not_called()


# ---- Telnyx terminator ----------------------------------------------------------

class TestTelnyxTerminator:
    def test_delegates_to_texml_engine_with_call_id(self, monkeypatch):
        # Telnyx over TeXML: hang up via the TeXML engine using the TeXML CallSid,
        # NOT the Call-Control API (which 422s on a TeXML SID).
        engine = MagicMock()
        engine.end_call.return_value = True
        monkeypatch.setattr(telnyx_mod, "get_call_engine", lambda provider, org_id=None: engine)
        ok = asyncio.run(TelnyxTerminator().hangup({"call_id": "v3:abc"}, "org-1"))
        assert ok is True
        engine.end_call.assert_called_once_with("v3:abc")

    def test_skips_when_no_call_id(self, monkeypatch):
        engine = MagicMock()
        monkeypatch.setattr(telnyx_mod, "get_call_engine", lambda provider, org_id=None: engine)
        ok = asyncio.run(TelnyxTerminator().hangup({}, "org-1"))
        assert ok is False
        engine.end_call.assert_not_called()


# ---- SIP terminator -------------------------------------------------------------

class TestSipTerminator:
    def test_deletes_livekit_room_by_call_id(self, monkeypatch):
        # SIP hangs up by deleting the LiveKit room (call_data["call_id"] == room),
        # which disconnects the caller regardless of participant identity.
        engine = MagicMock()
        engine.end_room.return_value = True
        monkeypatch.setattr(sip_mod, "get_call_engine", lambda provider, org_id=None: engine)
        ok = asyncio.run(SipTerminator().hangup({"call_id": "sip-out-abc123"}, "org-1"))
        assert ok is True
        engine.end_room.assert_called_once_with("sip-out-abc123")

    def test_skips_when_no_room(self, monkeypatch):
        engine = MagicMock()
        monkeypatch.setattr(sip_mod, "get_call_engine", lambda provider, org_id=None: engine)
        ok = asyncio.run(SipTerminator().hangup({}, "org-1"))
        assert ok is False
        engine.end_room.assert_not_called()


# ---- terminate_call orchestration ----------------------------------------------

class TestTerminateCall:
    def test_dispatches_and_reports_success(self, monkeypatch):
        fake = _FakeTerminator(result=True)
        monkeypatch.setattr(ct, "get_call_terminator", lambda tt: fake)
        state = {"done": False}
        ok = asyncio.run(terminate_call(
            transport_type="twilio", call_data={"call_id": "CA1"}, org_id="o", state=state,
        ))
        assert ok is True
        assert fake.calls == 1
        assert state["done"] is True

    def test_idempotent_when_already_done(self, monkeypatch):
        fake = _FakeTerminator(result=True)
        monkeypatch.setattr(ct, "get_call_terminator", lambda tt: fake)
        ok = asyncio.run(terminate_call(
            transport_type="twilio", call_data={}, org_id="o", state={"done": True},
        ))
        assert ok is True
        assert fake.calls == 0

    def test_never_raises_when_strategy_throws(self, monkeypatch):
        fake = _FakeTerminator(raises=RuntimeError("boom"))
        monkeypatch.setattr(ct, "get_call_terminator", lambda tt: fake)
        state = {"done": False}
        ok = asyncio.run(terminate_call(
            transport_type="telnyx", call_data={"call_control_id": "cc"}, org_id="o", state=state,
        ))
        assert ok is False
        assert state["done"] is True

    def test_reports_failed_outcome(self, monkeypatch):
        fake = _FakeTerminator(result=False)
        monkeypatch.setattr(ct, "get_call_terminator", lambda tt: fake)
        ok = asyncio.run(terminate_call(
            transport_type="exotel", call_data={}, org_id="o", state={"done": False},
        ))
        assert ok is False
