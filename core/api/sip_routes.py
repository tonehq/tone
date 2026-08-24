from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from livekit import api
from loguru import logger
from pipecat.runner.types import LiveKitRunnerArguments

from core.database.session import get_db_context
from core.services.agent_runner_service import AgentRunnerService
from core.services.sip.livekit_termination import LiveKitTermination
from core.services.transport.telephony_credentials import channel_config
from core.services.webrtc.dispatcher import LocalBotDispatcher
from shared.config import settings

router = APIRouter()

_dispatcher = LocalBotDispatcher()

SIP_ATTR_CALLED_NUMBER = "sip.trunkPhoneNumber"
SIP_ATTR_CALLER_NUMBER = "sip.phoneNumber"
SIP_ATTR_TRUNK_ID = "sip.trunkID"


def _livekit_config(org_id=None) -> Dict[str, Any]:
    return channel_config("livekit", org_id=org_id)


def _verify(body: bytes, auth_header: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    api_key = (config.get("api_key") or "").strip()
    api_secret = (config.get("api_secret") or "").strip()
    if not api_key or not api_secret:
        logger.warning("[sip] livekit webhook rejected — no livekit channel configured")
        return None
    try:
        receiver = api.WebhookReceiver(api_key, api_secret)
        event = receiver.receive(body.decode("utf-8"), auth_header)
        return event
    except Exception:
        logger.exception("[sip] livekit webhook signature verification failed")
        return None


def _participant_numbers(participant) -> Dict[str, str]:
    attributes = dict(getattr(participant, "attributes", {}) or {})
    return {
        "to": attributes.get(SIP_ATTR_CALLED_NUMBER, ""),
        "from": attributes.get(SIP_ATTR_CALLER_NUMBER, ""),
        "trunk_id": attributes.get(SIP_ATTR_TRUNK_ID, ""),
    }


@router.post("/sip/livekit-webhook")
async def livekit_webhook(request: Request) -> Dict[str, Any]:
    raw = await request.body()
    config = _livekit_config()
    event = _verify(raw, request.headers.get("authorization", ""), config)
    if event is None:
        return {"ok": False}

    event_name = getattr(event, "event", "")
    if event_name != "participant_joined":
        return {"ok": True}

    participant = getattr(event, "participant", None)
    room = getattr(event, "room", None)
    if participant is None or room is None:
        return {"ok": True}

    numbers = _participant_numbers(participant)
    if not numbers["to"]:
        return {"ok": True}

    room_name = room.name
    if _dispatcher.is_active(room_name):
        return {"ok": True}

    with get_db_context() as db:
        agent = AgentRunnerService(db).get_agent_by_phone_number(numbers["to"])

    if agent is None:
        logger.warning(
            "[sip] inbound rejected — no agent assigned to {} (room={})", numbers["to"], room_name
        )
        return {"ok": False, "reason": "no_agent_for_number"}

    grant = LiveKitTermination(config).bot_grant(room_name)
    runner_args = LiveKitRunnerArguments(
        room_name=room_name,
        url=grant["url"],
        token=grant["token"],
        body={
            "agent_id": str(agent.id),
            "transport_type": "livekit",
            "direction": "inbound",
            "call_data": {
                "from": numbers["from"],
                "to": numbers["to"],
                "call_id": room_name,
                "stream_id": room_name,
                "sip_trunk_id": numbers["trunk_id"],
            },
        },
    )

    logger.info(
        "[sip] inbound routed room={} from={} to={} agent={}",
        room_name, numbers["from"], numbers["to"], agent.id,
    )
    await _dispatcher.dispatch(room_name, runner_args)
    return {"ok": True, "agent_id": str(agent.id), "room": room_name}


@router.post("/sip/status")
async def sip_status(request: Request) -> Dict[str, Any]:
    from core.models.scheduled_call import ScheduledCall
    from core.services.outbound_call_service import OutboundCallService

    try:
        payload = await request.json()
    except Exception:
        logger.exception("[sip] /sip/status received a malformed body")
        return {"ok": False}

    scheduled_call_id = (payload.get("scheduled_call_id") or "").strip()
    call_status = (payload.get("status") or "").strip()
    logger.info(
        "[sip] /sip/status call_id={} status={} scheduled_call_id={}",
        payload.get("call_id"), call_status, scheduled_call_id,
    )
    if not scheduled_call_id:
        return {"ok": True}

    try:
        with get_db_context() as db:
            sc = db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
            if sc is not None:
                OutboundCallService(db, org_id=sc.organization_id).handle_status_callback(
                    scheduled_call_id,
                    {
                        "CallSid": payload.get("call_id"),
                        "CallStatus": call_status,
                        "CallDuration": payload.get("duration"),
                        "To": payload.get("to"),
                        "From": payload.get("from"),
                    },
                )
    except Exception:
        logger.exception("[sip] /sip/status failed scheduled_call_id={}", scheduled_call_id)

    return {"ok": True}
