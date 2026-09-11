from pipecat.serializers.vonage import VonageFrameSerializer

from core.services.transport.base import TelephonyProvider

VONAGE_SAMPLE_RATE = 16000
VONAGE_CONTENT_TYPE = f"audio/l16;rate={VONAGE_SAMPLE_RATE}"


class VonageTransport(TelephonyProvider):
    transport_type = "vonage"

    def create_serializer(self, call_data: dict):
        sample_rate = int(call_data.get("sample_rate") or VONAGE_SAMPLE_RATE)
        return VonageFrameSerializer(
            params=VonageFrameSerializer.InputParams(vonage_sample_rate=sample_rate),
        )
