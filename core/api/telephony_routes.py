from xml.sax.saxutils import escape as _xml_escape

from fastapi import APIRouter, Request
from fastapi.responses import Response
from loguru import logger

from core.database.session import get_db_context
from core.services.pod_picker import PodPicker
from shared.config import settings

router = APIRouter()


async def _resolve_stream(request: Request, tag: str):
    host = request.url.hostname or "localhost"
    ws_url = f"wss://{host}/ws"

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
        pass

    pod_name = None
    pod_ordinal = None
    node_name = None
    if settings.POD_PINNING_ENABLED:
        try:
            pinned_url = None
            with get_db_context() as db:
                picker = PodPicker(db)
                pod = picker.pick()
                pinned_url = picker.url_for(pod)
                if pod is not None:
                    pod_name = pod.name
                    pod_ordinal = pod.ordinal
                    node_name = pod.node.name if pod.node is not None else None
            if pinned_url:
                ws_url = pinned_url
        except Exception as exc:
            logger.warning("[{}] pod pinning failed, falling back to /ws: {}", tag, exc)

    logger.info(
        "[{}] REQUEST from={} to={} pod={} ordinal={} node={} pod_url={}",
        tag, from_number, to_number, pod_name, pod_ordinal, node_name, ws_url,
    )
    return ws_url, from_number, to_number, pod_name, node_name


@router.post("/twiml")
@router.get("/twiml")
async def twiml(request: Request) -> Response:
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
        "[/twiml] RESPONSE from={} to={} pod={} node={} handshake_url={}",
        from_number, to_number, pod_name, node_name, ws_url,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/exotel/applet")
@router.get("/exotel/applet")
async def exotel_applet(request: Request) -> Response:
    ws_url, from_number, to_number, pod_name, node_name = await _resolve_stream(request, "/exotel/applet")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'<Stream url="{ws_url}"/>'
        '</Response>'
    )

    logger.info(
        "[/exotel/applet] RESPONSE from={} to={} pod={} node={} handshake_url={}",
        from_number, to_number, pod_name, node_name, ws_url,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/telnyx/texml")
@router.get("/telnyx/texml")
async def telnyx_texml(request: Request) -> Response:
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
        "[/telnyx/texml] RESPONSE from={} to={} pod={} node={} handshake_url={}",
        from_number, to_number, pod_name, node_name, ws_url,
    )
    return Response(content=xml, media_type="application/xml")
