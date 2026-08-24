from typing import Any, Dict, List, Optional

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


def _livekit_channels() -> List[Dict[str, Any]]:
    from core.models.channel import Channel
    from core.utils.encryption import decrypt_json

    configs = []
    with get_db_context() as db:
        for row in db.query(Channel).filter(Channel.channel_type == "livekit").all():
            if not row.encrypted_config:
                continue
            try:
                cfg = decrypt_json(row.encrypted_config) or {}
            except Exception:
                logger.exception("[sip] could not decrypt livekit channel {}", row.id)
                continue
            cfg["organization_id"] = row.organization_id
            configs.append(cfg)
    return configs


def _verify(body: bytes, auth_header: str) -> Optional[tuple]:
    payload = body.decode("utf-8")
    channels = _livekit_channels()
    if not channels:
        logger.warning("[sip] livekit webhook rejected — no livekit channel configured")
        return None
    for config in channels:
        api_key = (config.get("api_key") or "").strip()
        api_secret = (config.get("api_secret") or "").strip()
        if not api_key or not api_secret:
            continue
        try:
            receiver = api.WebhookReceiver(api.TokenVerifier(api_key, api_secret))
            event = receiver.receive(payload, auth_header)
            return event, config
        except Exception as exc:
            logger.debug("[sip] livekit webhook not signed by channel org={}: {}",
                         config.get("organization_id"), exc)
    logger.warning(
        "[sip] livekit webhook rejected — signature did not match any of {} livekit channels",
        len(channels),
    )
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
    verified = _verify(raw, request.headers.get("authorization", ""))
    if verified is None:
        return {"ok": False}
    event, config = verified

    event_name = getattr(event, "event", "")
    room_name = getattr(getattr(event, "room", None), "name", "")
    logger.info("[sip] livekit webhook event={} room={}", event_name, room_name)
    if event_name != "participant_joined":
        return {"ok": True}

    participant = getattr(event, "participant", None)
    room = getattr(event, "room", None)
    if participant is None or room is None:
        return {"ok": True}

    numbers = _participant_numbers(participant)
    if not numbers["to"]:
        logger.warning(
            "[sip] participant_joined without a dialled number room={} attributes={}",
            room_name, dict(getattr(participant, "attributes", {}) or {}),
        )
        return {"ok": True}

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
