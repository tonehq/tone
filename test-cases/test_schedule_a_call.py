"""Requirements-as-tests for the "Schedule a Call" feature (docs/features/schedule-a-call.md §5).

Source: core/services/outbound_call_service.py — the immediate-vs-scheduled decision the PRD
is about lives entirely in ``OutboundCallService.create_outbound_call`` (:407) and the read
path ``get_scheduled_call`` (:1272). Mocked DB, no live Twilio — same style as
``test-cases/core/test_outbound_calls.py``.

These lock TODAY's behaviour: whichever of FR-4 / FR-5 product picks, the four response
``mode`` values and the schedule-time validation below must keep behaving this way (§5,
"Regression tests locking today's behaviour").

Cases from §5 deliberately NOT implemented here, and why:

* "cross-org scheduled call is not visible" is specified against
  ``GET /api/v1/outbound-call/scheduled/{id}``. This module's fixtures
  (``test-cases/conftest.py``) are mock-only — there is no ``TestClient`` here; the real-DB
  ``TestClient`` fixtures live one level down in ``test-cases/core/conftest.py`` and are not
  visible to a top-level module. The org boundary is therefore asserted where it is actually
  enforced — ``BaseService.query``'s org filter, via ``get_scheduled_call`` — with a
  filter-aware session double. The route adds no scoping of its own
  (``core/api/v1/outbound_calls.py:247`` constructs the service with the caller's org and
  forwards), so this covers the same seam one layer down.
* "multi-number immediate batch … AND the UI reports it as an immediate call" — only the
  backend half (``mode == "bulk"`` for a no-``scheduled_at`` batch) is asserted. The UI half
  is a frontend assertion; there is no Playwright/RTL harness for
  ``NewOutboundCallModal``/``ScheduledCallsPage`` in this repo (``frontend/e2e/`` holds no
  outbound spec), and the PRD forbids inventing scaffolding.
* "Schedule a Call requires a time" and "Outbound Call hides scheduling controls" are
  frontend-only and describe entry points that do not exist yet — the split into
  "Outbound Call" / "Schedule a Call" is FR-1/FR-2, still ``TBD - needs product input``.
  Testing them needs the application code the PRD has not approved.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from core.models.agent import Agent
from core.models.channel import Channel
from core.models.contact import Contact
from core.models.phone_number import PhoneNumber
from core.models.scheduled_call import ScheduledCall
from core.services.outbound_call_service import OutboundCallService


def make_db(by_model=None):
    """MagicMock Session that returns a per-model query whose .first() is configurable."""
    by_model = by_model or {}
    db = MagicMock()

    def _query(model):
        qm = MagicMock()
        qm.filter.return_value = qm
        qm.order_by.return_value = qm
        qm.limit.return_value = qm
        qm.offset.return_value = qm
        qm.first.return_value = by_model.get(model)
        qm.update.return_value = by_model.get((model, "update"), 1)
        qm.all.return_value = by_model.get((model, "all"), [])
        return qm

    db.query.side_effect = _query
    return db


def _agent(agent_type="outbound", active=True):
    return SimpleNamespace(id=uuid4(), name="A", agent_type=agent_type, is_active=active)


def _now():
    return datetime.now(timezone.utc)


@patch("core.services.outbound_call_service.OutboundCallService._prewarm_pipeline", lambda *a, **k: None)
@patch("core.services.outbound_call_service.get_provider_credentials",
       return_value={"account_sid": "AC", "auth_token": "tok"})
class TestImmediateVsScheduled:
    """The two behaviours the ticket says one button conflates: dial now vs queue for later."""

    def _db(self):
        ch = SimpleNamespace(id=uuid4(), channel_type="twilio")
        pn = SimpleNamespace(id=uuid4(), channel_id=ch.id)
        return make_db({Agent: _agent(), PhoneNumber: pn, Channel: ch})

    def _db_with_contacts(self, numbers):
        """A mock DB plus the fake Contact rows the Schedule → Assign → Create path resolves to.

        Bulk/scheduled create routes through ``_schedule_via_contacts``: the numbers become
        contacts in the default directory, then ``schedule_calls_for_contacts`` loads them
        back and builds the ``scheduled_calls`` rows."""
        ch = SimpleNamespace(id=uuid4(), channel_type="twilio")
        pn = SimpleNamespace(id=uuid4(), channel_id=ch.id)
        contacts = [
            SimpleNamespace(id=uuid4(), phone_number=n, name=None, contact_metadata={})
            for n in numbers
        ]
        db = make_db({Agent: _agent(), PhoneNumber: pn, Channel: ch, (Contact, "all"): contacts})
        return db, contacts

    def _patch_contact_services(self, mock_dir, mock_contacts, contacts):
        mock_dir.return_value.get_or_create_default_directory.return_value = SimpleNamespace(id=uuid4())
        mock_contacts.return_value.create_contacts.return_value = {
            "created": [{"id": str(c.id)} for c in contacts],
            "assigned": len(contacts),
        }

    # -- §5: single immediate number dials inline ---------------------------------------

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_single_immediate_dials_inline_and_writes_no_scheduled_row(
        self, mock_engine, _creds, monkeypatch
    ):
        """One valid number + no scheduled_at → mode 'immediate', dialed inline, and NOTHING
        lands in scheduled_calls (so it surfaces in Call History, not the Scheduled list)."""
        monkeypatch.setattr("core.services.outbound_call_service.settings.BASE_CALL_URL", "https://api.x")
        mock_engine.return_value.initiate_call.return_value = SimpleNamespace(
            call_id="CA1", provider="twilio"
        )
        db = self._db()
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000", to_numbers=["+15552220000"],
        )

        assert res["mode"] == "immediate" and res["status"] == "dialing"
        mock_engine.return_value.initiate_call.assert_called_once()
        assert not db.add_all.called  # no scheduled_calls row for an immediate single dial

    # -- §5: future time queues instead of dialing --------------------------------------

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    @patch("core.services.outbound_call_service.get_call_engine")
    def test_future_time_queues_scheduled_row_and_dials_nothing(
        self, mock_engine, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        """scheduled_at an hour out → mode 'scheduled', a 'scheduled' row at exactly that
        instant, and the dial engine is never touched at schedule time."""
        enq = MagicMock(side_effect=lambda items: [(4242, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220000"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())
        future = _now() + timedelta(hours=1)

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220000"], scheduled_at=future,
        )

        assert res["mode"] == "scheduled" and res["count"] == 1
        rows = db.add_all.call_args.args[0]
        assert len(rows) == 1 and isinstance(rows[0], ScheduledCall)
        assert rows[0].status == "scheduled"
        assert rows[0].scheduled_at == future
        enq.assert_called_once()
        mock_engine.return_value.initiate_call.assert_not_called()

    # -- §5: past time is rejected ------------------------------------------------------

    def test_past_time_is_rejected_400(self, _creds):
        """10 minutes in the past is outside the 60s grace window → 400 with the exact copy
        the modal mirrors client-side (NewOutboundCallModal.tsx:602-608)."""
        svc = OutboundCallService(self._db(), org_id=uuid4())
        past = _now() - timedelta(minutes=10)

        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(
                agent_id=uuid4(), from_number="+15551110000",
                to_numbers=["+15552220000"], scheduled_at=past,
            )

        assert exc.value.status_code == 400
        assert exc.value.detail == "scheduled_at must be in the future."

    # -- §5: near-now time is accepted (60s grace) --------------------------------------

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    def test_near_now_time_within_grace_is_accepted_and_dials_asap(
        self, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        """A time the user picked seconds ago (client-clock skew / request latency) must NOT
        be rejected: 30s in the past is inside the 60s grace, so the row is queued at that
        already-elapsed instant, i.e. due now → the worker dials ASAP."""
        enq = MagicMock(side_effect=lambda items: [(11, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220000"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())
        near_now = _now() - timedelta(seconds=30)

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220000"], scheduled_at=near_now,
        )

        assert res["mode"] == "scheduled" and res["count"] == 1
        rows = db.add_all.call_args.args[0]
        assert rows[0].scheduled_at == near_now
        assert rows[0].scheduled_at <= _now()  # already due → dispatched ASAP, not held
        enq.assert_called_once()

    # -- §5 (new): multi-number immediate batch is labelled correctly -------------------

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    @patch("core.services.outbound_call_service.get_call_engine")
    def test_multi_number_immediate_batch_is_mode_bulk_not_scheduled(
        self, mock_engine, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        """Two numbers + no scheduled_at → mode 'bulk', NOT 'scheduled'. ``mode`` is the
        contract the client labels the outcome from (types/outboundCall.ts:23), so the UI can
        call this an immediate call without a new endpoint (FR-5a).

        This is also the behavioural inconsistency the ticket is about, pinned here so any FR-4
        decision has to face it explicitly: the batch dials ASAP (every row is due now) yet it
        IS persisted to scheduled_calls, which is what the "Scheduled Calls" list renders."""
        enq = MagicMock(side_effect=lambda items: [(99, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220001", "+15552220002"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220001", "+15552220002"],
        )

        assert res["mode"] == "bulk" and res["count"] == 2
        rows = db.add_all.call_args.args[0]
        assert len(rows) == 2 and all(isinstance(r, ScheduledCall) for r in rows)
        assert all(r.scheduled_at <= _now() for r in rows)  # due now — an immediate batch
        assert all(r.status == "scheduled" for r in rows)   # …yet listed as a scheduled row
        mock_engine.return_value.initiate_call.assert_not_called()  # bulk goes to the queue


# ---------------------------------------------------------------------- org isolation

def _row_matches(row, expr) -> bool:
    """Evaluate a simple ``Column == value`` SQLAlchemy clause against a fake row.

    Only equality on a mapped column is simulated; anything else (IS NULL, IN, …) is treated
    as non-narrowing, which is enough for the two clauses ``_get_owned`` builds."""
    column = getattr(expr, "left", None)
    bind = getattr(expr, "right", None)
    key = getattr(column, "key", None)
    if key is None or not hasattr(bind, "value"):
        return True
    return getattr(row, key, None) == bind.value


class _FilterAwareQuery:
    """Query double that actually applies ``filter(Column == value)`` — so the org filter
    ``BaseService.query`` adds is exercised rather than mocked away."""

    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *criteria):
        rows = self._rows
        for expr in criteria:
            rows = [r for r in rows if _row_matches(r, expr)]
        return _FilterAwareQuery(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


def _scoped_db(scheduled_calls):
    """Session double whose ScheduledCall query honours equality filters; every other model
    resolves to nothing (get_scheduled_call's agent/contact lookups are incidental here)."""
    db = MagicMock()
    db.query.side_effect = lambda model: (
        _FilterAwareQuery(scheduled_calls) if model is ScheduledCall else _FilterAwareQuery([])
    )
    return db


class TestScheduledCallOrgIsolation:
    """§5: a scheduled call owned by another org must not be readable. Asserted at the seam
    that enforces it — the org filter in ``BaseService.query``, reached via
    ``get_scheduled_call`` (``GET /outbound-call/scheduled/{id}`` is a thin forward)."""

    def _sc(self, org_id):
        return SimpleNamespace(
            id=uuid4(), organization_id=org_id, agent_id=uuid4(), contact_id=None,
            status="scheduled", from_number="+15551110000", to_number="+15552220000",
            scheduled_at=_now() + timedelta(hours=1), provider_call_sid=None,
            call_id=None, error=None, created_at=None,
        )

    def test_cross_org_scheduled_call_is_404(self):
        org_a, org_b = uuid4(), uuid4()
        owned_by_b = self._sc(org_b)
        svc = OutboundCallService(_scoped_db([owned_by_b]), org_id=org_a)

        with pytest.raises(HTTPException) as exc:
            svc.get_scheduled_call(owned_by_b.id)

        assert exc.value.status_code == 404  # not 403 — the row is invisible, not forbidden

    def test_same_org_scheduled_call_is_returned(self):
        """Control for the test above: the same double DOES find an in-org row, so the 404
        comes from the org filter and not from a lookup that can never match."""
        org_a = uuid4()
        owned_by_a = self._sc(org_a)
        svc = OutboundCallService(_scoped_db([owned_by_a]), org_id=org_a)

        res = svc.get_scheduled_call(owned_by_a.id)

        assert res["id"] == str(owned_by_a.id)
        assert res["status"] == "scheduled"
