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


@patch("core.services.outbound_call_service.OutboundCallService._prewarm_pipeline", lambda *a, **k: None)
@patch("core.services.outbound_call_service.get_twilio_credentials",
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
