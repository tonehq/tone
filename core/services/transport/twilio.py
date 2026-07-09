"""Twilio call engine."""

import aiohttp
from loguru import logger
from pipecat.serializers.twilio import TwilioFrameSerializer

from core.services.transport.base import TelephonyProvider
from core.services.transport.telephony_credentials import get_twilio_credentials


async def get_call_info(transport_type: str, call_sid: str, org_id=None) -> dict:
    """Fetch call information from the telephony provider's REST API.

    Currently only Twilio is supported for call info lookup via REST API.
    Telnyx and Exotel provide from/to in the WebSocket start message directly.
    Plivo call info lookup is not implemented yet.

    Args:
        transport_type: The telephony provider type ("twilio", "telnyx", "exotel", "plivo").
        call_sid: The provider-specific call ID.

    Returns:
        Dictionary containing call information including from_number, to_number, etc.
    """
    if transport_type != "twilio":
        return {}

    twilio_creds = get_twilio_credentials(org_id=org_id)
    account_sid = twilio_creds.get("account_sid")
    auth_token = twilio_creds.get("auth_token")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials in DB, cannot fetch call info")
        return {}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"

    try:
        # Use HTTP Basic Auth with aiohttp
        auth = aiohttp.BasicAuth(account_sid, auth_token)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Twilio API error ({response.status}): {error_text}")
                    return {}

                data = await response.json()

                call_info = {
                    "from_number": data.get("from"),
                    "to_number": data.get("to"),
                }

                return call_info

    except Exception as e:
        logger.error(f"Error fetching call info from Twilio: {e}")
        return {}


class TwilioTransport(TelephonyProvider):
    transport_type = "twilio"

    def create_serializer(self, call_data: dict):
        # Reuse credentials cached by AgentRunnerService if available
        twilio_creds = call_data.get("_twilio_creds") or get_twilio_credentials(
            org_id=call_data.get("_org_id"),
            channel_id=call_data.get("_channel_id"),
        )
        return TwilioFrameSerializer(
            stream_sid=call_data["stream_id"],
            call_sid=call_data["call_id"],
            account_sid=twilio_creds.get("account_sid", ""),
            auth_token=twilio_creds.get("auth_token", ""),
        )

    async def resolve_from_to(self, call_data: dict) -> None:
        # Twilio passes from/to in the WS start message's <Parameter> tags
        # (call_data["body"]); use those first and only fall back to the REST API when
        # absent (the API 404s for test calls whose SID isn't a real Twilio call).
        if call_data.get("from"):
            return
        twilio_body = call_data.get("body") or {}
        param_from = (twilio_body.get("from") or "").strip()
        param_to = (twilio_body.get("to") or "").strip()
        if param_from or param_to:
            call_data["from"] = param_from
            call_data["to"] = param_to
            logger.info("Twilio from/to resolved from <Parameter> tags (skipped API call)")
        else:
            call_info = await get_call_info(
                "twilio", call_data.get("call_id", ""), org_id=call_data.get("_org_id")
            )
            if call_info:
                call_data["from"] = call_info.get("from_number", "")
                call_data["to"] = call_info.get("to_number", "")
