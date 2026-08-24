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
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.channel import Channel
from core.models.contact import Contact
from core.models.phone_number import PhoneNumber
from core.models.scheduled_call import ScheduledCall
from core.services.base import BaseService
from core.services.call_engines import get_call_engine
from core.services.call_engines.websocket_engine import NoOutboundCapacity
from core.services.outbound_capacity import get_env_outbound_ceiling, resolve_batch_concurrency
from core.services.transport.telephony_credentials import get_provider_credentials
from shared.config import settings

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

# Role permitted to use the WebSocket ("test bridge") outbound trigger. Assigned via SQL only
# (``UPDATE members SET role='super_admin' WHERE ...``) — there is no UI/API to grant it.
SUPER_ADMIN_ROLE = "super_admin"

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

# Non-terminal, post-claim states that occupy a concurrency slot (a live outbound leg):
# claimed but not yet dialed, ringing, and connected. Used by the concurrency limiter to
# count "in-flight" calls against MAX_CONCURRENT_OUTBOUND_CALLS.
_ACTIVE_OUTBOUND_STATES = ("processing", "dispatched", "in_progress")

# Upper bound on how many held/waiting rows the per-minute drain safety-net attempts per tick,
# so a large backlog can't scan unboundedly in one run.
_DRAIN_MAX = 500

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

# Best-effort OUTBOUND background thread pools, created LAZILY on first use (not at import), so
# nothing is allocated until a call actually needs it and the size reflects the CURRENT
# settings.OUTBOUND_BG_WORKERS at that moment:
#   - _PREWARM_EXECUTOR: pipeline-config cache pre-warming (after a dial, while it rings).
#   - _REFILL_EXECUTOR: the completion refill, which enqueues via asyncio.run() — that CANNOT run
#     inside the status webhook's async event loop, so it must run on a worker thread.
# Cap = settings.OUTBOUND_BG_WORKERS (env); 0/negative → None = the runtime's default cap
# (on-demand, no idle threads). A positive value pins an explicit ceiling.
_PREWARM_EXECUTOR: Optional[ThreadPoolExecutor] = None
_REFILL_EXECUTOR: Optional[ThreadPoolExecutor] = None
_EXECUTOR_LOCK = threading.Lock()


def _bg_max_workers() -> Optional[int]:
    n = settings.OUTBOUND_BG_WORKERS
    return n if isinstance(n, int) and n > 0 else None


def _get_prewarm_executor() -> ThreadPoolExecutor:
    global _PREWARM_EXECUTOR
    if _PREWARM_EXECUTOR is None:
        with _EXECUTOR_LOCK:
            if _PREWARM_EXECUTOR is None:
                _PREWARM_EXECUTOR = ThreadPoolExecutor(
                    max_workers=_bg_max_workers(), thread_name_prefix="prewarm"
                )
    return _PREWARM_EXECUTOR


def _get_refill_executor() -> ThreadPoolExecutor:
    global _REFILL_EXECUTOR
    if _REFILL_EXECUTOR is None:
        with _EXECUTOR_LOCK:
            if _REFILL_EXECUTOR is None:
                _REFILL_EXECUTOR = ThreadPoolExecutor(
                    max_workers=_bg_max_workers(), thread_name_prefix="outbound-refill"
                )
    return _REFILL_EXECUTOR


def _refill_batch_job(batch_id) -> None:
    """Enqueue the next DUE waiting call(s) of ``batch_id`` to fill slot(s) a just-finished
    call freed. Runs in a worker thread with its OWN DB session (never shares the request's).
    Best-effort — the periodic drain covers any miss."""
    from sqlalchemy import func as _func

    from core.database.session import get_db_context
    from core.services.ingestion_queue import enqueue_outbound_calls_batch

    try:
        with get_db_context() as db:
            sample = (
                db.query(ScheduledCall).filter(ScheduledCall.batch_id == batch_id).first()
            )
            if sample is None or not sample.max_concurrency:
                return
            active = (
                db.query(_func.count(ScheduledCall.id))
                .filter(
                    ScheduledCall.batch_id == batch_id,
                    ScheduledCall.status.in_(_ACTIVE_OUTBOUND_STATES),
                )
                .scalar()
                or 0
            )
            free = sample.max_concurrency - active
            if free <= 0:
                return
            now = datetime.now(timezone.utc)
            rows = (
                db.query(ScheduledCall)
                .filter(
                    ScheduledCall.batch_id == batch_id,
                    ScheduledCall.status == "scheduled",
                    ScheduledCall.scheduled_at <= now,
                )
                .order_by(ScheduledCall.scheduled_at.asc())
                .limit(free)
                .all()
            )
            if not rows:
                return
            items = [(sc.id, sc.organization_id, now) for sc in rows]
            results = enqueue_outbound_calls_batch(items)
            for sc, (job_id, err) in zip(rows, results):
                if err is None and job_id is not None:
                    sc.queue_job_id = job_id
            db.commit()
            logger.info(
                "[outbound] completion refill enqueued {} waiting call(s) for batch {}",
                len(rows), batch_id,
            )
    except Exception:  # noqa: BLE001
        logger.exception("[outbound] completion refill job failed batch={}", batch_id)

# How long a 'scheduled' row may sit with no queue job before reconcile re-enqueues it.
# Longer than the enqueue round-trip so we never race a batch that's mid-creation.
_ORPHAN_GRACE = timedelta(minutes=2)

# A row stuck in 'processing' with no provider_call_sid is only re-claimed (crash recovery) once
# it has sat that way longer than this. Guards against a DOUBLE-DIAL: while a dispatch is mid
# hand-off (for WebSocket, an HTTP POST to another pod — a wide window), the row is
# 'processing'+sid=NULL; without this age gate a concurrent dispatcher (the Procrastinate job AND
# the periodic drain) would re-claim it and start a SECOND bridge. Must exceed the hand-off /
# provider-call round-trip (WS hand-off httpx timeout is 10s).
_PROCESSING_RECLAIM_GRACE = timedelta(seconds=90)




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
        _get_prewarm_executor().submit(_warm)

    @staticmethod
    def _normalize_e164(number: str, field: str) -> str:
        normalized = (number or "").strip().replace(" ", "")
        if not _E164_RE.match(normalized):
            raise HTTPException(
                status_code=400,
                detail=f"{field} must be E.164 format (e.g. +14155550123).",
            )
        return normalized

    def select_from_number(self, agent, explicit: Optional[str] = None, provider: Optional[str] = None) -> str:
        """Resolve the outbound caller-id — the SINGLE place outbound number choice lives.

        Explicit selection always wins (validated E.164). When omitted, auto-select from
        the org's configured telephony numbers: prefer numbers assigned to ``agent``, else any
        org number; a single number is used directly, multiple numbers round-robin
        by least-recently-used (from recent ``scheduled_calls`` usage — no extra state).
        Every outbound path calls this so number choice is never re-implemented.
        """
        if explicit and str(explicit).strip():
            return self._normalize_e164(explicit, "from_number")

        query = (
            self.db.query(PhoneNumber)
            .join(Channel, Channel.id == PhoneNumber.channel_id)
            .filter(PhoneNumber.organization_id == self.org_id)
        )
        if provider:
            query = query.filter(Channel.channel_type == provider)
        else:
            query = query.filter(Channel.channel_type.in_(self._PSTN_PROVIDERS))
        candidates = query.all()
        # Prefer this agent's assigned numbers; otherwise any org number.
        agent_numbers = [pn.number for pn in candidates if pn.agent_id == agent.id]
        pool = agent_numbers or [pn.number for pn in candidates]

        seen: set = set()
        numbers: List[str] = []
        for n in pool:
            nn = (n or "").strip()
            if nn and _E164_RE.match(nn) and nn not in seen:
                seen.add(nn)
                numbers.append(nn)

        if not numbers:
            raise HTTPException(
                status_code=400,
                detail="No outbound phone number is configured for this organization. "
                       "Add a Twilio, Telnyx or SIP trunk number, or pick one explicitly.",
            )
        if len(numbers) == 1:
            return numbers[0]
        return self._least_recently_used_number(numbers)

    def _least_recently_used_number(self, numbers: List[str]) -> str:
        """Round-robin across ``numbers`` by picking the one used least recently as a
        ``scheduled_calls.from_number`` (org-scoped). Never-used numbers go first, then the
        oldest last-use. Note: the caller resolves the from-number once per request
        (``_validate_agent_and_from``), so rotation spreads across successive batches — every
        call within a single bulk batch shares the one selected number, by design."""
        rows = (
            self.query(ScheduledCall)
            .filter(ScheduledCall.from_number.in_(numbers))
            .with_entities(ScheduledCall.from_number, func.max(ScheduledCall.created_at))
            .group_by(ScheduledCall.from_number)
            .all()
        )
        last_used = {num: ts for num, ts in rows}
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        # (used?, last_use): never-used (False, epoch) sort first; among used, oldest first.
        return min(numbers, key=lambda n: (n in last_used, last_used.get(n) or epoch))

    _PSTN_PROVIDERS = ("twilio", "telnyx", "sip")
    _SUPPORTED_PROVIDERS = ("twilio", "telnyx", "sip", "websocket")

    def _validate_provider(self, provider: Optional[str]) -> str:
        """Normalize + validate the trigger provider. Empty means auto — the engine is
        resolved from the from-number's channel. ``websocket`` additionally requires
        the remote /ws/test target to be configured, checked here so the user gets an
        immediate 400 instead of a silent worker failure at dispatch time."""
        provider = (provider or "").strip().lower()
        if not provider:
            return ""
        if provider not in self._SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown trigger provider '{provider}'. Supported: {', '.join(self._SUPPORTED_PROVIDERS)}.",
            )
        if provider == "websocket" and not (settings.WS_CALL_TARGET_URL or "").strip():
            # Fail fast at create time (not silently at dispatch) if the remote /ws/test host
            # is unset. The remote agent is resolved by the dialed to_number on that side, so
            # only the target host is required here (WS_CALL_TARGET_AGENT_ID is an optional
            # fallback used by the engine when a call carries no number).
            raise HTTPException(
                status_code=400,
                detail="WebSocket trigger is not configured (WS_CALL_TARGET_URL is unset).",
            )
        return provider

    def _validate_agent_and_from(self, agent_id, from_number: Optional[str] = None, *, provider: str = ""):
        """Validate the agent and resolve the from-number once (shared across a bulk
        batch). ``from_number`` may be None/blank — it is then auto-selected via
        ``select_from_number``. Returns (agent, channel_id, from_number, provider), where
        ``provider`` is the resolved call engine — the from-number's channel type when the
        caller passed no explicit trigger.

        The ``websocket`` trigger places no PSTN call (it bridges to a remote /ws/test and
        routes by ``to_number``), so it requires NO telephony number/channel/credentials: only the
        agent is validated, there is no channel, and any explicit ``from_number`` is passed
        through solely as a display label. This keeps the telephony-free /ws/test bridge usable
        in dev/staging orgs that have no telephony set up."""
        org_id = self.org_id

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

        # WebSocket bridge: no telephony, so skip the from-number/channel/credentials gate.
        # There is no channel; keep any explicit from_number purely as a label (the engine ignores it).
        if provider == "websocket":
            return agent, None, (from_number or "").strip(), provider

        requested = provider if provider in self._PSTN_PROVIDERS else None
        from_number = self.select_from_number(agent, explicit=from_number, provider=requested)

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
        channel_type = ((channel.channel_type if channel else "") or "").strip().lower()
        if channel_type not in self._PSTN_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail="from_number must belong to a Twilio, Telnyx or SIP trunk channel.",
            )
        if requested and channel_type != requested:
            raise HTTPException(
                status_code=400,
                detail=f"from_number does not belong to a {requested} channel.",
            )

        if not get_provider_credentials(channel_type, org_id=org_id):
            raise HTTPException(
                status_code=400,
                detail=f"No {channel_type} credentials configured for this organization.",
            )
        return agent, channel.id, from_number, channel_type

    # ------------------------------------------------------------------ create

    def create_outbound_call(
        self,
        agent_id,
        from_number: Optional[str],
        to_numbers: List[str],
        scheduled_at: Optional[datetime] = None,
        created_by_user_id=None,
        directory_id=None,
        max_concurrency: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Place one or many outbound calls. A single immediate number dials right away;
        multiple numbers (or a scheduled time) are queued as ``scheduled_calls`` rows that
        the worker dials at ``scheduled_at`` (or now), and they show up on the Scheduled
        Calls page. ``provider`` selects the trigger engine (``twilio`` = real PSTN;
        ``websocket`` = bridge to a remote /ws/test)."""
        if not to_numbers:
            raise HTTPException(status_code=400, detail="Provide at least one destination number.")

        provider = self._validate_provider(provider)
        agent, _channel_id, from_number, provider = self._validate_agent_and_from(agent_id, from_number, provider=provider)

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

        # WebSocket provider (immediate): max_concurrency is the NUMBER OF PARALLEL bridge
        # calls to fire at once — a load/parallel test — not a dial-rate limit. Each bridge
        # opens its own WS to the remote /ws/test, so they run concurrently. Deliberately
        # bypasses the dedupe/contacts path (we want N calls to the SAME target).
        if provider == "websocket" and scheduled_at is None:
            return self._dial_parallel_ws(agent, from_number, valid, max_concurrency, invalid)

        # Single immediate call: dial inline for instant feedback (surfaces in Call History).
        if len(valid) == 1 and scheduled_at is None:
            return self._dial_now(agent, from_number, valid[0], invalid, provider=provider)

        # Bulk and/or scheduled: route through the shared create+assign+schedule path so
        # every scheduled number becomes an agent-assigned contact (single implementation —
        # Schedule → Assign Contact to Agent → Create Contact). See _schedule_via_contacts.
        rows = [{"phone_number": num} for num in valid]
        return self._schedule_via_contacts(
            agent, from_number, rows, invalid, scheduled_at, created_by_user_id,
            directory_id=directory_id, max_concurrency=max_concurrency, provider=provider,
        )

    def create_outbound_calls_from_rows(
        self,
        agent_id,
        from_number: Optional[str],
        rows: List[Dict[str, Any]],
        *,
        directory_id=None,
        scheduled_at: Optional[datetime] = None,
        created_by_user_id=None,
        invalid: Optional[List[Dict[str, str]]] = None,
        max_concurrency: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create contacts from parsed ``rows`` (e.g. an uploaded CSV/Excel), assign them to
        the agent, and schedule outbound calls — the file-upload counterpart of
        ``create_outbound_call``. ``directory_id`` selects the target contact directory
        (defaults to the org's "Global" directory). Reuses the same Schedule→Assign→Create
        path (``_schedule_via_contacts``)."""
        if not rows:
            raise HTTPException(status_code=400, detail="No contacts were found in the file.")
        provider = self._validate_provider(provider)
        agent, _channel_id, from_number, provider = self._validate_agent_and_from(agent_id, from_number, provider=provider)
        if scheduled_at is not None and scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at is not None and scheduled_at <= datetime.now(timezone.utc) - timedelta(seconds=60):
            raise HTTPException(status_code=400, detail="scheduled_at must be in the future.")
        return self._schedule_via_contacts(
            agent, from_number, rows, invalid or [], scheduled_at, created_by_user_id,
            directory_id=directory_id, max_concurrency=max_concurrency, provider=provider,
        )

    def _schedule_via_contacts(
        self, agent, from_number, rows, invalid, scheduled_at, created_by_user_id,
        directory_id=None, max_concurrency=None, provider="",
    ) -> Dict[str, Any]:
        """Create each ``rows`` entry as a contact in ``directory_id`` (default the org's
        "Global" directory) AND assign it to ``agent`` (reusing
        ``ContactService.create_contacts(..., agent_id=)`` — which itself reuses
        ``AgentContactService`` for the assignment), then schedule the calls via
        ``schedule_calls_for_contacts``. This is the single Schedule→Assign→Create path; no
        contact create/assign logic is duplicated here."""
        from core.services.contacts.contact_directory_service import ContactDirectoryService
        from core.services.contacts.contact_service import ContactService

        dir_service = ContactDirectoryService(self.db, user_id=self.user_id, org_id=self.org_id)
        directory = (
            dir_service.get_directory(directory_id)
            if directory_id
            else dir_service.get_or_create_default_directory()
        )

        create_result = ContactService(
            self.db, user_id=self.user_id, org_id=self.org_id
        ).create_contacts(directory.id, rows, agent_id=agent.id)

        from uuid import UUID as _UUID

        contact_ids = [_UUID(c["id"]) for c in create_result.get("created", [])]
        if not contact_ids:
            raise HTTPException(
                status_code=400,
                detail="No contacts could be created from the provided data.",
            )

        # Pass the already-resolved from_number explicitly so it isn't re-rotated.
        result = self.schedule_calls_for_contacts(
            agent.id, from_number, contact_ids, scheduled_at, created_by_user_id,
            max_concurrency=max_concurrency, provider=provider,
        )
        result["mode"] = "scheduled" if scheduled_at is not None else "bulk"
        result["invalid"] = (result.get("invalid") or []) + invalid
        result["assigned"] = create_result.get("assigned", len(contact_ids))
        return result

    def _dial_now(self, agent, from_number, to_number, invalid, provider="twilio") -> Dict[str, Any]:
        # No calls row is created here — the call log is written by the pipeline
        # (create_call_log) when the media stream connects.
        logger.info(
            "[outbound] placing immediate call agent={} from={} to={} provider={}",
            agent.id, from_number, to_number, provider,
        )
        base = self._public_base()
        engine = get_call_engine(provider, org_id=self.org_id)
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
            "provider": provider,
            "provider_call_id": info.call_id,
            "invalid": invalid,
        }

    # Hard ceiling on parallel WS bridges from one request, so a large max_concurrency can't
    # spawn unbounded threads. Each bridge is a live media session (a thread) — keep it sane.
    _MAX_PARALLEL_WS = 25

    def _dial_parallel_ws(
        self, agent, from_number, valid: List[str], max_concurrency, invalid
    ) -> Dict[str, Any]:
        """Fan out N parallel WebSocket bridge calls (N = ``max_concurrency`` from the modal;
        default one per destination, cycling ``valid`` so 1 target + N → N calls to it).

        The media must run on the dedicated outbound voice pods, never in THIS originating process
        (that OOMs under load). So this creates N ``scheduled_calls`` rows due NOW (sharing a
        ``batch_id``) and dispatches the hand-off **INLINE** right here — each dispatch atomically
        claims its row, picks an outbound pod (``PodPicker.for_outbound``), and HTTP-POSTs the bridge
        to it (no media on this pod, just a POST). Dispatching inline (instead of only waiting on the
        orchestrator's Procrastinate poll) means an immediate test call triggers on create rather
        than sitting in 'scheduled'. Rows a pod refuses (429) / with no pod free stay 'scheduled' and
        the enqueued Procrastinate jobs + the drain retry the hand-off as pods free."""
        from core.services.call_engines.ws_test_client import prepare_bridge_run

        # Resolve each destination to its remote test scenarios (test-case fan-out). A number assigned
        # to a remote agent with scenarios → one bridge PER scenario, each tracked as a TestRun case
        # (metadata carries run_id + scenario_id); a number with no scenarios / an unreachable remote
        # → a single untracked bridge. If NO destination resolves, fall back to the load-test fan-out
        # (N = max_concurrency, cycling `valid`) so existing behavior is preserved.
        specs: List[tuple] = []  # (to_number, metadata_dict)
        tracked = False
        for num in valid:
            prep = prepare_bridge_run(num)
            if prep and prep.get("scenarios"):
                tracked = True
                run_id = prep["run_id"]
                for sc in prep["scenarios"]:
                    specs.append(
                        (num, {"ws_run_id": run_id, "ws_scenario_id": sc["scenario_id"]})
                    )
            else:
                specs.append((num, {}))

        if not tracked:
            try:
                count = int(max_concurrency) if max_concurrency else 0
            except (TypeError, ValueError):
                count = 0
            count = count if count > 0 else len(valid)
            specs = [(valid[i % len(valid)], {}) for i in range(count)]

        # The cap bounds SIMULTANEOUS bridges for an UNTRACKED load-test (every row dials at once,
        # throttled only by the per-pod MAX_CONCURRENT_CALLS). A TRACKED test-case run is throttled
        # per-batch at DISPATCH (``batch_limit`` below), so we must NOT truncate its scenario rows —
        # dropping cases here would leave their remote TestRun mappings stuck 'pending' forever. Every
        # scenario gets a row; only ``batch_limit`` cases are in flight at a time, the rest queue.
        if not tracked and len(specs) > self._MAX_PARALLEL_WS:
            logger.warning(
                "[outbound][ws] {} bridges requested; capping to {}",
                len(specs), self._MAX_PARALLEL_WS,
            )
            specs = specs[: self._MAX_PARALLEL_WS]
        count = len(specs)

        # Per-batch concurrency (the row's ``max_concurrency``):
        # - TRACKED test-case run → honor the user's requested value (dial K cases at a time; the rest
        #   stay 'scheduled' and refill as each finishes). This is what the modal's "Concurrent calls"
        #   selector controls for a per-case fan-out.
        # - UNTRACKED load-test → admit all N (max_concurrency = count) and let the per-pod
        #   MAX_CONCURRENT_CALLS be the throttle (existing behavior).
        # A batch_id + a non-null limit also enable the completion-refill fast path so a held row dials
        # the instant a slot frees, and let drain_outbound_capacity retry holds.
        batch_limit = resolve_batch_concurrency(max_concurrency) if tracked else count
        batch_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        rows: List[ScheduledCall] = [
            ScheduledCall(
                agent_id=agent.id,
                organization_id=self.org_id,
                channel_id=None,
                from_number=from_number,
                to_number=to_num,
                scheduled_at=now,
                status="scheduled",
                provider="websocket",
                created_by_user_id=None,
                batch_id=batch_id,
                max_concurrency=batch_limit,
                metadata_=meta,
            )
            for (to_num, meta) in specs
        ]
        self._persist_and_enqueue_rows(rows)

        # Trigger the hand-off INLINE now — don't wait on the orchestrator's poll. Each
        # dispatch_scheduled_call claims the row (age-gated so the queued job can't double-dial it),
        # picks an outbound voice pod, and hands off. A row with no free pod stays 'scheduled' and is
        # retried by its Procrastinate job + the drain. Loop is bounded by the row count (untracked:
        # <= _MAX_PARALLEL_WS; tracked: one row per scenario, each held past batch_limit as a no-op).
        placed_calls: List[Dict[str, Any]] = []
        held = 0
        for sc in rows:
            try:
                result = self.dispatch_scheduled_call(sc.id)
                if result is not None and result.status == "dispatched":
                    placed_calls.append(
                        {"to_number": result.to_number, "provider_call_id": result.provider_call_sid}
                    )
                else:
                    held += 1
            except Exception:  # noqa: BLE001
                held += 1
                logger.exception("[outbound][ws] inline dispatch failed id={}", sc.id)
        logger.info(
            "[outbound][ws] immediate fan-out agent={} batch={}: {} placed, {} held (of {})",
            agent.id, batch_id, len(placed_calls), held, len(rows),
        )
        return {
            "mode": "parallel_websocket",
            "status": "dialing" if placed_calls else "queued",
            "provider": "websocket",
            "agent_id": str(agent.id),
            "from_number": from_number,
            "requested": count,
            "placed": len(placed_calls),
            "queued": held,
            "batch_id": str(batch_id),
            "calls": placed_calls,
            "invalid": invalid,
        }

    def _persist_and_enqueue_rows(self, rows: List[ScheduledCall]) -> None:
        """Persist ``scheduled_calls`` rows then defer one Procrastinate job per row at
        that row's own ``scheduled_at`` (so a batch can carry per-contact times). Enqueue
        failures are isolated per row (marked ``failed``) so one bad defer doesn't drop
        the rest of the batch."""
        if not rows:
            return

        # NB: the concurrency cap (MAX_CONCURRENT_OUTBOUND_CALLS) is enforced at DISPATCH
        # time, not here — every row is enqueued at its own schedule_at, and the dispatcher
        # only dials while a slot is free (see dispatch_scheduled_call / drain_outbound_capacity).
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
        from_number: Optional[str],
        contact_ids: List,
        scheduled_at: Optional[datetime] = None,
        created_by_user_id=None,
        max_concurrency: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule outbound calls to the given org-owned contacts.

        Reuses ``_validate_agent_and_from`` (gates outbound/both agent + Twilio
        from-number) and the ``scheduled_calls`` pipeline. Each row carries its
        ``contact_id`` and a per-contact effective time (CSV ``scheduled_at`` overrides
        the request time). Contacts with no/invalid phone are collected into ``invalid``
        rather than failing the whole batch.

        ``max_concurrency`` (from the UI) limits how many of THIS batch's calls run at once:
        the batch gets a shared ``batch_id`` and each row stores the limit in the typed
        ``batch_id`` / ``max_concurrency`` columns, so the dispatcher only dials while fewer
        than ``max_concurrency`` of the batch are in flight (the next fires as one finishes).
        Clamped to the env ceiling when configured."""
        if not contact_ids:
            raise HTTPException(status_code=400, detail="Provide at least one contact.")

        provider = self._validate_provider(provider)
        agent, channel_id, from_number, provider = self._validate_agent_and_from(agent_id, from_number, provider=provider)

        if scheduled_at is not None and scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at is not None and scheduled_at <= datetime.now(timezone.utc) - timedelta(seconds=60):
            raise HTTPException(status_code=400, detail="scheduled_at must be in the future.")

        # Resolve the effective per-batch limit ONCE (UI value → clamp; empty/API → env default;
        # no env → None). One id groups the batch; the limit + id ride on each row's typed
        # columns (``batch_id`` is indexed for the dispatch-time in-flight count).
        batch_limit = resolve_batch_concurrency(max_concurrency)
        batch_id = uuid.uuid4() if batch_limit is not None else None

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
                provider=provider,
                created_by_user_id=created_by_user_id,
                batch_id=batch_id,
                max_concurrency=batch_limit,
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
        # Pre-read the row to resolve its batch — a per-batch concurrency limit lives on the
        # typed ``max_concurrency`` column (grouped by the indexed ``batch_id`` column).
        sc = self.db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
        if sc is None:
            logger.warning("[outbound] dispatch: scheduled call {} not found", scheduled_call_id)
            return None

        # Concurrency admission: a FRESH 'scheduled' row is claimed only while its BATCH has
        # headroom (fewer than ``max_concurrency`` of the batch in flight). The count is folded
        # into the claim's WHERE so admission + claim are one atomic statement (a small transient
        # overshoot is still possible under READ COMMITTED with many concurrent workers —
        # acceptable for a soft call cap). A crashed-'processing' recovery is EXEMPT — that row
        # already holds its slot, so re-dialing it never exceeds the limit.
        batch_id = sc.batch_id
        batch_limit = sc.max_concurrency
        limited = batch_id is not None and isinstance(batch_limit, int) and batch_limit > 0
        now = datetime.now(timezone.utc)
        scheduled_cond = ScheduledCall.status == "scheduled"
        if limited:
            batch_active = (
                self.db.query(func.count(ScheduledCall.id))
                .filter(
                    ScheduledCall.batch_id == batch_id,
                    ScheduledCall.status.in_(_ACTIVE_OUTBOUND_STATES),
                )
                .scalar_subquery()
            )
            scheduled_cond = and_(scheduled_cond, batch_active < batch_limit)
        # ``updated_at`` is stamped on the claim below so the recovery clause can tell a FRESH
        # in-flight claim (do not re-grab — its hand-off is still running) from a genuinely
        # crashed one (safe to recover). A Core ``.update()`` does not fire the ORM ``onupdate``,
        # so we set it explicitly.
        claimed = (
            self.db.query(ScheduledCall)
            .filter(
                ScheduledCall.id == scheduled_call_id,
                or_(
                    scheduled_cond,
                    and_(
                        ScheduledCall.status == "processing",
                        ScheduledCall.provider_call_sid.is_(None),
                        ScheduledCall.updated_at < now - _PROCESSING_RECLAIM_GRACE,
                    ),
                ),
            )
            .update(
                {ScheduledCall.status: "processing", ScheduledCall.updated_at: now},
                synchronize_session=False,
            )
        )
        self.db.commit()
        sc = self.db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
        if sc is None:
            return None
        if not claimed:
            # A still-'scheduled' row that failed to claim under a batch limit was held back by
            # concurrency — leave it queued; the completion/periodic drain retries it.
            if limited and sc.status == "scheduled":
                logger.info(
                    "[outbound] batch concurrency limit reached; holding scheduled call id={} (batch={})",
                    scheduled_call_id, batch_id,
                )
            else:
                logger.info("[outbound] dispatch no-op id={} status={}", scheduled_call_id, sc.status)
            return sc

        # The WebSocket bridge places no PSTN call and ignores callback_base_url (it hands off to
        # an outbound voice pod), so it must NOT require the Twilio BASE_CALL_URL gate.
        base = "" if sc.provider == "websocket" else self._public_base()
        engine = get_call_engine(sc.provider, org_id=sc.organization_id)
        # Test-case fan-out: a websocket row carries its remote run_id/scenario_id in metadata so the
        # bridge runs THAT scenario and the remote records it. Only the websocket engine accepts
        # these; Twilio's signature is untouched.
        _meta = getattr(sc, "metadata_", None) or {}
        _ws_extra = (
            {"ws_run_id": _meta.get("ws_run_id"), "ws_scenario_id": _meta.get("ws_scenario_id")}
            if sc.provider == "websocket"
            else {}
        )
        try:
            info = engine.initiate_call(
                to_number=sc.to_number,
                from_number=sc.from_number,
                agent_id=str(sc.agent_id),
                callback_base_url=base,
                scheduled_call_id=str(sc.id),
                **_ws_extra,
            )
        except NoOutboundCapacity as exc:
            # No outbound voice pod free right now — HOLD the row (revert the claim to 'scheduled')
            # instead of failing it, so the periodic drain / batch refill retries the hand-off when
            # a pod frees. This is the backpressure seam for the WS load-test path.
            self.db.query(ScheduledCall).filter(
                ScheduledCall.id == sc.id, ScheduledCall.status == "processing"
            ).update({ScheduledCall.status: "scheduled"}, synchronize_session=False)
            self.db.commit()
            self.db.refresh(sc)
            logger.info(
                "[outbound] dispatch held id={} — no outbound capacity ({})",
                scheduled_call_id, exc,
            )
            return sc
        except Exception as exc:  # noqa: BLE001
            sc.status = "failed"
            sc.error = str(exc)[:500]
            self.db.commit()
            logger.exception("[outbound] dispatch dial failed id={}", scheduled_call_id)
            return sc

        # Compare-and-set the status: only advance a row that is still 'processing' to
        # 'dispatched'. For the WebSocket bridge, initiate_call returns immediately and the
        # bridge thread's _finalize_scheduled_call may already have written a terminal status
        # from its own session (e.g. an instant connect failure whose teardown beats this
        # commit's round-trip). A plain assign+commit would clobber that back to an active
        # state, stranding the row in 'dispatched' where it holds its batch concurrency slot
        # forever and is never retried by the drain (which only re-dispatches 'scheduled').
        advanced = (
            self.db.query(ScheduledCall)
            .filter(ScheduledCall.id == sc.id, ScheduledCall.status == "processing")
            .update(
                {ScheduledCall.status: "dispatched", ScheduledCall.provider_call_sid: info.call_id},
                synchronize_session=False,
            )
        )
        self.db.commit()
        self.db.refresh(sc)
        if not advanced:
            logger.info(
                "[outbound] dispatch: row already terminal (status={}) before dispatched-mark id={}",
                sc.status, scheduled_call_id,
            )
            return sc
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

    # ------------------------------------------------------ concurrency limiter

    def is_ws_trigger_allowed(self, role: Optional[str]) -> bool:
        """True when ``role`` is the ``super_admin`` role — the only role permitted to use the
        WebSocket ("test bridge") outbound trigger (an internal test tool). Case- and
        whitespace-insensitive; empty/None → denied. Single source of truth for the gate — used by
        both the UI-capabilities payload and the create-time enforcement. The role is assigned via
        SQL only (``UPDATE members SET role='super_admin' WHERE ...``)."""
        return (role or "").strip().lower() == SUPER_ADMIN_ROLE

    def assert_ws_trigger_allowed(self, role: Optional[str], provider: Optional[str]) -> None:
        """Reject provider='websocket' for a caller whose role isn't ``super_admin`` (403). No-op for
        twilio / non-websocket requests. Enforced server-side because the UI gate (hiding the
        selector) is advisory only."""
        if (provider or "").strip().lower() == "websocket" and not self.is_ws_trigger_allowed(role):
            raise HTTPException(
                status_code=403,
                detail="You are not permitted to use the WebSocket trigger.",
            )

    def get_concurrency_max(self, caller_role: Optional[str] = None) -> Dict[str, Any]:
        """UI capabilities payload for the New Outbound Call modal:
        - ``max``: the env ceiling the concurrency selector is capped to and defaults to
          (``None`` = unset, so the field has no upper bound); the actual limit is chosen per
          batch at schedule time.
        - ``ws_trigger_allowed``: whether ``caller_role`` may use the WebSocket trigger (i.e. it is
          the ``super_admin`` role), so the UI can show the "Trigger via" selector for allowed users
          only."""
        return {
            "max": get_env_outbound_ceiling(),
            "ws_trigger_allowed": self.is_ws_trigger_allowed(caller_role),
        }

    def drain_outbound_capacity(self) -> int:
        """Safety net (per-minute worker task): re-drive calls that would otherwise stall. Covers
        two cases, both dispatched INLINE (never re-deferred from inside the worker), bounded per
        tick. Each ``dispatch_scheduled_call`` re-applies the atomic per-batch + capacity check, so
        this can't overshoot. Returns the number dispatched.

        (a) DUE rows a prior claim HELD at dispatch — by a per-batch limit, or (WebSocket) by no
            outbound voice pod being free. Both leave the row 'scheduled' after its Procrastinate
            job already fired, so nothing else re-dials them.
        (b) CRASHED rows stranded in 'processing' with no ``provider_call_sid`` — a dispatch claimed
            the row then died mid hand-off before persisting a SID. Nothing else re-drives a
            'processing' row (the drain and reconcile otherwise only touch 'scheduled'), so without
            this they'd hold their batch slot forever, relying solely on a well-timed Procrastinate
            redelivery. We recover them here once older than ``_PROCESSING_RECLAIM_GRACE`` — the same
            age gate dispatch's recovery clause applies, so a hand-off still in flight is never grabbed."""
        now = datetime.now(timezone.utc)
        rows = (
            self.db.query(ScheduledCall)
            .filter(
                or_(
                    # (a) Held-at-dispatch: batch-limited rows OR WS rows (pod-capacity-held without
                    # a batch limit).
                    and_(
                        ScheduledCall.status == "scheduled",
                        ScheduledCall.scheduled_at <= now,
                        or_(
                            ScheduledCall.batch_id.isnot(None),
                            ScheduledCall.provider == "websocket",
                        ),
                    ),
                    # (b) Crashed-'processing' recovery, age-gated so a live hand-off isn't grabbed.
                    and_(
                        ScheduledCall.status == "processing",
                        ScheduledCall.provider_call_sid.is_(None),
                        ScheduledCall.updated_at < now - _PROCESSING_RECLAIM_GRACE,
                    ),
                )
            )
            .order_by(ScheduledCall.scheduled_at.asc())
            .limit(_DRAIN_MAX)
            .all()
        )
        dispatched = 0
        for sc in rows:
            try:
                result = self.dispatch_scheduled_call(sc.id)
                if result is not None and result.status == "dispatched":
                    dispatched += 1
            except Exception:  # noqa: BLE001
                logger.exception("[outbound] drain dispatch failed id={}", sc.id)
        if dispatched:
            logger.info("[outbound] concurrency drain dispatched {} waiting call(s)", dispatched)
        return dispatched

    def _refill_after_completion(self, completed: ScheduledCall) -> None:
        """A batch-limited call just reached a terminal state, freeing a slot in ITS batch —
        refill the next DUE waiting call(s) of the SAME batch so they dial immediately (no
        waiting for the periodic tick). No-op when the completed call carried no per-batch limit.

        Offloaded to a worker thread: the enqueue uses ``asyncio.run()``, which cannot run inside
        the status webhook's async event loop, and the thread owns its own DB session — so we
        pass only ``batch_id`` (never the ORM object) across the boundary."""
        if completed.batch_id is None or not completed.max_concurrency:
            return
        _get_refill_executor().submit(_refill_batch_job, completed.batch_id)

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
        # A finished call frees a slot in its batch — immediately pull the next batch call.
        if internal in _TERMINAL:
            try:
                self._refill_after_completion(sc)
            except Exception:  # noqa: BLE001
                logger.exception("[outbound] completion refill failed after id={}", scheduled_call_id)
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
