import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Request
from livekit import api
from loguru import logger

from core.database.session import get_db_context
from core.models.channel import Channel
from core.models.scheduled_call import ScheduledCall
from core.services.agent_runner_service import AgentRunnerService
from core.services.outbound_call_service import OutboundCallService
from core.services.sip.dispatch import build_handoff_payload, dispatch_call
from core.services.sip.livekit_termination import (BOT_IDENTITY, SIP_ROOM_PREFIX,
                                                   LiveKitTermination)
from core.services.webrtc.dispatcher import get_bot_dispatcher
from core.utils.encryption import decrypt_json

_HANDOFF_TIMEOUT_SECONDS = 10.0

router = APIRouter()

SIP_ATTR_CALLED_NUMBER = "sip.trunkPhoneNumber"
SIP_ATTR_CALLER_NUMBER = "sip.phoneNumber"
SIP_ATTR_TRUNK_ID = "sip.trunkID"


def _livekit_channels() -> List[Dict[str, Any]]:
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


def _numbers_from_room_meta(room) -> Dict[str, str]:
    metadata = (getattr(room, "metadata", "") or "").strip()
    if metadata:
        try:
            parsed = json.loads(metadata)
            if isinstance(parsed, dict) and parsed.get("to"):
                return {
                    "to": str(parsed["to"]),
                    "from": "",
                    "trunk_id": str(parsed.get("trunk_id") or ""),
                }
        except ValueError:
            logger.debug("[sip] room metadata is not json: {}", metadata[:120])

    name = getattr(room, "name", "") or ""
    if name.startswith(SIP_ROOM_PREFIX):
        candidate = name[len(SIP_ROOM_PREFIX):].split("_")[0].strip()
        if candidate.startswith("+") and candidate[1:].isdigit():
            return {"to": candidate, "from": "", "trunk_id": ""}
    return {}


async def _numbers_from_room(config: Dict[str, Any], room_name: str) -> Dict[str, str]:
    client = api.LiveKitAPI(
        (config.get("url") or "").replace("wss://", "https://").replace("ws://", "http://"),
        config.get("api_key"),
        config.get("api_secret"),
    )
    try:
        for _attempt in range(6):
            found = await client.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            for participant in found.participants:
                numbers = _participant_numbers(participant)
                if numbers["to"]:
                    return numbers
            await asyncio.sleep(0.5)
    except Exception:
        logger.exception("[sip] could not list participants for room {}", room_name)
    finally:
        await client.aclose()
    return {"to": "", "from": "", "trunk_id": ""}


def _participant_numbers(participant) -> Dict[str, str]:
    attributes = dict(getattr(participant, "attributes", {}) or {})
    return {
        "to": attributes.get(SIP_ATTR_CALLED_NUMBER, ""),
        "from": attributes.get(SIP_ATTR_CALLER_NUMBER, ""),
        "trunk_id": attributes.get(SIP_ATTR_TRUNK_ID, ""),
    }


@router.post("/sip/livekit-webhook")
async def livekit_webhook(
    request: Request, background: BackgroundTasks
) -> Dict[str, Any]:
    raw = await request.body()
    verified = _verify(raw, request.headers.get("authorization", ""))
    if verified is None:
        return {"ok": False}
    event, config = verified

    event_name = getattr(event, "event", "")
    room_name = getattr(getattr(event, "room", None), "name", "")
    logger.info("[sip] livekit webhook event={} room={}", event_name, room_name)
    if event_name not in ("participant_joined", "room_started"):
        return {"ok": True}
    if not room_name or get_bot_dispatcher().is_active(room_name):
        return {"ok": True}

    participant_identity = getattr(getattr(event, "participant", None), "identity", "")
    if participant_identity == BOT_IDENTITY:
        return {"ok": True}

    participant = getattr(event, "participant", None)
    numbers = _participant_numbers(participant) if participant is not None else {}
    if not numbers.get("to"):
        numbers = _numbers_from_room_meta(getattr(event, "room", None)) or {}
    if not numbers.get("to"):
        numbers = await _numbers_from_room(config, room_name)
    if not numbers.get("to"):
        logger.warning(
            "[sip] {} without a dialled number room={} attributes={}",
            event_name, room_name, dict(getattr(participant, "attributes", {}) or {}),
        )
        return {"ok": True}

    with get_db_context() as db:
        agent = AgentRunnerService(db).get_agent_by_phone_number(numbers["to"])

    if agent is None:
        logger.warning(
            "[sip] inbound rejected — no agent assigned to {} (room={})", numbers["to"], room_name
        )
        return {"ok": False, "reason": "no_agent_for_number"}

    grant = LiveKitTermination(config).bot_grant(room_name)
    payload = build_handoff_payload(
        room_name=room_name,
        grant=grant,
        agent_id=str(agent.id),
        direction="inbound",
        from_number=numbers["from"],
        to_number=numbers["to"],
        trunk_id=numbers.get("trunk_id") or "",
    )

    logger.info(
        "[sip] inbound routed room={} from={} to={} agent={}",
        room_name, numbers["from"], numbers["to"], agent.id,
    )
    if not get_bot_dispatcher().reserve(room_name):
        return {"ok": True}
    background.add_task(dispatch_call, payload)
    return {"ok": True, "agent_id": str(agent.id), "room": room_name}


@router.post("/sip/status")
async def sip_status(request: Request) -> Dict[str, Any]:
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
