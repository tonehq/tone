"""Telnyx call engine."""

from pipecat.serializers.telnyx import TelnyxFrameSerializer

from core.services.transport.base import TelephonyProvider
from core.services.transport.telephony_credentials import get_telnyx_api_key


class TelnyxTransport(TelephonyProvider):
    transport_type = "telnyx"

    def create_serializer(self, call_data: dict):
        telnyx_api_key = call_data.get("_telnyx_creds", {}).get("api_key") or get_telnyx_api_key(
            org_id=call_data.get("_org_id")
        )
        return TelnyxFrameSerializer(
            stream_id=call_data["stream_id"],
            call_control_id=call_data.get("call_control_id"),
            outbound_encoding=call_data.get("outbound_encoding", "PCMU"),
            inbound_encoding="PCMU",
            api_key=telnyx_api_key,
        )
