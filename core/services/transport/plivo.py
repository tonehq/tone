"""Plivo call engine."""

from pipecat.serializers.plivo import PlivoFrameSerializer

from core.services.transport.base import TelephonyProvider
from core.services.transport.telephony_credentials import get_plivo_credentials


class PlivoTransport(TelephonyProvider):
    transport_type = "plivo"

    def create_serializer(self, call_data: dict):
        plivo_creds = call_data.get("_plivo_creds") or get_plivo_credentials(
            org_id=call_data.get("_org_id"),
            channel_id=call_data.get("_channel_id"),
        )
        return PlivoFrameSerializer(
            stream_id=call_data["stream_id"],
            call_id=call_data.get("call_id"),
            auth_id=plivo_creds.get("auth_id", ""),
            auth_token=plivo_creds.get("auth_token", ""),
        )
