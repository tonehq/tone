from xml.sax.saxutils import escape as _xml_escape

from typing import Any, Awaitable, Callable, Dict

from fastapi import APIRouter, Request
from fastapi.responses import Response
from loguru import logger

from core.database.session import get_db_context
from core.utils.telephony import fallback_media_ws_url, pinned_ws_url, to_e164

router = APIRouter()


async def _resolve_stream(request: Request, tag: str):
    default_ws_url = fallback_media_ws_url(request.url.hostname)

    from_number = ""
    to_number = ""
    try:
        source = await request.form() if request.method == "POST" else request.query_params
        from_number = (source.get("From") or source.get("from") or "").strip()
        to_number = (source.get("To") or source.get("to") or "").strip()
    except Exception:
        # Non-fatal: a malformed form/query just means no from/to to log; the
        # call still proceeds. Capture the traceback rather than swallowing silently.
        logger.exception("[{}] failed to parse From/To from request", tag)

    ws_url, pod_name, pod_ordinal, node_name = pinned_ws_url(default_ws_url, tag)

    logger.info(
        "[{}] REQUEST from={} to={} pod={} ordinal={} node={} pod_url={}",
        tag, from_number, to_number, pod_name, pod_ordinal, node_name, ws_url,
    )
    return ws_url, from_number, to_number, pod_name, node_name


@router.post("/twiml")
@router.get("/twiml")
async def twiml(request: Request) -> Response:
    try:
        ws_url, from_number, to_number, pod_name, node_name = await _resolve_stream(request, "/twiml")

        params_xml = ""
        if from_number:
            params_xml += f'<Parameter name="from" value="{_xml_escape(from_number)}" />'
        if to_number:
            params_xml += f'<Parameter name="to" value="{_xml_escape(to_number)}" />'

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Connect>'
            f'<Stream url="{ws_url}">{params_xml}</Stream>'
            '</Connect>'
            '</Response>'
        )

        logger.info(
            "[inbound] /twiml RESPONSE from={} to={} pod={} node={} handshake_url={}",
            from_number, to_number, pod_name, node_name, ws_url,
        )
        return Response(content=xml, media_type="application/xml")
    except Exception:
        logger.exception("[inbound] /twiml failed to build stream response — returning hangup")
        return Response(content=_HANGUP_TWIML, media_type="application/xml")


@router.post("/telnyx/texml")
@router.get("/telnyx/texml")
async def telnyx_texml(request: Request) -> Response:
    try:
        ws_url, from_number, to_number, pod_name, node_name = await _resolve_stream(request, "/telnyx/texml")

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Connect>'
            f'<Stream url="{ws_url}" bidirectionalMode="rtp"></Stream>'
            '</Connect>'
            '<Pause length="40"/>'
            '</Response>'
        )

        logger.info(
            "[inbound] /telnyx/texml RESPONSE from={} to={} pod={} node={} handshake_url={}",
            from_number, to_number, pod_name, node_name, ws_url,
        )
        return Response(content=xml, media_type="application/xml")
    except Exception:
        logger.exception("[inbound] /telnyx/texml failed to build stream response — returning hangup")
        return Response(content=_HANGUP_TWIML, media_type="application/xml")


_HANGUP_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'


async def _outbound_answer_xml(request: Request, provider: str, tag: str, call_id: str = "") -> Response:
    from core.services.call_engines import get_call_engine

    engine = get_call_engine(provider)
    qp = request.query_params
    agent_id = (qp.get("agent_id") or "").strip()
    to_number = (qp.get("to") or "").strip()
    scheduled_call_id = (qp.get("scheduled_call_id") or "").strip()
    if not agent_id:
        logger.warning("[{}] missing agent_id", tag)
        return Response(content=engine.hangup_answer, media_type=engine.answer_media_type)

    default_ws_url = fallback_media_ws_url(request.url.hostname)
    ws_url, pod_name, pod_ordinal, node_name = pinned_ws_url(default_ws_url, tag)
    params = {
        "from": (qp.get("from") or "").strip(),
        "to": to_number,
        "agent_id": agent_id,
        "direction": "outbound",
    }
    if scheduled_call_id:
        params["scheduled_call_id"] = scheduled_call_id
    if call_id:
        params["call_id"] = call_id.strip()
    answer = engine.generate_twiml(ws_url, params)

    logger.info(
        "[{}] RESPONSE agent={} to={} scheduled_call_id={} pod={} node={} handshake_url={}",
        tag, agent_id, to_number, scheduled_call_id, pod_name, node_name, ws_url,
    )
    return Response(content=answer, media_type=engine.answer_media_type)


@router.post("/twiml/outbound")
@router.get("/twiml/outbound")
async def twiml_outbound(request: Request) -> Response:
    return await _outbound_answer_xml(request, "twilio", "/twiml/outbound")


@router.post("/telnyx/texml/outbound")
@router.get("/telnyx/texml/outbound")
async def telnyx_texml_outbound(request: Request) -> Response:
    return await _outbound_answer_xml(request, "telnyx", "/telnyx/texml/outbound")


async def _twiml_status_fields(request: Request) -> Dict[str, Any]:
    form = await request.form()
    return {k: form.get(k) for k in ("CallSid", "CallStatus", "CallDuration", "To", "From")}


async def _plivo_status_fields(request: Request) -> Dict[str, Any]:
    form = await request.form()
    return {
        "CallSid": form.get("RequestUUID") or form.get("CallUUID"),
        "CallStatus": form.get("CallStatus"),
        "CallDuration": form.get("Duration"),
        "To": to_e164(form.get("To")),
        "From": to_e164(form.get("From")),
    }


async def _vonage_status_fields(request: Request) -> Dict[str, Any]:
    event = await request.json()
    return {
        "CallSid": event.get("uuid"),
        "CallStatus": event.get("status"),
        "CallDuration": event.get("duration"),
        "To": to_e164(event.get("to")),
        "From": to_e164(event.get("from")),
    }


async def _outbound_status_callback(
    request: Request,
    tag: str,
    fields: Callable[[Request], Awaitable[Dict[str, Any]]] = _twiml_status_fields,
) -> Response:
    from core.models.scheduled_call import ScheduledCall
    from core.services.outbound_call_service import OutboundCallService

    scheduled_call_id = (request.query_params.get("scheduled_call_id") or "").strip()
    try:
        form_dict = await fields(request)
        logger.info(
            "[{}] scheduled_call_id={} sid={} status={}",
            tag, scheduled_call_id, form_dict.get("CallSid"), form_dict.get("CallStatus"),
        )
        if scheduled_call_id:
            with get_db_context() as db:
                sc = db.query(ScheduledCall).filter(ScheduledCall.id == scheduled_call_id).first()
                if sc is not None:
                    OutboundCallService(db, org_id=sc.organization_id).handle_status_callback(
                        scheduled_call_id, form_dict
                    )
    except Exception:  # noqa: BLE001 — never surface errors to the provider
        logger.exception("[{}] error scheduled_call_id={}", tag, scheduled_call_id)

    return Response(status_code=204)


@router.post("/twilio/outbound-status")
async def twilio_outbound_status(request: Request) -> Response:
    return await _outbound_status_callback(request, "/twilio/outbound-status")


@router.post("/telnyx/outbound-status")
async def telnyx_outbound_status(request: Request) -> Response:
    return await _outbound_status_callback(request, "/telnyx/outbound-status")


async def _inbound_answer(request: Request, provider: str, tag: str) -> Response:
    from core.services.call_engines import get_call_engine

    engine = get_call_engine(provider)
    try:
        ws_url, from_number, to_number, pod_name, node_name = await _resolve_stream(request, tag)
        params = {"from": from_number, "to": to_number}
        call_id = (request.query_params.get("uuid") or "").strip()
        if call_id:
            params["call_id"] = call_id
        answer = engine.generate_twiml(ws_url, params)
        logger.info(
            "[{}] RESPONSE from={} to={} call_id={} pod={} node={} handshake_url={}",
            tag, from_number, to_number, call_id, pod_name, node_name, ws_url,
        )
        return Response(content=answer, media_type=engine.answer_media_type)
    except Exception:
        logger.exception("[{}] failed to build stream response — returning hangup", tag)
        return Response(content=engine.hangup_answer, media_type=engine.answer_media_type)


@router.post("/plivo/answer")
@router.get("/plivo/answer")
async def plivo_answer(request: Request) -> Response:
    return await _inbound_answer(request, "plivo", "/plivo/answer")


@router.post("/plivo/outbound")
@router.get("/plivo/outbound")
async def plivo_outbound(request: Request) -> Response:
    return await _outbound_answer_xml(request, "plivo", "/plivo/outbound")


@router.post("/plivo/outbound-status")
async def plivo_outbound_status(request: Request) -> Response:
    return await _outbound_status_callback(request, "/plivo/outbound-status", _plivo_status_fields)


@router.post("/vonage/answer")
@router.get("/vonage/answer")
async def vonage_answer(request: Request) -> Response:
    if (request.query_params.get("agent_id") or "").strip():
        return await _outbound_answer_xml(
            request, "vonage", "/vonage/answer", request.query_params.get("uuid") or ""
        )
    return await _inbound_answer(request, "vonage", "/vonage/answer")


@router.post("/vonage/events")
async def vonage_events(request: Request) -> Response:
    return await _outbound_status_callback(request, "/vonage/events", _vonage_status_fields)
