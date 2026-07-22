"""WebSocket call engine — originate over a WebSocket bridge (no PSTN), on an OUTBOUND voice pod.

Instead of Twilio placing a phone call, this engine originates the call as a WebSocket bridge to
a REMOTE deployment's ``/ws/test`` endpoint (agent-to-agent, no telephony). Crucially, the media
pipeline must run on the dedicated ``staging-tone-outbound-call-worker`` pool — NOT on the
API/orchestrator pod that OOMs under parallel load. Twilio achieves pod placement by handing the
provider a pinned ``/pod/N/ws`` URL to connect INTO; a WS bridge is an OUTBOUND client, so there is
no inbound socket to ingress-pin. Placement is therefore a HAND-OFF:

``initiate_call`` (running on the originating API/orchestrator pod) picks an outbound voice pod via
``PodPicker.for_outbound`` and HTTP-POSTs it ``/internal/ws-bridge/start`` over the StatefulSet's
headless service (intra-cluster, no ingress). That pod runs the bridge locally
(``ws_bridge_runner.start_local_bridge``) and owns the ``scheduled_calls`` terminal lifecycle. If no
pod is live, or the picked pod is at its ``MAX_CONCURRENT_CALLS`` (HTTP 429), ``initiate_call`` raises
``NoOutboundCapacity`` so the caller queues the row and the drain retries it as slots free.
"""

from typing import Any, Dict, Optional

import httpx
from loguru import logger

from core.services.call_engines.base import CallEngine, CallInfo
from shared.config import settings

_HANDOFF_TIMEOUT_SECONDS = 10.0


class NoOutboundCapacity(RuntimeError):
    """No outbound voice pod could accept the bridge right now (none live, or all at capacity).

    Distinct from a hard failure: the caller should QUEUE the row (leave it ``scheduled``) so the
    periodic drain retries the hand-off when a pod frees, rather than marking it ``failed``."""


class WebSocketCallEngine(CallEngine):
    """Originate an outbound WS bridge by handing it off to an outbound voice pod."""

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
        """Pick an outbound voice pod and hand the bridge off to it; return immediately.

        Raises ``NoOutboundCapacity`` when no pod is live or the picked pod is full (429), so the
        caller queues. Raises other exceptions on a genuine hand-off failure (marked ``failed``)."""
        from core.database.session import get_db_context
        from core.services.pod_picker import PodPicker

        # Pick a pod + resolve its intra-cluster URL in a short-lived read-only session.
        with get_db_context() as db:
            picker = PodPicker.for_outbound(db)
            pod = picker.pick()
            base = picker.internal_base_for(pod)
        if pod is None or not base:
            raise NoOutboundCapacity(
                "no live outbound voice pod to run the WS bridge (is the outbound-call-worker "
                "pool up and registered via pod_sync?)"
            )

        payload = {
            "agent_id": str(agent_id),
            "to_number": (to_number or "").strip(),
            "from_number": (from_number or "").strip(),
            "scheduled_call_id": str(scheduled_call_id) if scheduled_call_id else None,
        }
        headers = {}
        if settings.WS_BRIDGE_INTERNAL_TOKEN:
            headers["x-ws-bridge-token"] = settings.WS_BRIDGE_INTERNAL_TOKEN

        url = f"{base}/internal/ws-bridge/start"
        logger.info(
            "[outbound][ws] handing off bridge to pod={} agent={} to={} scheduled_call_id={}",
            getattr(pod, "name", None), agent_id, payload["to_number"], scheduled_call_id,
        )
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=_HANDOFF_TIMEOUT_SECONDS)
        except httpx.TransportError as exc:
            # Pod unreachable / connect or read timeout — e.g. it was picked while still inside the
            # 180s liveness window but has since terminated, or KEDA scaled the pool down mid-load
            # test. Transient (not a config error), so hold the row like a 429 and let the drain
            # retry the hand-off to another pod rather than marking it failed.
            raise NoOutboundCapacity(
                f"hand-off to outbound pod {getattr(pod, 'name', '?')} failed: {exc}"
            ) from exc
        if resp.status_code == 429:
            raise NoOutboundCapacity(f"outbound pod {getattr(pod, 'name', '?')} at capacity")
        if resp.status_code >= 500:
            # Server-side failure at the pod (bridge start blew up, pod restarting, ...). Retryable
            # like a 429 — queue and drain-retry instead of hard-failing. 4xx (bad token / not a
            # voice pod / bad request) is a genuine config error and falls through to raise below.
            raise NoOutboundCapacity(
                f"outbound pod {getattr(pod, 'name', '?')} hand-off failed ({resp.status_code})"
            )
        resp.raise_for_status()
        call_id = (resp.json() or {}).get("call_id")
        if not call_id:
            raise RuntimeError("ws-bridge-start returned no call_id")

        return CallInfo(
            call_id=call_id,
            session_id=str(scheduled_call_id or agent_id),
            status="dialing",
            provider="websocket",
        )

    # ------------------------------------------------------------ control/status

    def end_call(self, call_id: str) -> bool:
        # Bridges run on the outbound pods; the originator has no local session to end. end_call
        # is best-effort here (no cross-pod control channel), so this is a no-op from the origin.
        logger.debug("[outbound][ws] end_call is a no-op on the originator (call_id={})", call_id)
        return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        # Status is owned by the pod running the bridge (it advances the scheduled_calls row);
        # the originator does not track it.
        return {"call_id": call_id, "status": "unknown"}

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        # WebSocket calls never fetch answer-TwiML (no Twilio in the loop); /twiml/outbound is
        # hardcoded twilio-only, so this is unreachable for the websocket provider.
        raise NotImplementedError("WebSocket call engine does not render TwiML.")
