"""Outbound-call service.

Split-table design:
- **Immediate** calls dial right away and surface only as a call *log* when they
  connect (no pre-created ``calls`` row) — so the call-logs table holds logs only.
- **Scheduled** calls live in their own ``scheduled_calls`` table (shown on a separate
  page). When a scheduled call fires and connects it produces a normal call log, which
  is linked back via ``scheduled_calls.call_id``.

Dialing always goes through the provider-agnostic ``call_engines``.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.channel import Channel
from core.models.contact import Contact
from core.models.phone_number import PhoneNumber
from core.models.scheduled_call import ScheduledCall
from core.services.base import BaseService
from core.services.call_engines import get_call_engine
from core.services.transport.telephony_credentials import get_twilio_credentials
from shared.config import settings

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

# scheduled_calls lifecycle ranks — status only moves strictly forward.
# scheduled < processing < dispatched < in_progress < terminal.
_STATUS_RANK = {
    "scheduled": 0,
    "processing": 1,
    "dispatched": 2,
    "in_progress": 3,
    "completed": 4,
    "busy": 4,
    "no_answer": 4,
    "failed": 4,
    "canceled": 4,
}
_TERMINAL = {"completed", "busy", "no_answer", "failed", "canceled"}

# Twilio CallStatus -> scheduled_calls status. Pre-answer in-flight states collapse to
# "dispatched"; Twilio "in-progress" (the call is connected/live) maps to "in_progress"
# so the list can show an "In progress" chip. The connected call's own log carries detail.
_TWILIO_STATUS_MAP = {
    "queued": "dispatched",
    "initiated": "dispatched",
    "ringing": "dispatched",
    "in-progress": "in_progress",
    "completed": "completed",
    "busy": "busy",
    "no-answer": "no_answer",
    "failed": "failed",
    "canceled": "canceled",
}

# Bounded pool for best-effort pipeline pre-warming (see _prewarm_pipeline). Caps the
# number of concurrent warm threads so a burst of dials can't exhaust the DB pool.
_PREWARM_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="prewarm")

# How long a 'scheduled' row may sit with no queue job before reconcile re-enqueues it.
# Longer than the enqueue round-trip so we never race a batch that's mid-creation.
_ORPHAN_GRACE = timedelta(minutes=2)


class OutboundCallService(BaseService):
    def __init__(self, db: Session, user_id=None, org_id=None):
        super().__init__(db, user_id, org_id)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _public_base() -> str:
        """Public base URL Twilio uses to fetch outbound TwiML + post status callbacks.

        Root-mounted telephony webhooks hang off this (e.g. ``{BASE_CALL_URL}/twiml/outbound``).
        Locally set it to your ngrok URL; in prod, the public API host.
        """
        base = (settings.BASE_CALL_URL or "").rstrip("/")
        if not base:
            raise HTTPException(
                status_code=500,
                detail="BASE_CALL_URL is not configured. Set it to a URL Twilio can reach "
                       "(your ngrok URL locally, or the public API host) to place outbound calls.",
            )
        return base

    @staticmethod
    def _prewarm_pipeline(agent_id, org_id) -> None:
        """Warm the agent's pipeline-config Redis cache in the background.

        Called right after a call is dialed (while it's ringing). Resolving the agent
        config — decrypt keys, serialize tools/KB/MCP — is the slow part of the cold
        build on the voice pod; pre-populating ``agent_pipeline_config:{agent_id}`` (shared
        Redis) turns the answer-time load into a cache hit, so the agent greets sooner.
        Best-effort and non-blocking: any failure is logged and ignored.
        """
        def _warm():
            try:
                from core.database.session import get_db_context
                from core.models.agent import Agent as _Agent
                from core.services.pipeline.service_resolver import load_agent_service_config

                with get_db_context() as db:
                    agent = db.query(_Agent).filter(_Agent.id == agent_id).first()
                    if agent is not None:
                        load_agent_service_config(db, agent, transport_type="twilio", org_id=org_id)
                        logger.info("[outbound] prewarmed pipeline config cache agent={}", agent_id)
            except Exception:  # noqa: BLE001
                logger.exception("[outbound] pipeline prewarm failed agent={}", agent_id)

        # Submit to a bounded pool rather than spawning a raw thread per dial — under a
        # burst of scheduled dispatches, one thread (and pooled DB session) per call would
        # otherwise pile up and exhaust the connection pool.
        _PREWARM_EXECUTOR.submit(_warm)

    @staticmethod
    def _normalize_e164(number: str, field: str) -> str:
        normalized = (number or "").strip().replace(" ", "")
        if not _E164_RE.match(normalized):
            raise HTTPException(
                status_code=400,
                detail=f"{field} must be E.164 format (e.g. +14155550123).",
            )
        return normalized

    def _validate_agent_and_from(self, agent_id, from_number: str):
        """Validate the agent + from-number once (shared across a bulk batch).
        Returns (agent, channel_id, from_number)."""
        org_id = self.org_id
        from_number = self._normalize_e164(from_number, "from_number")

        agent = self.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found.")
        if getattr(agent, "agent_type", None) not in ("outbound", "both"):
            raise HTTPException(
                status_code=400,
                detail="Agent is not configured for outbound calls (agent_type must be 'outbound' or 'both').",
            )
        if getattr(agent, "is_active", True) is False:
            raise HTTPException(status_code=400, detail="Agent is inactive.")

        pn = (
            self.db.query(PhoneNumber)
            .filter(PhoneNumber.number == from_number, PhoneNumber.organization_id == org_id)
            .first()
        )
        if not pn:
            raise HTTPException(
                status_code=400,
                detail="from_number is not a phone number owned by this organization.",
            )
        channel = self.db.query(Channel).filter(Channel.id == pn.channel_id).first()
        if not channel or channel.channel_type != "twilio":
            raise HTTPException(status_code=400, detail="from_number must belong to a Twilio channel.")

        if not get_twilio_credentials(org_id=org_id):
            raise HTTPException(
                status_code=400,
                detail="No Twilio credentials configured for this organization.",
            )
        return agent, channel.id, from_number

    # ------------------------------------------------------------------ create

    # Cap per request so a huge CSV can't queue unbounded work in one call.
    MAX_BULK = 500

    def create_outbound_call(
        self,
        agent_id,
        from_number: str,
        to_numbers: List[str],
        scheduled_at: Optional[datetime] = None,
        created_by_user_id=None,
    ) -> Dict[str, Any]:
        """Place one or many outbound calls. A single immediate number dials right away;
        multiple numbers (or a scheduled time) are queued as ``scheduled_calls`` rows that
        the worker dials at ``scheduled_at`` (or now), and they show up on the Scheduled
        Calls page."""
        if not to_numbers:
            raise HTTPException(status_code=400, detail="Provide at least one destination number.")
        if len(to_numbers) > self.MAX_BULK:
            raise HTTPException(
                status_code=400,
                detail=f"Too many numbers in one request (max {self.MAX_BULK}).",
            )

        agent, channel_id, from_number = self._validate_agent_and_from(agent_id, from_number)

        # Per-number validation: collect invalid ones instead of failing the whole batch.
        valid: List[str] = []
        invalid: List[Dict[str, str]] = []
        seen = set()
        for raw in to_numbers:
            try:
                num = self._normalize_e164(raw, "to_number")
            except HTTPException as e:
                invalid.append({"to_number": raw, "error": str(e.detail)})
                continue
            if num in seen:
                continue
            seen.add(num)
            valid.append(num)

        if not valid:
            raise HTTPException(status_code=400, detail="No valid destination numbers were provided.")

        if scheduled_at is not None:
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            # Grace window so a time the user picked seconds ago (client-clock skew /
            # request latency) isn't rejected — the worker dials ASAP for near-now times.
            if scheduled_at <= datetime.now(timezone.utc) - timedelta(seconds=60):
                raise HTTPException(status_code=400, detail="scheduled_at must be in the future.")

        # Single immediate call: dial inline for instant feedback (surfaces in Call History).
        if len(valid) == 1 and scheduled_at is None:
            return self._dial_now(agent, from_number, valid[0], invalid)

        # Bulk and/or scheduled: one queued row per number (dialed at scheduled_at, or now).
        return self._queue_batch(agent, channel_id, from_number, valid, invalid, scheduled_at, created_by_user_id)

    def _dial_now(self, agent, from_number, to_number, invalid) -> Dict[str, Any]:
        # No calls row is created here — the call log is written by the pipeline
        # (create_call_log) when the media stream connects.
        logger.info("[outbound] placing immediate call agent={} from={} to={}", agent.id, from_number, to_number)
        base = self._public_base()
        engine = get_call_engine("twilio", org_id=self.org_id)
        try:
            info = engine.initiate_call(
                to_number=to_number,
                from_number=from_number,
                agent_id=str(agent.id),
                callback_base_url=base,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("[outbound] immediate dial failed agent={} to={}", agent.id, to_number)
            raise HTTPException(status_code=502, detail=f"Failed to place call: {exc}")

        logger.info("[outbound] immediate call placed agent={} to={} sid={}", agent.id, to_number, info.call_id)
        # Warm the pipeline config cache while the phone rings so the voice pod cache-hits
        # on answer (faster first greeting). Best-effort, non-blocking.
        self._prewarm_pipeline(agent.id, self.org_id)
        return {
            "mode": "immediate",
            "status": "dialing",
            "agent_id": str(agent.id),
            "from_number": from_number,
            "to_number": to_number,
            "provider_call_id": info.call_id,
            "invalid": invalid,
        }

    def _queue_batch(self, agent, channel_id, from_number, numbers, invalid, scheduled_at, created_by_user_id) -> Dict[str, Any]:
        when = scheduled_at or datetime.now(timezone.utc)
        rows = [
            ScheduledCall(
                agent_id=agent.id,
                organization_id=self.org_id,
                channel_id=channel_id,
                from_number=from_number,
                to_number=num,
                scheduled_at=when,
                status="scheduled",
                created_by_user_id=created_by_user_id,
                metadata_={},
            )
            for num in numbers
        ]
        self._persist_and_enqueue_rows(rows)
        logger.info(
            "[outbound] queued batch agent={} count={} invalid={} scheduled_at={}",
            agent.id, len(rows), len(invalid), scheduled_at,
        )
        return {
            "mode": "bulk" if len(numbers) > 1 else "scheduled",
            "count": len(rows),
            "invalid": invalid,
            "data": [self._to_response(sc) for sc in rows],
        }

    def _persist_and_enqueue_rows(self, rows: List[ScheduledCall]) -> None:
        """Persist ``scheduled_calls`` rows then defer one Procrastinate job per row at
        that row's own ``scheduled_at`` (so a batch can carry per-contact times). Enqueue
        failures are isolated per row (marked ``failed``) so one bad defer doesn't drop
        the rest of the batch."""
        if not rows:
            return
        self.db.add_all(rows)
        # flush() assigns PKs while the instances' attributes are still live; reading
        # sc.id / sc.scheduled_at here avoids the per-row reload a post-commit access
        # would trigger under expire_on_commit.
        self.db.flush()
        batch = [(sc.id, self.org_id, sc.scheduled_at) for sc in rows]
        self.db.commit()

        from core.services.ingestion_queue import enqueue_outbound_calls_batch

        # Defer the whole batch over one connection while the session is idle.
        results = enqueue_outbound_calls_batch(batch)
        for sc, (job_id, err) in zip(rows, results):
            if err is not None:
                sc.status = "failed"
                sc.error = f"Failed to enqueue: {err[:400]}"
                logger.error("[outbound] enqueue failed id={} err={}", sc.id, err)
            else:
                sc.queue_job_id = job_id
        self.db.commit()

    # --------------------------------------------------- schedule for contacts

    @staticmethod
    def _resolve_contact_when(contact: Contact, request_when: Optional[datetime]) -> datetime:
        """Per-row effective schedule time. A contact's own ``scheduled_at`` metadata wins
        only when it is still in the FUTURE; a stale/past metadata time is ignored so it
        can neither override the (already future-validated) request time nor force an
        immediate dial. Falls back to the request-level time, then to ASAP (now)."""
        now = datetime.now(timezone.utc)
        meta_when: Optional[datetime] = None
        raw = (contact.contact_metadata or {}).get("scheduled_at")
        if raw:
            try:
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                meta_when = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                logger.debug("[outbound] contact {} has unparseable scheduled_at {!r}", contact.id, raw)
        # Contact metadata time wins only when still in the future; otherwise fall back to
        # the (already future-validated) request time, else ASAP.
        if meta_when is not None and meta_when > now:
            return meta_when
        if request_when is not None:
            return request_when
        return now

    def schedule_calls_for_contacts(
        self,
        agent_id,
        from_number: str,
        contact_ids: List,
        scheduled_at: Optional[datetime] = None,
        created_by_user_id=None,
    ) -> Dict[str, Any]:
        """Schedule outbound calls to the given org-owned contacts.

        Reuses ``_validate_agent_and_from`` (gates outbound/both agent + Twilio
        from-number) and the ``scheduled_calls`` pipeline. Each row carries its
        ``contact_id`` and a per-contact effective time (CSV ``scheduled_at`` overrides
        the request time). Contacts with no/invalid phone are collected into ``invalid``
        rather than failing the whole batch."""
        if not contact_ids:
            raise HTTPException(status_code=400, detail="Provide at least one contact.")
        if len(contact_ids) > self.MAX_BULK:
            raise HTTPException(
                status_code=400,
                detail=f"Too many contacts in one request (max {self.MAX_BULK}).",
            )

        agent, channel_id, from_number = self._validate_agent_and_from(agent_id, from_number)

        if scheduled_at is not None and scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at is not None and scheduled_at <= datetime.now(timezone.utc) - timedelta(seconds=60):
            raise HTTPException(status_code=400, detail="scheduled_at must be in the future.")

        # Org-scoped load; a spoofed id from another org simply won't be found.
        contacts = (
            self.query(Contact)
            .filter(Contact.id.in_(contact_ids), Contact.deleted_at.is_(None))
            .all()
        )
        found = {c.id for c in contacts}
        invalid: List[Dict[str, str]] = [
            {"contact_id": str(cid), "error": "Contact not found."}
            for cid in contact_ids if cid not in found
        ]

        rows: List[ScheduledCall] = []
        for contact in contacts:
            try:
                to_number = self._normalize_e164(contact.phone_number or "", "phone_number")
            except HTTPException:
                invalid.append({
                    "contact_id": str(contact.id),
                    "error": "Contact has no valid E.164 phone number.",
                })
                continue
            rows.append(ScheduledCall(
                agent_id=agent.id,
                organization_id=self.org_id,
                channel_id=channel_id,
                contact_id=contact.id,
                from_number=from_number,
                to_number=to_number,
                scheduled_at=self._resolve_contact_when(contact, scheduled_at),
                status="scheduled",
                created_by_user_id=created_by_user_id,
                metadata_={},
            ))

        if not rows:
            raise HTTPException(
                status_code=400,
                detail="No contacts with a valid phone number were provided.",
            )

        self._persist_and_enqueue_rows(rows)
        logger.info(
            "[outbound] scheduled {} call(s) for contacts agent={} invalid={}",
            len(rows), agent.id, len(invalid),
        )
        contact_by_id = {c.id: c for c in contacts}
        return {
            "count": len(rows),
            "invalid": invalid,
            "data": [self._to_response(sc, contact=contact_by_id.get(sc.contact_id)) for sc in rows],
        }

    # ---------------------------------------------------------------- dispatch

    def dispatch_scheduled_call(self, scheduled_call_id) -> Optional[ScheduledCall]:
        """Fired by the Procrastinate worker at ``scheduled_at``. Atomically claims the
        row so a re-delivered job can't double-dial.

        Claims ``scheduled`` rows, and also re-claims a ``processing`` row that has no
        ``provider_call_sid`` — that state means a prior attempt crashed after claiming but
        before it ever dialed, so recovering it here avoids the row being stranded in
        ``processing`` forever. (Relies on Procrastinate not running the same job twice
        concurrently; the narrow window between Twilio accepting the call and us persisting
        the SID is the only residual double-dial risk.)"""
        claimed = (
            self.db.query(ScheduledCall)
            .filter(
                ScheduledCall.id == scheduled_call_id,
                or_(
                    ScheduledCall.status == "scheduled",
                    and_(
                        ScheduledCall.status == "processing",
                        ScheduledCall.provider_call_sid.is_(None),
                    ),
                ),
            )
            .update({ScheduledCall.status: "processing"}, synchronize_session=False)
        )
        self.db.commit()
        sc = self.db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
        if sc is None:
            logger.warning("[outbound] dispatch: scheduled call {} not found", scheduled_call_id)
            return None
        if not claimed:
            logger.info("[outbound] dispatch no-op id={} status={}", scheduled_call_id, sc.status)
            return sc

        base = self._public_base()
        engine = get_call_engine(sc.provider, org_id=sc.organization_id)
        try:
            info = engine.initiate_call(
                to_number=sc.to_number,
                from_number=sc.from_number,
                agent_id=str(sc.agent_id),
                callback_base_url=base,
                scheduled_call_id=str(sc.id),
            )
        except Exception as exc:  # noqa: BLE001
            sc.status = "failed"
            sc.error = str(exc)[:500]
            self.db.commit()
            logger.exception("[outbound] dispatch dial failed id={}", scheduled_call_id)
            return sc

        sc.provider_call_sid = info.call_id
        sc.status = "dispatched"
        self.db.commit()
        self.db.refresh(sc)
        logger.info("[outbound] dispatched id={} sid={}", scheduled_call_id, info.call_id)
        # Warm the pipeline config cache while it rings so the voice pod cache-hits on answer.
        self._prewarm_pipeline(sc.agent_id, sc.organization_id)
        return sc

    def reconcile_orphaned_scheduled_calls(self, limit: int = 50) -> int:
        """Recover 'scheduled' rows that were persisted but never got a Procrastinate job
        (``queue_job_id IS NULL``) — e.g. the API process died between committing the rows
        and deferring their jobs. Without this they would never dial and never reach a
        terminal state, and the list page would poll them as live forever.

        Dispatches any that are now DUE inline (the same sync path the worker runs), rather
        than re-deferring — deferring would mean re-entering the Procrastinate app from
        inside the worker, which shares this process's already-open pool and is unsafe. A
        future-dated orphan is left until it comes due, then picked up by a later run.

        System task: scans across orgs (unscoped query), and ``dispatch_scheduled_call``
        keys off each row's own org/provider. Only touches rows older than ``_ORPHAN_GRACE``
        so a batch that is merely mid-creation isn't disturbed. Idempotent: the dispatch
        claim guards against double-dial, and a dispatched row is no longer 'scheduled'.
        Returns the count dispatched."""
        now = datetime.now(timezone.utc)
        cutoff = now - _ORPHAN_GRACE
        orphans = (
            self.db.query(ScheduledCall)
            .filter(
                ScheduledCall.status == "scheduled",
                ScheduledCall.queue_job_id.is_(None),
                ScheduledCall.created_at <= cutoff,
                ScheduledCall.scheduled_at <= now,
            )
            .order_by(ScheduledCall.scheduled_at.asc())
            .limit(limit)
            .all()
        )
        if not orphans:
            return 0

        dispatched = 0
        for sc in orphans:
            try:
                self.dispatch_scheduled_call(sc.id)
                dispatched += 1
            except Exception:  # noqa: BLE001
                logger.exception("[outbound] reconcile dispatch failed id={}", sc.id)
        logger.warning("[outbound] reconciled {} orphaned scheduled call(s)", dispatched)
        return dispatched

    # ---------------------------------------------------------- status webhook

    def _apply_status(self, sc: ScheduledCall, new_status: str) -> bool:
        current = sc.status or "scheduled"
        if _STATUS_RANK.get(new_status, -1) <= _STATUS_RANK.get(current, 0):
            return False
        logger.info("[outbound] scheduled status id={} {} -> {}", sc.id, current, new_status)
        sc.status = new_status
        return True

    def handle_status_callback(self, scheduled_call_id, form: Dict[str, Any]) -> Optional[ScheduledCall]:
        sc = self.db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
        if not sc:
            logger.warning("[outbound] status callback for unknown scheduled id={}", scheduled_call_id)
            return None

        call_sid = (form.get("CallSid") or "").strip()
        if sc.provider_call_sid and call_sid and call_sid != sc.provider_call_sid:
            logger.warning(
                "[outbound] status callback CallSid mismatch id={} got={} expected={}",
                scheduled_call_id, call_sid, sc.provider_call_sid,
            )
            return None

        twilio_status = (form.get("CallStatus") or "").strip().lower()
        internal = _TWILIO_STATUS_MAP.get(twilio_status)
        if internal is None:
            logger.warning("[outbound] unmapped Twilio CallStatus={!r} scheduled id={}", twilio_status, scheduled_call_id)
            return sc

        prev = sc.status
        if not self._apply_status(sc, internal):
            return sc

        duration = form.get("CallDuration")
        if duration:
            meta = dict(sc.metadata_ or {})
            meta["provider_call_duration"] = duration
            sc.metadata_ = meta
        self.db.commit()
        self.db.refresh(sc)
        logger.info(
            "[outbound] scheduled status callback applied id={} {}->{} (twilio={})",
            scheduled_call_id, prev, sc.status, twilio_status,
        )
        return sc

    def link_call(self, scheduled_call_id, call_id) -> None:
        """Link the connected call log back to its scheduled row. Called from
        create_call_log when a dispatched scheduled call connects."""
        # Org-scoped (self.query) so a spoofed scheduled_call_id threaded through the
        # unauthenticated media path can't link/complete another org's scheduled row.
        sc = self.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
        if sc is None:
            return
        sc.call_id = call_id
        # A connected call is 'in_progress'; the terminal Twilio status callback
        # (completed/busy/no_answer/failed) advances it to its final state.
        self._apply_status(sc, "in_progress")
        self.db.commit()
        logger.info("[outbound] linked scheduled call {} -> call {}", scheduled_call_id, call_id)

    # ------------------------------------------------------------------ cancel

    def cancel_scheduled_call(self, scheduled_call_id) -> ScheduledCall:
        sc = self._get_owned(scheduled_call_id)
        # Only a still-queued ('scheduled') row is cancelable. Once the worker claims it
        # ('processing') it owns the dial, so canceling here would race the outbound call
        # and could leave the row 'canceled' while Twilio still places the call.
        claimed = (
            self.db.query(ScheduledCall)
            .filter(ScheduledCall.id == scheduled_call_id, ScheduledCall.status == "scheduled")
            .update({ScheduledCall.status: "canceled"}, synchronize_session=False)
        )
        self.db.commit()
        if not claimed:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel a scheduled call in status '{sc.status}'.",
            )
        if sc.queue_job_id:
            from core.services.ingestion_queue import cancel_outbound_job

            cancel_outbound_job(sc.queue_job_id)
        self.db.refresh(sc)
        logger.info("[outbound] scheduled call canceled id={}", scheduled_call_id)
        return sc

    def cancel_scheduled_calls(self, ids) -> Dict[str, Any]:
        """Cancel many scheduled calls (multi-select). Each is handled independently —
        a row that can't be canceled (already dispatched/terminal/not found) is reported
        in ``skipped`` rather than failing the whole batch."""
        canceled: List[str] = []
        skipped: List[Dict[str, str]] = []
        for sid in ids:
            try:
                self.cancel_scheduled_call(sid)
                canceled.append(str(sid))
            except HTTPException as exc:
                skipped.append({"id": str(sid), "error": str(exc.detail)})
        logger.info("[outbound] bulk cancel: canceled={} skipped={}", len(canceled), len(skipped))
        return {"canceled": len(canceled), "canceled_ids": canceled, "skipped": skipped}

    # -------------------------------------------------------------- read paths

    def _get_owned(self, scheduled_call_id) -> ScheduledCall:
        sc = self.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
        if not sc:
            raise HTTPException(status_code=404, detail="Scheduled call not found.")
        return sc

    def get_scheduled_call(self, scheduled_call_id) -> Dict[str, Any]:
        sc = self._get_owned(scheduled_call_id)
        agent = self.db.query(Agent).filter(Agent.id == sc.agent_id).first()
        contact = None
        if sc.contact_id:
            contact = self.query(Contact).filter(Contact.id == sc.contact_id).first()
        return self._to_response(sc, agent_name=agent.name if agent else None, contact=contact)

    def list_scheduled_calls(
        self,
        page_no: int = 1,
        page_size: int = 10,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        start_date_time: Optional[str] = None,
        end_date_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        q = self.query(ScheduledCall)
        for f in filters or []:
            field = f.get("field")
            value = f.get("value")
            if value in (None, "", []):
                continue
            if field == "status":
                q = q.filter(ScheduledCall.status.in_(value if isinstance(value, list) else [value]))
            elif field == "agent_id":
                q = q.filter(ScheduledCall.agent_id == value)
            elif field == "to_number":
                q = q.filter(ScheduledCall.to_number.ilike(f"%{value}%"))

        if start_date_time is not None:
            q = q.filter(ScheduledCall.scheduled_at >= start_date_time)
        if end_date_time is not None:
            q = q.filter(ScheduledCall.scheduled_at <= end_date_time)

        total = q.count()
        sort_map = {
            "scheduled_at": ScheduledCall.scheduled_at,
            "created_at": ScheduledCall.created_at,
            "status": ScheduledCall.status,
        }
        col = sort_map.get(sort_by or "scheduled_at", ScheduledCall.scheduled_at)
        col = col.asc() if sort_order == "asc" else col.desc()
        rows = q.order_by(col).offset((page_no - 1) * page_size).limit(page_size).all()

        agent_ids = {r.agent_id for r in rows}
        names = {}
        if agent_ids:
            names = {a.id: a.name for a in self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()}

        # Resolve the linked contact (FK) so the list can show contact name/phone.
        contact_ids = {r.contact_id for r in rows if r.contact_id}
        contacts_by_id = {}
        if contact_ids:
            contacts_by_id = {
                c.id: c for c in self.query(Contact).filter(Contact.id.in_(contact_ids)).all()
            }
        return {
            "data": [
                self._to_response(r, agent_name=names.get(r.agent_id), contact=contacts_by_id.get(r.contact_id))
                for r in rows
            ],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    @staticmethod
    def _to_response(sc: ScheduledCall, agent_name: Optional[str] = None, contact: Optional[Contact] = None) -> Dict[str, Any]:
        return {
            "id": str(sc.id),
            "agent_id": str(sc.agent_id),
            "agent_name": agent_name,
            "contact_id": str(sc.contact_id) if sc.contact_id else None,
            "contact_name": contact.name if contact else None,
            "contact_phone_number": contact.phone_number if contact else None,
            "status": sc.status,
            "from_number": sc.from_number,
            "to_number": sc.to_number,
            "scheduled_at": sc.scheduled_at.isoformat() if sc.scheduled_at else None,
            "provider_call_sid": sc.provider_call_sid,
            "call_id": str(sc.call_id) if sc.call_id else None,
            "error": sc.error,
            "created_at": sc.created_at.isoformat() if sc.created_at else None,
        }
