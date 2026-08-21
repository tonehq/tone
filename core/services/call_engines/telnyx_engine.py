from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode
from xml.sax.saxutils import escape as _xml_escape

import requests
from loguru import logger

from core.services.call_engines.base import CallEngine, CallInfo
from core.services.transport.telephony_credentials import get_telnyx_credentials

TEXML_BASE_URL = "https://api.telnyx.com/v2/texml"

DEFAULT_RING_TIMEOUT = 45

HTTP_TIMEOUT = 15

STATUS_CALLBACK_EVENTS = ["initiated", "ringing", "answered", "completed"]


class TelnyxCallEngine(CallEngine):
    def __init__(self, org_id=None):
        self._org_id = org_id
        self._creds: Optional[Dict[str, str]] = None

    @property
    def provider_name(self) -> str:
        return "telnyx"

    def _credentials(self) -> Dict[str, str]:
        if self._creds is None:
            creds = get_telnyx_credentials(org_id=self._org_id)
            if not creds:
                raise ValueError(
                    "No Telnyx credentials configured for this organization. "
                    "Add a Telnyx channel with api_key + account_sid before dialing."
                )
            self._creds = creds
        return self._creds

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._credentials()['api_key']}"}

    def _calls_url(self, call_id: Optional[str] = None) -> str:
        account_sid = self._credentials()["account_sid"]
        url = f"{TEXML_BASE_URL}/Accounts/{quote(str(account_sid))}/Calls"
        return f"{url}/{quote(str(call_id))}" if call_id else url

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
                "BASE_CALL_URL is not set — Telnyx needs a public callback base URL "
                "to fetch outbound TeXML and post status callbacks."
            )
        query = {"agent_id": str(agent_id), "direction": "outbound", "from": from_number, "to": to_number}
        if scheduled_call_id:
            query["scheduled_call_id"] = str(scheduled_call_id)
        texml_url = f"{base}/telnyx/texml/outbound?{urlencode(query)}"

        payload: Dict[str, Any] = {
            "To": to_number,
            "From": from_number,
            "Url": texml_url,
            "Method": "POST",
            "Timeout": DEFAULT_RING_TIMEOUT,
        }
        application_sid = self._credentials().get("application_sid")
        if application_sid:
            payload["ApplicationSid"] = application_sid
        if scheduled_call_id:
            payload.update(
                StatusCallback=f"{base}/telnyx/outbound-status?scheduled_call_id={quote(str(scheduled_call_id))}",
                StatusCallbackEvent=STATUS_CALLBACK_EVENTS,
                StatusCallbackMethod="POST",
            )

        session = scheduled_call_id or agent_id
        logger.info(
            "[outbound] dialing agent={} from={} to={} scheduled_call_id={} texml_url={}",
            agent_id, from_number, to_number, scheduled_call_id, texml_url,
        )
        try:
            response = requests.post(
                self._calls_url(), headers=self._headers(), data=payload, timeout=HTTP_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            logger.exception(
                "[outbound] telnyx call create failed agent={} to={} scheduled_call_id={}",
                agent_id, to_number, scheduled_call_id,
            )
            raise

        call_id = data.get("sid") or data.get("call_sid") or ""
        status = data.get("status") or "queued"
        logger.info(
            "[outbound] telnyx call created sid={} status={} scheduled_call_id={}",
            call_id, status, scheduled_call_id,
        )
        return CallInfo(call_id=call_id, session_id=str(session), status=status, provider="telnyx")

    def end_call(self, call_id: str) -> bool:
        try:
            response = requests.post(
                self._calls_url(call_id),
                headers=self._headers(),
                data={"Status": "completed"},
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            logger.info("[outbound] end_call hung up sid={}", call_id)
            return True
        except Exception:
            logger.exception("[outbound] end_call failed sid={}", call_id)
            return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        response = requests.get(self._calls_url(call_id), headers=self._headers(), timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return {
            "status": data.get("status"),
            "duration": data.get("duration"),
            "price": data.get("price"),
            "answered_by": data.get("answered_by"),
        }

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        query = {
            str(name): str(value)
            for name, value in (params or {}).items()
            if value is not None and value != ""
        }
        stream_url = ws_url
        if query:
            separator = "&" if "?" in ws_url else "?"
            stream_url = f"{ws_url}{separator}{urlencode(query)}"
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Connect>"
            f'<Stream url="{_xml_escape(stream_url)}" bidirectionalMode="rtp"></Stream>'
            "</Connect>"
            '<Pause length="40"/>'
            "</Response>"
        )
