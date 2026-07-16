"""Twilio call engine — outbound origination, hangup, status, and TwiML.

Mirrors tone-test's ``TwilioCallEngine`` but origination-only (see
``call_engines.base``). Credentials are per-org, decrypted from the org's Twilio
channel via ``get_twilio_credentials`` (havana stores them in the DB, not env).
"""

from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode
from xml.sax.saxutils import escape as _xml_escape

from loguru import logger
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from core.services.call_engines.base import CallEngine, CallInfo
from core.services.transport.telephony_credentials import get_twilio_credentials

# Twilio's REST default is 60s; we bound ringing tighter so no-answer resolves sooner.
DEFAULT_RING_TIMEOUT = 45

# Twilio only lets StatusCallbackEvent subscribe to these four; terminal outcomes
# (busy/no-answer/failed/canceled) arrive as CallStatus values inside "completed".
STATUS_CALLBACK_EVENTS = ["initiated", "ringing", "answered", "completed"]


class TwilioCallEngine(CallEngine):
    def __init__(self, org_id=None):
        self._org_id = org_id
        self._client: Optional[Client] = None

    @property
    def provider_name(self) -> str:
        return "twilio"

    def _get_client(self) -> Client:
        if self._client is None:
            creds = get_twilio_credentials(org_id=self._org_id)
            account_sid = creds.get("account_sid")
            auth_token = creds.get("auth_token")
            if not account_sid or not auth_token:
                raise ValueError(
                    "No Twilio credentials configured for this organization. "
                    "Add a Twilio channel with account_sid + auth_token before dialing."
                )
            self._client = Client(account_sid, auth_token)
        return self._client

    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        agent_id: str,
        callback_base_url: str,
        scheduled_call_id: Optional[str] = None,
    ) -> CallInfo:
        """Place an outbound call. The routing context (agent_id/from/to/direction and,
        for scheduled calls, scheduled_call_id) rides in the TwiML URL's query string, so
        the /twiml/outbound endpoint needs no pre-created DB row. A status callback is
        set only for scheduled calls (to update the scheduled_calls row); immediate calls
        surface purely as a call log when they connect."""
        base = (callback_base_url or "").rstrip("/")
        if not base:
            raise ValueError(
                "BASE_CALL_URL is not set — Twilio needs a public callback base URL "
                "to fetch outbound TwiML and post status callbacks."
            )
        query = {"agent_id": str(agent_id), "direction": "outbound", "from": from_number, "to": to_number}
        if scheduled_call_id:
            query["scheduled_call_id"] = str(scheduled_call_id)
        twiml_url = f"{base}/twiml/outbound?{urlencode(query)}"

        create_kwargs: Dict[str, Any] = dict(
            to=to_number,
            from_=from_number,
            url=twiml_url,
            method="POST",
            timeout=DEFAULT_RING_TIMEOUT,
        )
        if scheduled_call_id:
            create_kwargs.update(
                status_callback=f"{base}/twilio/outbound-status?scheduled_call_id={quote(str(scheduled_call_id))}",
                status_callback_event=STATUS_CALLBACK_EVENTS,
                status_callback_method="POST",
            )

        session = scheduled_call_id or agent_id
        logger.info(
            "[outbound] dialing agent={} from={} to={} scheduled_call_id={} twiml_url={}",
            agent_id, from_number, to_number, scheduled_call_id, twiml_url,
        )
        call = self._get_client().calls.create(**create_kwargs)
        status = getattr(call, "status", None) or "queued"
        logger.info(
            "[outbound] twilio call created sid={} status={} scheduled_call_id={}",
            call.sid, status, scheduled_call_id,
        )
        return CallInfo(call_id=call.sid, session_id=str(session), status=status, provider="twilio")

    def end_call(self, call_id: str) -> bool:
        try:
            self._get_client().calls(call_id).update(status="completed")
            logger.info("[outbound] end_call hung up sid={}", call_id)
            return True
        except TwilioRestException as e:
            logger.warning("[outbound] end_call failed sid={} err={}", call_id, e)
            return False

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        call = self._get_client().calls(call_id).fetch()
        return {
            "status": call.status,
            "duration": call.duration,
            "price": call.price,
            "answered_by": getattr(call, "answered_by", None),
        }

    def generate_twiml(self, ws_url: str, params: Dict[str, str]) -> str:
        param_xml = "".join(
            f'<Parameter name="{_xml_escape(str(name))}" value="{_xml_escape(str(value))}" />'
            for name, value in (params or {}).items()
            if value is not None and value != ""
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Connect>"
            f'<Stream url="{_xml_escape(ws_url)}">{param_xml}</Stream>'
            "</Connect>"
            "</Response>"
        )
