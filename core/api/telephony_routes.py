from xml.sax.saxutils import escape as _xml_escape

from fastapi import APIRouter, Request
from fastapi.responses import Response
from loguru import logger

from core.database.session import get_db_context
from core.utils.telephony import fallback_media_ws_url, pinned_ws_url

router = APIRouter()


async def _resolve_stream(request: Request, tag: str):
    default_ws_url = fallback_media_ws_url(request.url.hostname)

    from_number = ""
    to_number = ""
    try:
        if request.method == "POST":
            form = await request.form()
            from_number = (form.get("From") or "").strip()
            to_number = (form.get("To") or "").strip()
        else:
            from_number = (request.query_params.get("From") or "").strip()
            to_number = (request.query_params.get("To") or "").strip()
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


async def _outbound_answer_xml(request: Request, provider: str, tag: str) -> Response:
    from core.services.call_engines import get_call_engine

    qp = request.query_params
    agent_id = (qp.get("agent_id") or "").strip()
    to_number = (qp.get("to") or "").strip()
    scheduled_call_id = (qp.get("scheduled_call_id") or "").strip()
    if not agent_id:
        logger.warning("[{}] missing agent_id", tag)
        return Response(content=_HANGUP_TWIML, media_type="application/xml")

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
    xml = get_call_engine(provider).generate_twiml(ws_url, params)

    logger.info(
        "[{}] RESPONSE agent={} to={} scheduled_call_id={} pod={} node={} handshake_url={}",
        tag, agent_id, to_number, scheduled_call_id, pod_name, node_name, ws_url,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/twiml/outbound")
@router.get("/twiml/outbound")
async def twiml_outbound(request: Request) -> Response:
    return await _outbound_answer_xml(request, "twilio", "/twiml/outbound")


@router.post("/telnyx/texml/outbound")
@router.get("/telnyx/texml/outbound")
async def telnyx_texml_outbound(request: Request) -> Response:
    return await _outbound_answer_xml(request, "telnyx", "/telnyx/texml/outbound")


async def _outbound_status_callback(request: Request, tag: str) -> Response:
    from core.models.scheduled_call import ScheduledCall
    from core.services.outbound_call_service import OutboundCallService

    scheduled_call_id = (request.query_params.get("scheduled_call_id") or "").strip()
    try:
        form = await request.form()
        form_dict = {k: form.get(k) for k in ("CallSid", "CallStatus", "CallDuration", "To", "From")}
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
