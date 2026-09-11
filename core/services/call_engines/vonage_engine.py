import json
import time
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode
from uuid import uuid4

import jwt
import requests
from loguru import logger

from core.services.call_engines.base import TERMINAL_CALL_STATUSES, CallEngine, CallInfo
from core.services.transport.telephony_credentials import get_vonage_credentials
from core.services.transport.vonage import VONAGE_CONTENT_TYPE
from core.utils.telephony import to_e164

VONAGE_CALLS_URL = "https://api.nexmo.com/v1/calls"
DEFAULT_RING_TIMEOUT = 45
HTTP_TIMEOUT = 15
JWT_TTL_SECONDS = 900
_STATUS_MAP = {
    "started": "queued",
    "ringing": "ringing",
    "answered": "in-progress",
    "completed": "completed",
    "busy": "busy",
    "cancelled": "canceled",
    "unanswered": "no-answer",
    "timeout": "no-answer",
    "failed": "failed",
    "rejected": "failed",
}


def vonage_number(number: str) -> str:
    return "".join(ch for ch in (number or "") if ch.isdigit())


class VonageCallEngine(CallEngine):
    answer_media_type = "application/json"
    hangup_answer = "[]"

    def __init__(self, org_id=None):
        self._org_id = org_id
        self._creds: Optional[Dict[str, str]] = None

    @property
    def provider_name(self) -> str:
        return "vonage"

    def _credentials(self) -> Dict[str, str]:
        if self._creds is None:
            creds = get_vonage_credentials(org_id=self._org_id)
            if not creds:
                raise ValueError(
                    "No Vonage credentials configured for this organization. "
                    "Add a Vonage channel with application_id + private_key before dialing."
                )
            self._creds = creds
        return self._creds

    def _headers(self) -> Dict[str, str]:
        creds = self._credentials()
        now = int(time.time())
        token = jwt.encode(
            {"application_id": creds["application_id"], "iat": now, "exp": now + JWT_TTL_SECONDS, "jti": uuid4().hex},
            creds["private_key"],
            algorithm="RS256",
        )
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _call_url(self, call_id: str) -> str:
        return f"{VONAGE_CALLS_URL}/{quote(str(call_id))}"

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
                "BASE_CALL_URL is not set — Vonage needs a public callback base URL "
                "for the answer and event webhooks."
            )
        query = {"agent_id": str(agent_id), "direction": "outbound", "from": from_number, "to": to_number}
        events_query = {}
        if scheduled_call_id:
            query["scheduled_call_id"] = str(scheduled_call_id)
            events_query["scheduled_call_id"] = str(scheduled_call_id)
        event_url = f"{base}/vonage/events" + (f"?{urlencode(events_query)}" if events_query else "")
        payload: Dict[str, Any] = {
            "to": [{"type": "phone", "number": vonage_number(to_number)}],
            "from": {"type": "phone", "number": vonage_number(from_number)},
            "answer_url": [f"{base}/vonage/answer?{urlencode(query)}"],
            "answer_method": "GET",
            "event_url": [event_url],
            "event_method": "POST",
            "ringing_timer": DEFAULT_RING_TIMEOUT,
        }
        session = scheduled_call_id or agent_id
        logger.info(
            "[outbound] dialing agent={} from={} to={} scheduled_call_id={} answer_url={}",
            agent_id, from_number, to_number, scheduled_call_id, payload["answer_url"][0],
        )
        try:
            response = requests.post(VONAGE_CALLS_URL, json=payload, headers=self._headers(), timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            body = " ".join((getattr(getattr(exc, "response", None), "text", None) or "")[:300].split())
            logger.exception(
                "[outbound] vonage call create failed agent={} to={} scheduled_call_id={} body={}",
                agent_id, to_number, scheduled_call_id, body,
            )
            raise
        call_id = data.get("uuid") or ""
        status = _STATUS_MAP.get((data.get("status") or "").lower(), "queued")
        logger.info(
            "[outbound] vonage call created uuid={} status={} scheduled_call_id={}", call_id, status, scheduled_call_id,
        )
        return CallInfo(call_id=call_id, session_id=str(session), status=status, provider="vonage")

    def end_call(self, call_id: str) -> bool:
        try:
            response = requests.put(
                self._call_url(call_id), json={"action": "hangup"}, headers=self._headers(), timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            logger.exception("[outbound] end_call request failed uuid={}", call_id)
            return False
        if response.status_code in (200, 204):
            logger.info("[outbound] end_call hung up uuid={}", call_id)
            return True
        if response.status_code == 404:
            logger.debug("[outbound] end_call: call already gone uuid={}", call_id)
            return True
        try:
            status = self.get_call_status(call_id).get("status")
        except requests.HTTPError as exc:
            if getattr(exc.response, "status_code", None) == 404:
                logger.debug("[outbound] end_call: call already gone uuid={}", call_id)
                return True
            logger.exception("[outbound] end_call failed uuid={} http={}", call_id, response.status_code)
            return False
        except Exception:
            logger.exception("[outbound] end_call failed uuid={} http={}", call_id, response.status_code)
            return False
        if status in TERMINAL_CALL_STATUSES:
            logger.debug("[outbound] end_call: call already {} uuid={}", status, call_id)
            return True
        logger.error("[outbound] end_call failed uuid={} http={} status={}", call_id, response.status_code, status)
        return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        response = requests.get(self._call_url(call_id), headers=self._headers(), timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        raw = (data.get("status") or "").lower()
        return {
            "status": _STATUS_MAP.get(raw, raw),
            "duration": data.get("duration"),
            "price": data.get("price"),
            "answered_by": None,
        }

    def transfer_call(
        self, call_id: str, sip_address: str, headers: Optional[Dict[str, str]] = None
    ) -> bool:
        if sip_address.lower().startswith("sip:"):
            endpoint: Dict[str, Any] = {"type": "sip", "uri": sip_address}
            if headers:
                endpoint["headers"] = headers
        else:
            endpoint = {"type": "phone", "number": vonage_number(sip_address)}
        ncco = [{"action": "connect", "endpoint": [endpoint]}]
        try:
            response = requests.put(
                self._call_url(call_id),
                json={"action": "transfer", "destination": {"type": "ncco", "ncco": ncco}},
                headers=self._headers(),
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            logger.exception("[outbound] transfer request failed uuid={}", call_id)
            return False
        if response.status_code in (200, 204):
            return True
        logger.error(
            "[outbound] transfer failed uuid={} http={} body={}", call_id, response.status_code, response.text[:200],
        )
        return False

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        query = {"provider": self.provider_name}
        query.update({name: value for name, value in params.items() if value not in (None, "")})
        for name in ("from", "to"):
            if query.get(name):
                query[name] = to_e164(query[name])
        ncco = [
            {
                "action": "connect",
                "endpoint": [
                    {
                        "type": "websocket",
                        "uri": f"{ws_url}?{urlencode(query)}",
                        "content-type": VONAGE_CONTENT_TYPE,
                    }
                ],
            }
        ]
        return json.dumps(ncco)
