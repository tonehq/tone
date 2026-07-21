"""Unit tests for the scheduled-call status machine + validation helpers.

Source: core/services/outbound_call_service.py — pure logic, no DB.
"""

import pytest

from core.services.outbound_call_service import (
    OutboundCallService as Svc,
    _ACTIVE_OUTBOUND_STATES,
    _STATUS_RANK,
    _TERMINAL,
    _TWILIO_STATUS_MAP,
)
from core.services.outbound_capacity import get_env_outbound_ceiling, resolve_batch_concurrency
from shared.config import settings
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
    def test_preanswer_inflight_collapses_to_dispatched(self):
        # Pre-answer states collapse to "dispatched"; only the connected/live state
        # ("in-progress") maps to the distinct "in_progress" status.
        for s in ("queued", "initiated", "ringing"):
            assert _TWILIO_STATUS_MAP[s] == "dispatched"

    def test_in_progress_maps_to_in_progress(self):
        assert _TWILIO_STATUS_MAP["in-progress"] == "in_progress"

    def test_terminal_outcomes(self):
        assert _TWILIO_STATUS_MAP["completed"] == "completed"
        assert _TWILIO_STATUS_MAP["busy"] == "busy"
        assert _TWILIO_STATUS_MAP["no-answer"] == "no_answer"
        assert _TWILIO_STATUS_MAP["failed"] == "failed"
        assert _TWILIO_STATUS_MAP["canceled"] == "canceled"

    def test_all_terminals_share_top_rank(self):
        # Terminals sit above in_progress: scheduled<processing<dispatched<in_progress<terminal.
        assert all(_STATUS_RANK[s] == 4 for s in _TERMINAL)

    def test_rank_ordering(self):
        assert (
            _STATUS_RANK["scheduled"]
            < _STATUS_RANK["processing"]
            < _STATUS_RANK["dispatched"]
            < _STATUS_RANK["in_progress"]
            < _STATUS_RANK["completed"]
        )


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

    def test_in_progress_advances_from_dispatched(self):
        svc = self._svc()
        sc = _FakeSc("dispatched")
        assert svc._apply_status(sc, "in_progress") is True
        assert sc.status == "in_progress"

    def test_terminal_advances_over_in_progress(self):
        svc = self._svc()
        sc = _FakeSc("in_progress")
        assert svc._apply_status(sc, "completed") is True
        assert sc.status == "completed"

    def test_in_progress_cannot_regress_a_terminal(self):
        # A connected call that already completed must not drop back to in_progress
        # if a late "in-progress" callback arrives.
        svc = self._svc()
        sc = _FakeSc("completed")
        assert svc._apply_status(sc, "in_progress") is False
        assert sc.status == "completed"


class TestOutboundConcurrency:
    """Per-batch concurrency: the env value is only the selector ceiling + default; the
    resolver turns a requested value into the effective per-batch limit. The dispatch-time
    admission, drain safety-net and completion refill are covered in
    ``test-cases/core/test_outbound_calls.py`` (TestDispatchConcurrencyAdmission /
    TestDrainOutboundCapacity / TestCompletionRefill)."""

    def test_active_states_are_inflight_and_disjoint_from_terminal(self):
        assert set(_ACTIVE_OUTBOUND_STATES) == {"processing", "dispatched", "in_progress"}
        assert not (set(_ACTIVE_OUTBOUND_STATES) & _TERMINAL)

    def test_env_ceiling_resolver(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", 8)
        assert get_env_outbound_ceiling() == 8
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", 0)
        assert get_env_outbound_ceiling() is None
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", -5)
        assert get_env_outbound_ceiling() is None

    def test_requested_is_clamped_to_ceiling(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", 5)
        assert resolve_batch_concurrency(3) == 3
        assert resolve_batch_concurrency(99) == 5  # clamped down to the env ceiling

    def test_empty_or_zero_defaults_to_env_ceiling(self, monkeypatch):
        # API-without-UI / empty field → the env ceiling is the default.
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", 7)
        assert resolve_batch_concurrency(None) == 7
        assert resolve_batch_concurrency(0) == 7
        assert resolve_batch_concurrency("") == 7

    def test_requested_used_as_is_when_no_env_ceiling(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", 0)
        assert resolve_batch_concurrency(4) == 4

    def test_no_request_and_no_ceiling_means_unlimited(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_CONCURRENT_OUTBOUND_CALLS", 0)
        assert resolve_batch_concurrency(None) is None
        assert resolve_batch_concurrency(0) is None
