"""WebSocket call engine — origination over a WebSocket bridge (no PSTN).

Instead of Twilio placing a phone call, this engine originates the call by opening an
outbound WebSocket *client* to a REMOTE deployment's ``/ws/test`` endpoint and running
THIS deployment's outbound agent bridged to it. tonehq's agent audio streams to the
remote agent and vice-versa — an agent-to-agent conversation carried by WebSocket
(reuses the raw-PCM ``/ws/test`` receiver + ``RawPCMSerializer``).

Runtime shape (mirrors the ``CallEngine`` sync contract):
  ``initiate_call`` is called from sync contexts with no running event loop
  (``dispatch_scheduled_call`` in the Procrastinate worker; ``_dial_now`` in FastAPI's
  sync threadpool). A live media session must NOT block those, so ``initiate_call``
  spawns a **detached daemon thread** that runs the async bridge and returns a
  ``CallInfo`` immediately. Because WebSocket has no Twilio status callback, the bridge
  thread owns the ``scheduled_calls`` status lifecycle: it marks the row terminal on
  completion and refills the batch so held rows dial (otherwise the batch's concurrency
  slot never frees).
"""

import threading
import uuid
from typing import Any, Dict, Optional
from urllib.parse import quote

from loguru import logger

from core.services.call_engines.base import CallEngine, CallInfo
from shared.config import settings

# call_id -> {"thread", "status", "stop"} for get_call_status / end_call.
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSIONS_LOCK = threading.Lock()

# The one PCM rate for the whole bridge. We DECLARE it in the /ws/test URL so the remote
# tags inbound audio at exactly this rate — the two sides can never disagree (a mismatch is
# what makes ASR return empty transcripts while VAD still fires). 24 kHz = Cartesia's native
# TTS rate on both ends, so there is also no resampling anywhere on the TTS→wire→STT path.
_BRIDGE_SAMPLE_RATE = 24000


class WebSocketCallEngine(CallEngine):
    """Originate an outbound call over a WebSocket bridge to a remote ``/ws/test``."""

    def __init__(self, org_id=None):
        self._org_id = org_id

    @property
    def provider_name(self) -> str:
        return "websocket"

    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        agent_id: str,
        callback_base_url: str,
        scheduled_call_id: Optional[str] = None,
    ) -> CallInfo:
        """Start the WebSocket bridge in a detached daemon thread and return immediately.

        Routing mirrors a real call: the remote deployment resolves ITS agent by the dialed
        ``to_number`` (``/ws/test?phone_number=…`` → the same number→agent mapping inbound
        Twilio calls use), so the number the user dials picks the remote agent — no hardcoded
        agent id. ``WS_CALL_TARGET_AGENT_ID`` is only an optional fallback for when no
        ``to_number`` is available. Raises if the WS target host is not configured (surfaced
        to the caller as a dispatch/dial failure, like a Twilio credential error)."""
        target_url = (settings.WS_CALL_TARGET_URL or "").rstrip("/")
        if not target_url:
            raise ValueError(
                "WebSocket trigger is not configured — set WS_CALL_TARGET_URL "
                "(the remote deployment's /ws/test base URL)."
            )

        # Prefer routing by the dialed number (remote resolves its own agent); fall back to a
        # configured default remote agent id only when there is no number to route on.
        to_number = (to_number or "").strip()
        fallback_agent_id = (settings.WS_CALL_TARGET_AGENT_ID or "").strip()
        if to_number:
            remote_query = f"phone_number={quote(to_number)}"
        elif fallback_agent_id:
            remote_query = f"agent_id={quote(fallback_agent_id)}"
        else:
            raise ValueError(
                "WebSocket trigger has no target — provide a to_number (routed by number on "
                "the remote) or set WS_CALL_TARGET_AGENT_ID as a fallback."
            )

        call_id = uuid.uuid4().hex
        # Declare our PCM rate so the remote tags inbound audio identically (no rate disagreement).
        remote_uri = f"{target_url}/ws/test?{remote_query}&sample_rate={_BRIDGE_SAMPLE_RATE}"

        thread = threading.Thread(
            target=self._bridge_thread,
            args=(call_id, remote_uri, str(agent_id), scheduled_call_id),
            name=f"ws-call-{call_id[:8]}",
            daemon=True,
        )
        with _SESSIONS_LOCK:
            _SESSIONS[call_id] = {"thread": thread, "status": "dialing", "stop": threading.Event()}
        logger.info(
            "[outbound][ws] initiating bridge call_id={} agent={} remote={} scheduled_call_id={}",
            call_id, agent_id, remote_uri, scheduled_call_id,
        )
        thread.start()

        return CallInfo(
            call_id=call_id,
            session_id=str(scheduled_call_id or agent_id),
            status="dialing",
            provider="websocket",
        )

    # ------------------------------------------------------------------ bridge

    def _bridge_thread(self, call_id, remote_uri, agent_id, scheduled_call_id) -> None:
        """Thread entry: run the async bridge to completion, then mark the row terminal."""
        import asyncio

        terminal = "completed"
        try:
            asyncio.run(self._run_bridge(call_id, remote_uri, agent_id))
        except Exception:
            terminal = "failed"
            logger.exception("[outbound][ws] bridge failed call_id={}", call_id)
        finally:
            with _SESSIONS_LOCK:
                sess = _SESSIONS.get(call_id)
                if sess is not None:
                    sess["status"] = terminal
            self._finalize_scheduled_call(scheduled_call_id, terminal)
            with _SESSIONS_LOCK:
                _SESSIONS.pop(call_id, None)
            logger.info("[outbound][ws] bridge finished call_id={} status={}", call_id, terminal)

    async def _run_bridge(self, call_id, remote_uri, agent_id) -> None:
        """Open the outbound WS client to the remote ``/ws/test`` and run our outbound
        agent bridged to it. Blocks until the media session ends."""
        from pipecat.runner.types import RunnerArguments
        from pipecat.transports.websocket.client import (WebsocketClientParams,
                                                         WebsocketClientTransport)

        from core.bot import run_bot
        from core.serializers.raw_pcm import RawPCMSerializer

        # Raw-PCM bridge at 24 kHz BOTH ways — this must match the remote /ws/test rate.
        # 24 kHz is Cartesia's native TTS output rate on both ends, so pinning the bridge here
        # means ZERO resampling on the TTS→wire→STT path. That matters: a 24 kHz→16 kHz resample
        # keeps enough energy for VAD/smart-turn to fire but degrades the audio enough that
        # Deepgram (ASR) transcribes NOTHING — an empty user turn, so neither agent ever replies.
        # Keep this rate identical to tone-test's RawPCMTransport(sample_rate=...).
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

    # ------------------------------------------------------------ status/refill

    def _finalize_scheduled_call(self, scheduled_call_id, terminal_status: str) -> None:
        """Advance the scheduled_calls row to a terminal status and refill its batch.

        WebSocket calls have no Twilio status callback, so this is the ONLY place a
        WS-triggered scheduled row reaches a terminal state. Runs in the bridge thread
        with its own DB session. No-op for immediate calls (no scheduled_call_id)."""
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
                # Only advance if not already terminal (idempotent; avoids regressing a
                # row an operator may have canceled).
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

    # ----------------------------------------------------------- control/status

    def end_call(self, call_id: str) -> bool:
        with _SESSIONS_LOCK:
            sess = _SESSIONS.get(call_id)
        if sess is None:
            return False
        sess["stop"].set()
        logger.info("[outbound][ws] end_call requested call_id={}", call_id)
        return True

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        with _SESSIONS_LOCK:
            sess = _SESSIONS.get(call_id)
        return {"call_id": call_id, "status": sess["status"] if sess else "completed"}

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        # WebSocket calls never fetch answer-TwiML (no Twilio in the loop); /twiml/outbound
        # is hardcoded twilio-only, so this is unreachable for the websocket provider.
        raise NotImplementedError("WebSocket call engine does not render TwiML.")
