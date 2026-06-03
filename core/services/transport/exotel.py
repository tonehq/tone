"""Exotel call engine."""

from pipecat.serializers.exotel import ExotelFrameSerializer

from core.services.transport.base import TelephonyProvider


class ExotelTransport(TelephonyProvider):
    transport_type = "exotel"

    def create_serializer(self, call_data: dict):
        return ExotelFrameSerializer(
            stream_sid=call_data["stream_id"],
            call_sid=call_data.get("call_id"),
        )
