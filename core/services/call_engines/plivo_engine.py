from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode
from xml.sax.saxutils import escape as _xml_escape

import requests
from loguru import logger

from core.services.call_engines.base import TERMINAL_CALL_STATUSES, CallEngine, CallInfo
from core.services.transport.telephony_credentials import get_plivo_credentials

PLIVO_API_BASE = "https://api.plivo.com/v1/Account"
DEFAULT_RING_TIMEOUT = 45
HTTP_TIMEOUT = 15
STREAM_CONTENT_TYPE = "audio/x-mulaw;rate=8000"
_STATUS_MAP = {
    "queued": "queued",
    "ringing": "ringing",
    "in-progress": "in-progress",
    "completed": "completed",
    "busy": "busy",
    "no-answer": "no-answer",
    "failed": "failed",
    "cancel": "canceled",
    "canceled": "canceled",
}


class PlivoCallEngine(CallEngine):
    def __init__(self, org_id=None):
        self._org_id = org_id
        self._creds: Optional[Dict[str, str]] = None

    @property
    def provider_name(self) -> str:
        return "plivo"

    def _credentials(self) -> Dict[str, str]:
        if self._creds is None:
            creds = get_plivo_credentials(org_id=self._org_id)
            if not creds.get("auth_id") or not creds.get("auth_token"):
                raise ValueError(
                    "No Plivo credentials configured for this organization. "
                    "Add a Plivo channel with auth_id + auth_token before dialing."
                )
            self._creds = creds
        return self._creds

    def _auth(self):
        creds = self._credentials()
        return (creds["auth_id"], creds["auth_token"])

    def _url(self, path: str) -> str:
        return f"{PLIVO_API_BASE}/{quote(self._credentials()['auth_id'])}/{path}"

    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        agent_id: str,
        callback_base_url: str,
        scheduled_call_id: Optional[str] = None,
    ) -> CallInfo:
        base = (callback_base_url or "").rstrip("/")
        if not base:
            raise ValueError(
                "BASE_CALL_URL is not set — Plivo needs a public callback base URL "
                "to fetch the outbound answer XML and post status callbacks."
            )
        query = {"agent_id": str(agent_id), "direction": "outbound", "from": from_number, "to": to_number}
        if scheduled_call_id:
            query["scheduled_call_id"] = str(scheduled_call_id)
        payload: Dict[str, Any] = {
            "from": from_number,
            "to": to_number,
            "answer_url": f"{base}/plivo/outbound?{urlencode(query)}",
            "answer_method": "POST",
            "ring_timeout": DEFAULT_RING_TIMEOUT,
        }
        if scheduled_call_id:
            payload["hangup_url"] = f"{base}/plivo/outbound-status?scheduled_call_id={quote(str(scheduled_call_id))}"
            payload["hangup_method"] = "POST"
        session = scheduled_call_id or agent_id
        logger.info(
            "[outbound] dialing agent={} from={} to={} scheduled_call_id={} answer_url={}",
            agent_id, from_number, to_number, scheduled_call_id, payload["answer_url"],
        )
        try:
            response = requests.post(self._url("Call/"), json=payload, auth=self._auth(), timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            logger.exception(
                "[outbound] plivo call create failed agent={} to={} scheduled_call_id={}",
                agent_id, to_number, scheduled_call_id,
            )
            raise
        request_uuid = data.get("request_uuid") or ""
        logger.info(
            "[outbound] plivo call created request_uuid={} scheduled_call_id={}", request_uuid, scheduled_call_id,
        )
        return CallInfo(call_id=request_uuid, session_id=str(session), status="queued", provider="plivo")

    def end_call(self, call_id: str) -> bool:
        for path in (f"Call/{quote(str(call_id))}/", f"Request/{quote(str(call_id))}/"):
            try:
                response = requests.delete(self._url(path), auth=self._auth(), timeout=HTTP_TIMEOUT)
            except requests.RequestException:
                logger.exception("[outbound] end_call request failed id={}", call_id)
                return False
            if response.status_code in (200, 204):
                logger.info("[outbound] end_call hung up id={}", call_id)
                return True
            if response.status_code != 404:
                logger.error(
                    "[outbound] end_call failed id={} status={} body={}",
                    call_id, response.status_code, response.text[:200],
                )
                return False
        try:
            status = self.get_call_status(call_id).get("status")
        except Exception:
            logger.exception("[outbound] end_call status lookup failed id={}", call_id)
            return False
        if status in TERMINAL_CALL_STATUSES:
            logger.debug("[outbound] end_call: call already {} id={}", status, call_id)
            return True
        logger.error("[outbound] end_call: call not found and not terminal id={} status={}", call_id, status)
        return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        url = self._url(f"Call/{quote(str(call_id))}/")
        response = requests.get(url, params={"status": "live"}, auth=self._auth(), timeout=HTTP_TIMEOUT)
        if response.status_code == 404:
            response = requests.get(url, auth=self._auth(), timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        raw = (data.get("call_status") or data.get("call_state") or "").lower()
        return {
            "status": _STATUS_MAP.get(raw, raw),
            "duration": data.get("call_duration") or data.get("bill_duration"),
            "price": data.get("total_amount"),
            "answered_by": None,
        }

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        query = {name: value for name, value in params.items() if value not in (None, "")}
        stream_url = f"{ws_url}?{urlencode(query)}" if query else ws_url
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Stream bidirectional="true" keepCallAlive="true" contentType="{STREAM_CONTENT_TYPE}">'
            f"{_xml_escape(stream_url)}"
            "</Stream>"
            "</Response>"
        )
