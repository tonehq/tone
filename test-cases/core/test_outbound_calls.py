"""Service-level tests for outbound / scheduled calls (mocked DB, no live Twilio).

Source: core/services/outbound_call_service.py, core/services/call_log_service.py
"""

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
from core.services.call_log_service import CallLogService
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


class TestCreateValidation:
    def test_no_numbers_400(self):
        svc = OutboundCallService(make_db(), org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(agent_id=uuid4(), from_number="+15551110000", to_numbers=[])
        assert exc.value.status_code == 400

    def test_agent_not_found_404(self):
        svc = OutboundCallService(make_db({Agent: None}), org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(agent_id=uuid4(), from_number="+15551110000", to_numbers=["+15552220000"])
        assert exc.value.status_code == 404

    def test_wrong_agent_type_400(self):
        svc = OutboundCallService(make_db({Agent: _agent(agent_type="inbound")}), org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(agent_id=uuid4(), from_number="+15551110000", to_numbers=["+15552220000"])
        assert exc.value.status_code == 400

    def test_unknown_provider_400(self):
        svc = OutboundCallService(make_db(), org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(
                agent_id=uuid4(), from_number="+15551110000",
                to_numbers=["+15552220000"], provider="carrier-pigeon",
            )
        assert exc.value.status_code == 400

    def test_websocket_provider_unconfigured_400(self, monkeypatch):
        # Fails fast at create time (before agent/creds checks) when the WS target is unset.
        monkeypatch.setattr("core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "")
        monkeypatch.setattr("core.services.outbound_call_service.settings.WS_CALL_TARGET_AGENT_ID", "")
        svc = OutboundCallService(make_db(), org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(
                agent_id=uuid4(), from_number="+15551110000",
                to_numbers=["+15552220000"], provider="websocket",
            )
        assert exc.value.status_code == 400

    def test_websocket_needs_no_twilio_config(self, monkeypatch):
        # The websocket bridge places no PSTN call, so it must NOT require a Twilio from-number /
        # channel / credentials — only the agent + the WS target. The DB has no PhoneNumber or
        # Channel, yet the call still queues its bridge row(s) for hand-off to the outbound voice
        # pods. Regression for the telephony-free trigger.
        monkeypatch.setattr(
            "core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "wss://remote.example"
        )
        enq = MagicMock(side_effect=lambda items: [(7, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        svc = OutboundCallService(make_db({Agent: _agent()}), org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number=None,
            to_numbers=["+15552220000"], provider="websocket",
        )

        assert res["mode"] == "parallel_websocket" and res["status"] == "queued"
        assert res["queued"] == 1


@patch("core.services.outbound_call_service.OutboundCallService._prewarm_pipeline", lambda *a, **k: None)
@patch("core.services.outbound_call_service.get_provider_credentials",
       return_value={"account_sid": "AC", "auth_token": "tok"})
class TestCreateSuccess:
    def _db(self):
        ch = SimpleNamespace(id=uuid4(), channel_type="twilio")
        pn = SimpleNamespace(id=uuid4(), channel_id=ch.id)
        return make_db({Agent: _agent(), PhoneNumber: pn, Channel: ch})

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_single_immediate_dials_now_no_scheduled_row(self, mock_engine, _creds, monkeypatch):
        monkeypatch.setattr("core.services.outbound_call_service.settings.BASE_CALL_URL", "https://api.x")
        eng = mock_engine.return_value
        eng.initiate_call.return_value = SimpleNamespace(call_id="CA1", provider="twilio")
        db = self._db()
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(agent_id=uuid4(), from_number="+15551110000", to_numbers=["+15552220000"])

        assert res["mode"] == "immediate" and res["status"] == "dialing"
        assert res["provider_call_id"] == "CA1"
        eng.initiate_call.assert_called_once()
        # No scheduled_calls row is added for a single immediate call.
        assert not db.add_all.called

    def _db_with_contacts(self, numbers):
        """A mock DB plus fake Contact rows the create+assign+schedule path resolves to.

        Bulk/scheduled create now routes through the shared Schedule → Assign → Create path
        (#10): the numbers become contacts in the default directory (assigned to the agent),
        then ``schedule_calls_for_contacts`` loads them back and builds the scheduled rows."""
        ch = SimpleNamespace(id=uuid4(), channel_type="twilio")
        pn = SimpleNamespace(id=uuid4(), channel_id=ch.id)
        contacts = [
            SimpleNamespace(id=uuid4(), phone_number=n, name=None, contact_metadata={})
            for n in numbers
        ]
        db = make_db(
            {Agent: _agent(), PhoneNumber: pn, Channel: ch, (Contact, "all"): contacts}
        )
        return db, contacts

    def _patch_contact_services(self, mock_dir, mock_contacts, contacts):
        mock_dir.return_value.get_or_create_default_directory.return_value = SimpleNamespace(
            id=uuid4()
        )
        mock_contacts.return_value.create_contacts.return_value = {
            "created": [{"id": str(c.id)} for c in contacts],
            "assigned": len(contacts),
        }

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    @patch("core.services.outbound_call_service.get_call_engine")
    def test_bulk_immediate_queues_one_row_per_number(
        self, mock_engine, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        enq = MagicMock(side_effect=lambda items: [(99, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220001", "+15552220002"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220001", "+15552220002", "+15552220002"],  # dup collapses
        )

        assert res["mode"] == "bulk" and res["count"] == 2
        # Numbers were created + assigned as contacts (single Schedule→Assign→Create path).
        mock_contacts.return_value.create_contacts.assert_called_once()
        rows = db.add_all.call_args.args[0]
        assert len(rows) == 2 and all(isinstance(r, ScheduledCall) for r in rows)
        # One batched defer over a single connection, carrying both rows.
        assert enq.call_count == 1
        assert len(enq.call_args.args[0]) == 2
        mock_engine.return_value.initiate_call.assert_not_called()  # bulk goes to the queue

    def test_websocket_immediate_queues_rows_for_pod_handoff(self, _creds, monkeypatch):
        """provider='websocket' (immediate) no longer runs bridges in-process — it QUEUES
        scheduled_calls rows (due now) so dispatch hands each off to an outbound voice pod."""
        monkeypatch.setattr(
            "core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "wss://remote.example"
        )
        enq = MagicMock(side_effect=lambda items: [(7, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db = self._db()
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220000"], provider="websocket",
        )

        assert res["mode"] == "parallel_websocket" and res["status"] == "queued"
        assert res["queued"] == 1 and res["placed"] == 0
        rows = db.add_all.call_args.args[0]
        assert len(rows) == 1
        assert rows[0].provider == "websocket" and rows[0].batch_id is not None

    def test_websocket_max_concurrency_queues_n_rows(self, _creds, monkeypatch):
        """provider=websocket + max_concurrency=N queues N rows in one batch (one target, cycled).
        Real concurrency is throttled per-pod at dispatch, not by firing N threads here."""
        monkeypatch.setattr(
            "core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "wss://remote.example"
        )
        enq = MagicMock(side_effect=lambda items: [(7, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db = self._db()
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220000"], provider="websocket", max_concurrency=5,
        )

        assert res["requested"] == 5 and res["queued"] == 5
        rows = db.add_all.call_args.args[0]
        assert len(rows) == 5
        assert all(r.max_concurrency == 5 for r in rows)
        assert len({r.batch_id for r in rows}) == 1  # one shared batch

    def test_websocket_no_concurrency_one_row_per_target(self, _creds, monkeypatch):
        """Without max_concurrency, WS queues one row per destination (no dedupe surprise)."""
        monkeypatch.setattr(
            "core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "wss://remote.example"
        )
        enq = MagicMock(side_effect=lambda items: [(7, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db = self._db()
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220000", "+15552220001"], provider="websocket",
        )

        assert res["queued"] == 2
        rows = db.add_all.call_args.args[0]
        assert {r.to_number for r in rows} == {"+15552220000", "+15552220001"}

    def test_websocket_immediate_dispatches_inline_when_pod_available(self, _creds, monkeypatch):
        """Immediate WS dispatches the hand-off INLINE on create (not only via the orchestrator
        poll), so a pod-available call triggers right away instead of sitting in 'scheduled'."""
        monkeypatch.setattr(
            "core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "wss://remote.example"
        )
        enq = MagicMock(side_effect=lambda items: [(7, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db = self._db()
        svc = OutboundCallService(db, org_id=uuid4())

        # Simulate the row dispatching successfully (a pod accepted the hand-off).
        dispatched = SimpleNamespace(
            status="dispatched", to_number="+15552220000", provider_call_sid="WS1"
        )
        with patch.object(svc, "dispatch_scheduled_call", return_value=dispatched) as disp:
            res = svc.create_outbound_call(
                agent_id=uuid4(), from_number="+15551110000",
                to_numbers=["+15552220000"], provider="websocket",
            )

        assert res["mode"] == "parallel_websocket" and res["status"] == "dialing"
        assert res["placed"] == 1 and res["queued"] == 0
        assert res["calls"][0]["provider_call_id"] == "WS1"
        disp.assert_called_once()  # dispatched inline, on create

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    @patch("core.services.outbound_call_service.get_call_engine")
    def test_bulk_stamps_provider_on_scheduled_rows(
        self, mock_engine, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        """Every SCHEDULED row created carries the selected provider (not the DB default).

        A scheduled_at is set so the WS provider routes through the schedule path (immediate
        WS goes to the parallel-bridge path instead, which creates no rows)."""
        from datetime import datetime, timedelta, timezone
        monkeypatch.setattr(
            "core.services.outbound_call_service.settings.WS_CALL_TARGET_URL", "wss://remote.example"
        )
        enq = MagicMock(side_effect=lambda items: [(7, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220001", "+15552220002"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220001", "+15552220002"], provider="websocket",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        assert res["count"] == 2
        rows = db.add_all.call_args.args[0]
        assert all(r.provider == "websocket" for r in rows)

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    @patch("core.services.outbound_call_service.get_call_engine")
    def test_invalid_numbers_reported_valid_proceed(
        self, mock_engine, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        enq = MagicMock(side_effect=lambda items: [(1, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220001", "+15552220003"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())
        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000",
            to_numbers=["+15552220001", "nope", "+15552220003"],
        )
        assert res["count"] == 2
        # The parse-invalid number is surfaced back through the merged response.
        assert any(i["to_number"] == "nope" for i in res["invalid"])

    def test_all_invalid_numbers_400(self, _creds):
        svc = OutboundCallService(self._db(), org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(agent_id=uuid4(), from_number="+15551110000", to_numbers=["nope", "bad"])
        assert exc.value.status_code == 400

    @patch("core.services.contacts.contact_service.ContactService")
    @patch("core.services.contacts.contact_directory_service.ContactDirectoryService")
    @patch("core.services.outbound_call_service.get_call_engine")
    def test_scheduled_inserts_rows_and_enqueues(
        self, mock_engine, mock_dir, mock_contacts, _creds, monkeypatch
    ):
        from datetime import datetime, timedelta, timezone

        enq = MagicMock(side_effect=lambda items: [(4242, None) for _ in items])
        monkeypatch.setattr("core.services.ingestion_queue.enqueue_outbound_calls_batch", enq)
        db, contacts = self._db_with_contacts(["+15552220000"])
        self._patch_contact_services(mock_dir, mock_contacts, contacts)
        svc = OutboundCallService(db, org_id=uuid4())
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        res = svc.create_outbound_call(
            agent_id=uuid4(), from_number="+15551110000", to_numbers=["+15552220000"], scheduled_at=future,
        )

        assert res["mode"] == "scheduled"
        assert db.add_all.called
        enq.assert_called_once()
        mock_engine.return_value.initiate_call.assert_not_called()  # nothing dialed at schedule time

    def test_scheduled_in_past_400(self, _creds):
        from datetime import datetime, timedelta, timezone

        svc = OutboundCallService(self._db(), org_id=uuid4())
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(HTTPException) as exc:
            svc.create_outbound_call(
                agent_id=uuid4(), from_number="+15551110000", to_numbers=["+15552220000"], scheduled_at=past,
            )
        assert exc.value.status_code == 400


class TestScheduledStatusCallback:
    def _sc(self, status="dispatched", sid="CA1"):
        return SimpleNamespace(id=uuid4(), organization_id=uuid4(), status=status,
                               provider_call_sid=sid, metadata_={}, call_id=None)

    def test_advances_to_completed(self):
        sc = self._sc()
        svc = OutboundCallService(make_db({ScheduledCall: sc}), org_id=uuid4())
        svc.handle_status_callback(sc.id, {"CallSid": "CA1", "CallStatus": "completed"})
        assert sc.status == "completed"

    def test_callsid_mismatch_ignored(self):
        sc = self._sc()
        svc = OutboundCallService(make_db({ScheduledCall: sc}), org_id=uuid4())
        out = svc.handle_status_callback(sc.id, {"CallSid": "CAX", "CallStatus": "completed"})
        assert out is None and sc.status == "dispatched"

    def test_duplicate_completed_is_noop(self):
        sc = self._sc(status="completed")
        svc = OutboundCallService(make_db({ScheduledCall: sc}), org_id=uuid4())
        svc.handle_status_callback(sc.id, {"CallSid": "CA1", "CallStatus": "completed"})
        assert sc.status == "completed"


class TestCreateCallLogOutboundInsert:
    def test_outbound_inserts_log_and_links_scheduled(self):
        db = make_db()
        svc = CallLogService(db)
        # avoid touching pod registry / phone resolution internals
        svc._resolve_channel_and_phones = MagicMock(return_value=(uuid4(), None, None))
        with patch("core.services.call_log_service.resolve_pod_id", return_value=None), \
             patch("core.services.outbound_call_service.OutboundCallService.link_call") as link:
            call = svc.create_call_log(
                agent_id=uuid4(),
                organization_id=uuid4(),
                direction="outbound",
                from_number="+15551110000",
                to_number="+15552220000",
                started_at=None,
                scheduled_call_id="sc-1",
            )
        # A new Call row is INSERTed (not an update-in-place).
        assert db.add.called
        added = db.add.call_args.args[0]
        assert added.direction == "outbound"
        link.assert_called_once()  # scheduled call linked to the new log


class TestReconcileOrphans:
    def test_dispatches_due_orphans_inline(self):
        # An orphan: committed 'scheduled' but never got a queue job.
        sc = SimpleNamespace(
            id=uuid4(), organization_id=uuid4(), scheduled_at=None,
            queue_job_id=None, status="scheduled",
        )
        db = make_db({(ScheduledCall, "all"): [sc]})
        svc = OutboundCallService(db, org_id=uuid4())
        with patch.object(svc, "dispatch_scheduled_call") as disp:
            n = svc.reconcile_orphaned_scheduled_calls()
        assert n == 1
        # Recovered by dispatching inline (no Procrastinate re-entry from the worker).
        disp.assert_called_once_with(sc.id)

    def test_no_orphans_is_noop(self):
        svc = OutboundCallService(make_db(), org_id=uuid4())
        with patch.object(svc, "dispatch_scheduled_call") as disp:
            n = svc.reconcile_orphaned_scheduled_calls()
        assert n == 0
        disp.assert_not_called()


def _sc(**over):
    """A ScheduledCall-like row for the dispatch path (only the attributes it touches)."""
    base = dict(
        id=uuid4(), organization_id=uuid4(), agent_id=uuid4(), provider="twilio",
        to_number="+15552220000", from_number="+15551110000", provider_call_sid=None,
        status="scheduled", batch_id=None, max_concurrency=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _dispatch_db(sc, *, claimed, batch_active=0):
    """DB double for ``dispatch_scheduled_call``.

    The batch admission folds a live in-flight COUNT subquery into the claim's WHERE, so the
    ``func.count(...)`` query must return a REAL scalar element (a ``literal``) — a bare
    MagicMock would raise on ``batch_active < batch_limit``. ``claimed`` is what the atomic
    ``UPDATE ... WHERE`` reports (1 = won the claim, 0 = held back by the batch limit)."""
    from sqlalchemy import literal

    db = MagicMock()
    sc_qm = MagicMock()
    sc_qm.filter.return_value = sc_qm
    sc_qm.first.return_value = sc
    sc_qm.update.return_value = claimed

    count_qm = MagicMock()
    count_qm.filter.return_value = count_qm
    count_qm.scalar_subquery.return_value = literal(batch_active)

    db.query.side_effect = lambda model: sc_qm if model is ScheduledCall else count_qm
    return db


class TestDispatchConcurrencyAdmission:
    """The per-batch limiter enforced inside ``dispatch_scheduled_call``: a fresh 'scheduled'
    row is only claimed while its batch has headroom; a row held by the limit stays 'scheduled'
    and is never dialed. (The admission predicate is decided in-DB by the atomic UPDATE; here we
    drive its two observable outcomes via the claim result.)"""

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_batch_at_limit_holds_row_without_dialing(self, mock_engine):
        # Batch limit 2, already 2 in flight → the atomic claim matches nothing (claimed=0).
        sc = _sc(batch_id=uuid4(), max_concurrency=2)
        svc = OutboundCallService(_dispatch_db(sc, claimed=0, batch_active=2), org_id=uuid4())

        res = svc.dispatch_scheduled_call(sc.id)

        # Held back: still 'scheduled', and the dial engine was never touched.
        assert res is sc and res.status == "scheduled"
        mock_engine.assert_not_called()

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_batch_with_headroom_claims_and_dials(self, mock_engine):
        # Batch limit 2, 0 in flight → the claim wins (claimed=1) and the row dials.
        mock_engine.return_value.initiate_call.return_value = SimpleNamespace(call_id="CA9")
        sc = _sc(batch_id=uuid4(), max_concurrency=2)
        db = _dispatch_db(sc, claimed=1, batch_active=0)
        svc = OutboundCallService(db, org_id=uuid4())

        with patch.object(svc, "_public_base", return_value="https://api.x"), \
                patch.object(svc, "_prewarm_pipeline"):
            res = svc.dispatch_scheduled_call(sc.id)

        assert res is sc
        mock_engine.return_value.initiate_call.assert_called_once()
        # The dispatched-mark is a compare-and-set (only advances a row still 'processing'), so a
        # WS bridge that already finalized in its own session isn't clobbered back to an active
        # state. Assert the mark carries status='dispatched' + the returned provider call id.
        mark = db.query(ScheduledCall).update.call_args_list[-1].args[0]
        assert mark[ScheduledCall.status] == "dispatched"
        assert mark[ScheduledCall.provider_call_sid] == "CA9"

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_terminal_row_not_clobbered_back_to_dispatched(self, mock_engine):
        # The WebSocket bridge returns immediately, and its thread's _finalize_scheduled_call can
        # write a terminal status before the dispatched-mark runs. The mark is a compare-and-set
        # (WHERE status='processing'), so it then matches 0 rows and dispatch must NOT overwrite
        # the terminal status (which would strand the row in an active state, holding its batch
        # slot forever). Regression for the dispatch/finalize race.
        mock_engine.return_value.initiate_call.return_value = SimpleNamespace(call_id="WS9")
        sc = _sc(batch_id=uuid4(), max_concurrency=2, provider="websocket")
        db = _dispatch_db(sc, claimed=1, batch_active=0)
        # Claim update wins (1); the later dispatched-mark compare-and-set matches nothing (0)
        # because the bridge already advanced the row to a terminal status in its own session.
        db.query(ScheduledCall).update.side_effect = [1, 0]
        sc.status = "failed"  # what refresh() loads after the bridge finalized the row
        svc = OutboundCallService(db, org_id=uuid4())

        with patch.object(svc, "_public_base", return_value="https://api.x"), \
                patch.object(svc, "_prewarm_pipeline") as prewarm:
            res = svc.dispatch_scheduled_call(sc.id)

        assert res.status == "failed"  # terminal status preserved, not clobbered to 'dispatched'
        prewarm.assert_not_called()  # no point warming a call that already ended

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_ws_no_capacity_holds_row_scheduled(self, mock_engine):
        # When no outbound voice pod is free, the WS engine raises NoOutboundCapacity. Dispatch must
        # HOLD the claimed row (revert 'processing' -> 'scheduled') so the drain retries the hand-off
        # — NOT mark it 'failed'. Backpressure regression for the load-test queue path.
        from core.services.call_engines.websocket_engine import NoOutboundCapacity
        mock_engine.return_value.initiate_call.side_effect = NoOutboundCapacity("no pod free")
        sc = _sc(batch_id=uuid4(), max_concurrency=2, provider="websocket")
        db = _dispatch_db(sc, claimed=1, batch_active=0)
        svc = OutboundCallService(db, org_id=uuid4())

        with patch.object(svc, "_prewarm_pipeline") as prewarm:
            res = svc.dispatch_scheduled_call(sc.id)

        assert res.status == "scheduled"  # held, retryable — not failed
        prewarm.assert_not_called()
        # The hold is a compare-and-set that reverts the claim to 'scheduled'.
        held = db.query(ScheduledCall).update.call_args_list[-1].args[0]
        assert held[ScheduledCall.status] == "scheduled"

    @patch("core.services.outbound_call_service.get_call_engine")
    def test_claim_stamps_updated_at_for_reclaim_age_gate(self, mock_engine):
        # The claim must stamp updated_at so the crashed-'processing' recovery clause can age-gate
        # re-claims (a fresh in-flight hand-off must NOT be re-grabbed, or a second bridge starts —
        # this is the concurrency=1 → 2 calls double-dial). A Core .update() skips the ORM onupdate,
        # so updated_at is set explicitly on the claim.
        mock_engine.return_value.initiate_call.return_value = SimpleNamespace(call_id="CA1")
        sc = _sc(batch_id=uuid4(), max_concurrency=2)
        db = _dispatch_db(sc, claimed=1, batch_active=0)
        svc = OutboundCallService(db, org_id=uuid4())
        with patch.object(svc, "_public_base", return_value="https://api.x"), \
                patch.object(svc, "_prewarm_pipeline"):
            svc.dispatch_scheduled_call(sc.id)
        claim = db.query(ScheduledCall).update.call_args_list[0].args[0]
        assert claim[ScheduledCall.status] == "processing"
        assert ScheduledCall.updated_at in claim  # updated_at stamped on the claim


class TestDrainOutboundCapacity:
    """The per-minute safety net that re-dispatches DUE, batch-limited rows a prior claim held
    back — each re-applies the atomic admission, so it can't overshoot the limit."""

    def test_dispatches_due_rows_and_counts_only_dialed(self):
        held, dialed = _sc(), _sc()
        db = make_db({(ScheduledCall, "all"): [held, dialed]})
        svc = OutboundCallService(db, org_id=uuid4())
        with patch.object(svc, "dispatch_scheduled_call") as disp:
            # First stays held (still 'scheduled'), second wins a freed slot ('dispatched').
            disp.side_effect = [
                SimpleNamespace(status="scheduled"),
                SimpleNamespace(status="dispatched"),
            ]
            n = svc.drain_outbound_capacity()
        assert disp.call_count == 2
        assert n == 1  # only the row that actually dialed is counted

    def test_no_due_rows_is_noop(self):
        svc = OutboundCallService(make_db(), org_id=uuid4())
        with patch.object(svc, "dispatch_scheduled_call") as disp:
            assert svc.drain_outbound_capacity() == 0
        disp.assert_not_called()

    def test_also_recovers_crashed_processing_rows(self):
        # Regression: a dispatch that crashed mid hand-off leaves the row 'processing' with no
        # provider_call_sid, and nothing else re-drives a 'processing' row (drain/reconcile
        # otherwise only touch 'scheduled'), so it would strand forever holding its batch slot.
        # The drain's WHERE must ALSO sweep aged crashed-'processing' rows (age-gated so a live
        # hand-off isn't grabbed), not only rows a limit held back as 'scheduled'.
        from sqlalchemy.dialects import postgresql

        captured = {}
        qm = MagicMock()

        def _filter(expr):
            captured["expr"] = expr
            return qm

        qm.filter.side_effect = _filter
        qm.order_by.return_value = qm
        qm.limit.return_value = qm
        qm.all.return_value = []
        db = MagicMock()
        db.query.return_value = qm

        svc = OutboundCallService(db, org_id=uuid4())
        assert svc.drain_outbound_capacity() == 0

        sql = str(captured["expr"].compile(dialect=postgresql.dialect()))
        assert "provider_call_sid IS NULL" in sql  # the crashed-'processing' recovery branch
        assert "updated_at <" in sql               # age-gated so a live hand-off isn't grabbed
        assert "batch_id IS NOT NULL" in sql       # the held-at-dispatch branch is retained


class TestCompletionRefill:
    """On a terminal status a batch-limited call frees a slot; the refill offloads enqueuing the
    batch's next DUE row to a worker thread. A call with no per-batch limit refills nothing."""

    def test_refill_submits_for_limited_batch(self):
        svc = OutboundCallService(make_db(), org_id=uuid4())
        completed = SimpleNamespace(batch_id=uuid4(), max_concurrency=3)
        with patch("core.services.outbound_call_service._get_refill_executor") as ex:
            svc._refill_after_completion(completed)
        ex.return_value.submit.assert_called_once()
        # Only the batch_id crosses the thread boundary (never the ORM object).
        assert ex.return_value.submit.call_args.args[1] == completed.batch_id

    def test_refill_noop_without_batch_limit(self):
        svc = OutboundCallService(make_db(), org_id=uuid4())
        with patch("core.services.outbound_call_service._get_refill_executor") as ex:
            svc._refill_after_completion(SimpleNamespace(batch_id=None, max_concurrency=None))
            svc._refill_after_completion(SimpleNamespace(batch_id=uuid4(), max_concurrency=0))
        ex.return_value.submit.assert_not_called()


class TestWsTriggerAllowlist:
    """The WebSocket trigger is an internal test tool gated by the ``super_admin`` role (assigned via
    SQL only). See OutboundCallService.is_ws_trigger_allowed / assert_ws_trigger_allowed and the
    capabilities payload. The gate is a pure role check — no DB access needed."""

    def _svc(self):
        return OutboundCallService(make_db(), org_id=uuid4())

    def test_super_admin_allows(self):
        svc = self._svc()
        assert svc.is_ws_trigger_allowed("super_admin") is True
        svc.assert_ws_trigger_allowed("super_admin", "websocket")  # no raise
        # case- / whitespace-insensitive
        assert svc.is_ws_trigger_allowed("  Super_Admin ") is True

    def test_non_super_admin_role_denies_and_403(self):
        svc = self._svc()
        for role in ("admin", "owner", "developer", "observer", "", None):
            assert svc.is_ws_trigger_allowed(role) is False
            with pytest.raises(HTTPException) as exc:
                svc.assert_ws_trigger_allowed(role, "websocket")
            assert exc.value.status_code == 403

    def test_twilio_provider_is_never_gated(self):
        svc = self._svc()
        svc.assert_ws_trigger_allowed("developer", "twilio")  # no raise
        svc.assert_ws_trigger_allowed(None, "twilio")  # no raise

    def test_capabilities_payload_reports_ws_flag(self):
        svc = self._svc()
        assert svc.get_concurrency_max(caller_role="super_admin")["ws_trigger_allowed"] is True
        assert svc.get_concurrency_max(caller_role="developer")["ws_trigger_allowed"] is False
