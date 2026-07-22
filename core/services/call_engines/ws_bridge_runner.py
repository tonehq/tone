"""Pod-local WebSocket-bridge runner (runs ON an outbound voice pod).

The WS "test bridge" trigger must NOT run its media pipeline on the API/orchestrator pod
(that OOMs under parallel load). Instead the originator picks an outbound voice pod and
HTTP-POSTs it ``/internal/ws-bridge/start`` (``main.py``), which calls ``start_local_bridge``
here. So THIS module always executes on the outbound voice pod that will carry the media.

It owns everything that used to live inline in ``WebSocketCallEngine``: opening the outbound
WS client to the remote ``/ws/test``, running the bridged bot, enforcing the per-pod
``MAX_CONCURRENT_CALLS`` ceiling, and advancing the ``scheduled_calls`` row to terminal +
refilling the batch when the bridge ends (WS calls have no Twilio status callback, so the
bridge thread is the only place a WS-triggered row reaches a terminal state).
"""

import threading
import uuid
from typing import Any, Dict, Optional
from urllib.parse import quote

from loguru import logger

from shared.config import settings

# call_id -> {"thread", "status", "stop"} for bridge_status / end_bridge and the cap count.
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSIONS_LOCK = threading.Lock()

# The one PCM rate for the whole bridge. We DECLARE it in the /ws/test URL so the remote tags
# inbound audio at exactly this rate — the two sides can never disagree (a mismatch is what makes
# ASR return empty transcripts while VAD still fires). 24 kHz = Cartesia's native TTS rate on both
# ends, so there is also no resampling anywhere on the TTS→wire→STT path.
_BRIDGE_SAMPLE_RATE = 24000


class AtCapacity(RuntimeError):
    """Raised when this pod is already running ``MAX_CONCURRENT_CALLS`` bridges."""


def active_count() -> int:
    """Number of live bridges on this pod (used for the cap check and diagnostics)."""
    with _SESSIONS_LOCK:
        return len(_SESSIONS)


def _remote_uri(to_number: str, agent_id: str) -> str:
    """Build the remote ``/ws/test`` URI. Routing mirrors a real call: the remote resolves ITS
    agent by the dialed number (``?phone_number=…``); ``WS_CALL_TARGET_AGENT_ID`` is only a
    fallback when there is no number. Raises if the WS target host is unset."""
    target_url = (settings.WS_CALL_TARGET_URL or "").rstrip("/")
    if not target_url:
        raise ValueError(
            "WebSocket trigger is not configured — set WS_CALL_TARGET_URL "
            "(the remote deployment's /ws/test base URL)."
        )
    to_number = (to_number or "").strip()
    fallback_agent_id = (settings.WS_CALL_TARGET_AGENT_ID or "").strip()
    if to_number:
        remote_query = f"phone_number={quote(to_number)}"
    elif fallback_agent_id:
        remote_query = f"agent_id={quote(fallback_agent_id)}"
    else:
        raise ValueError(
            "WebSocket trigger has no target — provide a to_number (routed by number on the "
            "remote) or set WS_CALL_TARGET_AGENT_ID as a fallback."
        )
    # Declare our PCM rate so the remote tags inbound audio identically (no rate disagreement).
    return f"{target_url}/ws/test?{remote_query}&sample_rate={_BRIDGE_SAMPLE_RATE}"


def start_local_bridge(
    agent_id: str,
    to_number: str,
    from_number: str = "",
    scheduled_call_id: Optional[str] = None,
) -> str:
    """Start the WS bridge in a detached daemon thread ON THIS POD and return its call_id.

    Enforces the per-pod ``MAX_CONCURRENT_CALLS`` ceiling atomically under the sessions lock:
    if the pod is already at the limit, raises ``AtCapacity`` and starts nothing — the caller
    (the ``/internal/ws-bridge/start`` route) turns that into a 429 so the originator queues."""
    remote_uri = _remote_uri(to_number, agent_id)  # validate BEFORE claiming a slot
    call_id = uuid.uuid4().hex
    cap = settings.MAX_CONCURRENT_CALLS
    stop = threading.Event()
    thread = threading.Thread(
        target=_bridge_thread,
        args=(call_id, remote_uri, str(agent_id), scheduled_call_id),
        name=f"ws-call-{call_id[:8]}",
        daemon=True,
    )
    with _SESSIONS_LOCK:
        if cap and cap > 0 and len(_SESSIONS) >= cap:
            raise AtCapacity(f"pod at MAX_CONCURRENT_CALLS={cap}")
        _SESSIONS[call_id] = {"thread": thread, "status": "dialing", "stop": stop}
    logger.info(
        "[outbound][ws] starting local bridge call_id={} agent={} remote={} scheduled_call_id={} live={}",
        call_id, agent_id, remote_uri, scheduled_call_id, len(_SESSIONS),
    )
    thread.start()
    return call_id


def _bridge_thread(call_id, remote_uri, agent_id, scheduled_call_id) -> None:
    """Thread entry: run the async bridge to completion, then mark the row terminal."""
    import asyncio

    terminal = "completed"
    try:
        asyncio.run(_run_bridge(call_id, remote_uri, agent_id))
    except Exception:
        terminal = "failed"
        logger.exception("[outbound][ws] bridge failed call_id={}", call_id)
    finally:
        with _SESSIONS_LOCK:
            sess = _SESSIONS.get(call_id)
            if sess is not None:
                sess["status"] = terminal
        _finalize_scheduled_call(scheduled_call_id, terminal)
        with _SESSIONS_LOCK:
            _SESSIONS.pop(call_id, None)
        logger.info("[outbound][ws] bridge finished call_id={} status={}", call_id, terminal)


async def _run_bridge(call_id, remote_uri, agent_id) -> None:
    """Open the outbound WS client to the remote ``/ws/test`` and run our outbound agent
    bridged to it. Blocks until the media session ends."""
    from pipecat.runner.types import RunnerArguments
    from pipecat.transports.websocket.client import (WebsocketClientParams,
                                                     WebsocketClientTransport)

    from core.bot import run_bot
    from core.serializers.raw_pcm import RawPCMSerializer

    # Raw-PCM bridge at 24 kHz BOTH ways — must match the remote /ws/test rate (Cartesia native),
    # so there is ZERO resampling on the TTS→wire→STT path (a 24→16 kHz resample keeps enough
    # energy for VAD but degrades audio enough that Deepgram transcribes NOTHING).
    params = WebsocketClientParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=_BRIDGE_SAMPLE_RATE,
        audio_out_sample_rate=_BRIDGE_SAMPLE_RATE,
        add_wav_header=False,
        serializer=RawPCMSerializer(sample_rate=_BRIDGE_SAMPLE_RATE, num_channels=1),
    )
    transport = WebsocketClientTransport(uri=remote_uri, params=params)

    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(call_id)
        if sess is not None:
            sess["status"] = "in_progress"

    runner_args = RunnerArguments(
        body={
            "agent_id": agent_id,
            "direction": "outbound",
            "transport_type": "websocket",
        }
    )
    logger.info("[outbound][ws] bridge connecting call_id={} remote={}", call_id, remote_uri)
    await run_bot(transport, runner_args)


def _finalize_scheduled_call(scheduled_call_id, terminal_status: str) -> None:
    """Advance the scheduled_calls row to a terminal status and refill its batch.

    WebSocket calls have no Twilio status callback, so this is the ONLY place a WS-triggered
    scheduled row reaches a terminal state. Runs in the bridge thread with its own DB session.
    No-op for immediate calls (no scheduled_call_id)."""
    if not scheduled_call_id:
        return
    try:
        from core.database.session import get_db_context
        from core.models.scheduled_call import ScheduledCall
        from core.services.outbound_call_service import (_TERMINAL,
                                                        _get_refill_executor,
                                                        _refill_batch_job)

        with get_db_context() as db:
            sc = db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
            if sc is None:
                return
            # Only advance if not already terminal (idempotent; avoids regressing a row an
            # operator may have canceled).
            if (sc.status or "") not in _TERMINAL:
                sc.status = terminal_status
                db.commit()
                logger.info(
                    "[outbound][ws] scheduled call id={} -> {}", scheduled_call_id, terminal_status
                )
            batch_id = sc.batch_id
            has_limit = sc.batch_id is not None and bool(sc.max_concurrency)
        # Free the batch slot so the next held row dials (safety-net drain also covers this).
        if has_limit:
            _get_refill_executor().submit(_refill_batch_job, batch_id)
    except Exception:
        logger.exception(
            "[outbound][ws] failed to finalize scheduled call id={}", scheduled_call_id
        )


def end_bridge(call_id: str) -> bool:
    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(call_id)
    if sess is None:
        return False
    sess["stop"].set()
    logger.info("[outbound][ws] end_bridge requested call_id={}", call_id)
    return True


def bridge_status(call_id: str) -> Dict[str, Any]:
    with _SESSIONS_LOCK:
        sess = _SESSIONS.get(call_id)
    return {"call_id": call_id, "status": sess["status"] if sess else "completed"}
