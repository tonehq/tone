from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status
from loguru import logger

from core.database.session import get_db_context
from core.services.sip.inbound import digest_credentials, resolve_inbound_call
from core.utils.telephony import default_media_ws_url, pinned_ws_url
from shared.config import settings

router = APIRouter()


def _authorize(request: Request) -> None:
    expected = (settings.SIP_SBC_WEBHOOK_TOKEN or "").strip()
    if not expected:
        return
    presented = (request.headers.get("authorization") or "").strip()
    if presented.lower().startswith("bearer "):
        presented = presented[7:].strip()
    if presented != expected:
        logger.warning("[sip] control-plane request rejected — bad token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def _source_ip(request: Request, payload: Dict[str, Any]) -> str:
    return (
        (payload.get("source_ip") or "").strip()
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "")
    )


@router.post("/sip/inbound")
async def sip_inbound(request: Request) -> Dict[str, Any]:
    _authorize(request)
    try:
        payload = await request.json()
    except Exception:
        logger.exception("[sip] /sip/inbound received a malformed body")
        return {"allowed": False, "reason": "bad_request"}

    to_number = (payload.get("to") or "").strip()
    from_number = (payload.get("from") or "").strip()
    source_ip = _source_ip(request, payload)
    auth_username = (payload.get("auth_username") or "").strip()
    trunk_id = (payload.get("trunk_id") or "").strip()

    default_ws_url = default_media_ws_url(settings.BASE_CALL_URL) or (
        f"wss://{request.url.hostname or 'localhost'}/ws"
    )
    ws_url, pod_name, _, node_name = pinned_ws_url(default_ws_url, "/sip/inbound")

    logger.info(
        "[sip] /sip/inbound from={} to={} source_ip={} pod={} node={}",
        from_number, to_number, source_ip, pod_name, node_name,
    )
    with get_db_context() as db:
        decision = resolve_inbound_call(
            db,
            to_number=to_number,
            source_ip=source_ip,
            auth_username=auth_username,
            trunk_id=trunk_id,
            media_ws_url=ws_url,
        )
    return decision


@router.post("/sip/credentials")
async def sip_credentials(request: Request) -> Dict[str, Any]:
    _authorize(request)
    try:
        payload = await request.json()
    except Exception:
        logger.exception("[sip] /sip/credentials received a malformed body")
        return {}

    auth_username = (payload.get("auth_username") or "").strip()
    with get_db_context() as db:
        credentials = digest_credentials(db, auth_username)
    if not credentials:
        logger.warning("[sip] no digest credentials for username={}", auth_username)
    return credentials


@router.post("/sip/status")
async def sip_status(request: Request) -> Dict[str, Any]:
    _authorize(request)
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
            sc = (
                db.query(ScheduledCall)
                .filter(ScheduledCall.id == scheduled_call_id)
                .first()
            )
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
