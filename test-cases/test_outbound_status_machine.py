"""Unit tests for the scheduled-call status machine + validation helpers.

Source: core/services/outbound_call_service.py — pure logic, no DB.
"""

import pytest

from core.services.outbound_call_service import (
    OutboundCallService as Svc,
    _STATUS_RANK,
    _TERMINAL,
    _TWILIO_STATUS_MAP,
)
from fastapi import HTTPException


class TestE164:
    @pytest.mark.parametrize("value,expected", [
        ("+14155550123", "+14155550123"),
        (" +1 415 555 0123 ", "+14155550123"),
    ])
    def test_valid(self, value, expected):
        assert Svc._normalize_e164(value, "to") == expected

    @pytest.mark.parametrize("bad", ["14155550123", "+0155", "", "+abc", "555", "++1415"])
    def test_invalid_raises_400(self, bad):
        with pytest.raises(HTTPException) as exc:
            Svc._normalize_e164(bad, "to_number")
        assert exc.value.status_code == 400


class TestTwilioStatusMap:
    def test_inflight_collapses_to_dispatched(self):
        for s in ("queued", "initiated", "ringing", "in-progress"):
            assert _TWILIO_STATUS_MAP[s] == "dispatched"

    def test_terminal_outcomes(self):
        assert _TWILIO_STATUS_MAP["completed"] == "completed"
        assert _TWILIO_STATUS_MAP["busy"] == "busy"
        assert _TWILIO_STATUS_MAP["no-answer"] == "no_answer"
        assert _TWILIO_STATUS_MAP["failed"] == "failed"
        assert _TWILIO_STATUS_MAP["canceled"] == "canceled"

    def test_all_terminals_share_top_rank(self):
        assert all(_STATUS_RANK[s] == 3 for s in _TERMINAL)


class _FakeSc:
    def __init__(self, status):
        self.status = status
        self.id = "sc-x"


class TestRankGuard:
    def _svc(self):
        return Svc.__new__(Svc)  # no DB needed for _apply_status

    def test_forward_advances(self):
        svc = self._svc()
        sc = _FakeSc("scheduled")
        assert svc._apply_status(sc, "dispatched") is True
        assert sc.status == "dispatched"

    def test_cannot_regress(self):
        svc = self._svc()
        sc = _FakeSc("dispatched")
        assert svc._apply_status(sc, "processing") is False
        assert sc.status == "dispatched"

    def test_duplicate_is_noop(self):
        # Twilio delivers callbacks at least once; a duplicate must not re-apply.
        svc = self._svc()
        sc = _FakeSc("dispatched")
        assert svc._apply_status(sc, "dispatched") is False
        assert sc.status == "dispatched"

    def test_duplicate_terminal_is_noop(self):
        svc = self._svc()
        sc = _FakeSc("completed")
        assert svc._apply_status(sc, "completed") is False
        assert sc.status == "completed"
