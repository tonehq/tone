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
from core.services.call_termination import telnyx as telnyx_mod
from core.services.call_termination import twilio as twilio_mod
from core.services.call_termination.base import CallTerminator
from core.services.call_termination.default import LogOnlyTerminator
from core.services.call_termination.telnyx import TelnyxTerminator
from core.services.call_termination.twilio import TwilioTerminator

# ---- fakes for aiohttp (Telnyx) -------------------------------------------------

class _FakeResp:
    def __init__(self, status, json_data=None, text_data=""):
        self.status = status
        self._json = json_data if json_data is not None else {}
        self._text = text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self):
        return self._json

    async def text(self):
        return self._text


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp
        self.posted = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, url, headers=None):
        self.posted.append((url, headers))
        return self._resp


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

    @pytest.mark.parametrize("tt", ["exotel", "plivo", "websocket", "test", "unknown"])
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
    def _patch_key(self, monkeypatch, key="key-123"):
        monkeypatch.setattr(telnyx_mod, "get_telnyx_api_key", lambda org_id=None: key)

    def test_hangup_200_uses_call_control_endpoint(self, monkeypatch):
        self._patch_key(monkeypatch)
        session = _FakeSession(_FakeResp(200))
        monkeypatch.setattr(telnyx_mod.aiohttp, "ClientSession", lambda: session)
        ok = asyncio.run(TelnyxTerminator().hangup({"call_control_id": "cc-1"}, "org-1"))
        assert ok is True
        url, headers = session.posted[0]
        assert url == "https://api.telnyx.com/v2/calls/cc-1/actions/hangup"
        assert headers["Authorization"] == "Bearer key-123"

    def test_already_ended_422_is_success(self, monkeypatch):
        self._patch_key(monkeypatch)
        resp = _FakeResp(422, json_data={"errors": [{"code": "90018"}]})
        monkeypatch.setattr(telnyx_mod.aiohttp, "ClientSession", lambda: _FakeSession(resp))
        ok = asyncio.run(TelnyxTerminator().hangup({"call_control_id": "cc-1"}, "org-1"))
        assert ok is True

    def test_other_error_is_failure(self, monkeypatch):
        self._patch_key(monkeypatch)
        resp = _FakeResp(500, text_data="boom")
        monkeypatch.setattr(telnyx_mod.aiohttp, "ClientSession", lambda: _FakeSession(resp))
        ok = asyncio.run(TelnyxTerminator().hangup({"call_control_id": "cc-1"}, "org-1"))
        assert ok is False

    def test_skips_when_no_call_control_id(self, monkeypatch):
        self._patch_key(monkeypatch)
        called = {"n": 0}
        monkeypatch.setattr(telnyx_mod.aiohttp, "ClientSession", lambda: called.__setitem__("n", 1))
        ok = asyncio.run(TelnyxTerminator().hangup({}, "org-1"))
        assert ok is False
        assert called["n"] == 0

    def test_skips_when_no_api_key(self, monkeypatch):
        self._patch_key(monkeypatch, key="")
        called = {"n": 0}
        monkeypatch.setattr(telnyx_mod.aiohttp, "ClientSession", lambda: called.__setitem__("n", 1))
        ok = asyncio.run(TelnyxTerminator().hangup({"call_control_id": "cc-1"}, "org-1"))
        assert ok is False
        assert called["n"] == 0


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
