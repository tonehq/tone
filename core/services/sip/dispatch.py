from typing import Any, Dict, Optional

import httpx
import requests
from loguru import logger
from pipecat.runner.types import LiveKitRunnerArguments

from core.database.session import get_db_context
from core.services.pod_picker import PodPicker
from core.services.webrtc.dispatcher import get_bot_dispatcher
from shared.config import settings

HANDOFF_TIMEOUT_SECONDS = 10.0
HANDOFF_PATH = "/internal/livekit/start"


def build_handoff_payload(
    room_name: str,
    grant: Dict[str, str],
    agent_id: str,
    direction: str,
    from_number: str,
    to_number: str,
    trunk_id: str = "",
    scheduled_call_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "room": room_name,
        "url": grant["url"],
        "token": grant["token"],
        "agent_id": str(agent_id),
        "direction": direction,
        "from": from_number,
        "to": to_number,
        "trunk_id": trunk_id,
    }
    if scheduled_call_id:
        payload["scheduled_call_id"] = str(scheduled_call_id)
    return payload


def build_runner_args(payload: Dict[str, Any]) -> LiveKitRunnerArguments:
    body: Dict[str, Any] = {
        "agent_id": payload["agent_id"],
        "transport_type": "livekit",
        "direction": payload.get("direction") or "inbound",
        "call_data": {
            "from": payload.get("from") or "",
            "to": payload.get("to") or "",
            "call_id": payload["room"],
            "stream_id": payload["room"],
            "sip_trunk_id": payload.get("trunk_id") or "",
        },
    }
    if payload.get("scheduled_call_id"):
        body["scheduled_call_id"] = payload["scheduled_call_id"]
    return LiveKitRunnerArguments(
        room_name=payload["room"],
        url=payload["url"],
        token=payload["token"],
        body=body,
    )


def _pick_voice_pod(direction: str):
    with get_db_context() as db:
        if direction == "outbound":
            picker = PodPicker.for_outbound(db)
            pod = picker.pick()
            return picker.internal_base_for(pod), (pod.name if pod is not None else None)
        picker = PodPicker(db)
        pod = picker.pick()
        return picker.http_base_for(pod), (pod.name if pod is not None else None)


def _handoff_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.WS_BRIDGE_INTERNAL_TOKEN:
        headers["x-ws-bridge-token"] = settings.WS_BRIDGE_INTERNAL_TOKEN
    return headers


def _handoff_result(status_code: int, body: str, pod_name, room: str) -> bool:
    if status_code in (200, 202):
        logger.info("[sip] pipeline handed off to voice pod={} room={}", pod_name, room)
        return True
    logger.warning(
        "[sip] voice pod refused hand-off pod={} status={} body={}",
        pod_name, status_code, body[:200],
    )
    return False


async def handoff_to_voice_pod(payload: Dict[str, Any]) -> bool:
    base, pod_name = _pick_voice_pod(payload.get("direction") or "inbound")
    if not base:
        logger.warning(
            "[sip] no voice pod available — running pipeline locally room={}", payload.get("room")
        )
        return False
    try:
        async with httpx.AsyncClient(timeout=HANDOFF_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{base}{HANDOFF_PATH}", json=payload, headers=_handoff_headers()
            )
    except Exception:
        logger.exception(
            "[sip] voice pod hand-off failed pod={} room={}", pod_name, payload.get("room")
        )
        return False
    return _handoff_result(response.status_code, response.text, pod_name, payload["room"])


def handoff_to_voice_pod_sync(payload: Dict[str, Any]) -> bool:
    base, pod_name = _pick_voice_pod(payload.get("direction") or "inbound")
    if not base:
        logger.warning(
            "[sip] no voice pod available — running pipeline locally room={}", payload.get("room")
        )
        return False
    try:
        response = requests.post(
            f"{base}{HANDOFF_PATH}",
            json=payload,
            headers=_handoff_headers(),
            timeout=HANDOFF_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception(
            "[sip] voice pod hand-off failed pod={} room={}", pod_name, payload.get("room")
        )
        return False
    return _handoff_result(response.status_code, response.text, pod_name, payload["room"])


async def dispatch_call(payload: Dict[str, Any]) -> None:
    room_name = payload["room"]
    dispatcher = get_bot_dispatcher()
    try:
        if await handoff_to_voice_pod(payload):
            dispatcher.release(room_name)
            return
        await dispatcher.dispatch_reserved(room_name, build_runner_args(payload))
    except Exception:
        logger.exception("[sip] bot dispatch failed room={}", room_name)
        dispatcher.release(room_name)


def dispatch_call_sync(payload: Dict[str, Any]) -> bool:
    return handoff_to_voice_pod_sync(payload)
