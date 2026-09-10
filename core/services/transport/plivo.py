"""Plivo call engine."""
import aiohttp
from loguru import logger
from pipecat.serializers.plivo import PlivoFrameSerializer

from core.services.transport.base import TelephonyProvider
from core.services.transport.telephony_credentials import get_plivo_credentials
from core.utils.telephony import to_e164

PLIVO_API_BASE = "https://api.plivo.com/v1/Account"


async def get_plivo_call_info(call_uuid: str, org_id=None) -> dict:
    creds = get_plivo_credentials(org_id=org_id)
    auth_id = creds.get("auth_id")
    auth_token = creds.get("auth_token")
    if not call_uuid or not auth_id or not auth_token:
        return {}
    url = f"{PLIVO_API_BASE}/{auth_id}/Call/{call_uuid}/"
    try:
        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(auth_id, auth_token)
            async with session.get(url, params={"status": "live"}, auth=auth) as response:
                if response.status != 200:
                    logger.warning("Plivo call lookup failed ({}) for call {}", response.status, call_uuid)
                    return {}
                data = await response.json()
                return {"from_number": data.get("from"), "to_number": data.get("to")}
    except Exception as e:
        logger.error(f"Error fetching call info from Plivo: {e}")
        return {}


class PlivoTransport(TelephonyProvider):
    transport_type = "plivo"

    def create_serializer(self, call_data: dict):
        plivo_creds = call_data.get("_plivo_creds") or get_plivo_credentials(org_id=call_data.get("_org_id"))
        return PlivoFrameSerializer(
            stream_id=call_data["stream_id"],
            call_id=call_data.get("call_id"),
            auth_id=plivo_creds.get("auth_id", ""),
            auth_token=plivo_creds.get("auth_token", ""),
        )

    async def resolve_from_to(self, call_data: dict) -> None:
        if call_data.get("from") or call_data.get("to"):
            return
        call_info = await get_plivo_call_info(call_data.get("call_id", ""), org_id=call_data.get("_org_id"))
        if call_info:
            call_data["from"] = to_e164(call_info.get("from_number")) or ""
            call_data["to"] = to_e164(call_info.get("to_number")) or ""
