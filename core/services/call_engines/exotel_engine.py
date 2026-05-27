from typing import Any, Dict

from pipecat.serializers.exotel import ExotelFrameSerializer

from core.services.call_engines.base import CallDirection, CallEngine, CallTransport
from core.services.call_engines.transports import WebsocketCallTransport


class ExotelCallEngine(CallEngine):
    SAMPLE_RATE = 8000

    @property
    def provider_name(self) -> str:
        return "exotel"

    def create_transport(
        self,
        websocket: Any,
        call_data: Dict[str, Any],
        direction: CallDirection = CallDirection.INBOUND,
    ) -> CallTransport:
        serializer = ExotelFrameSerializer(
            stream_sid=call_data.get("stream_id", ""),
            call_sid=call_data.get("call_id"),
        )
        return WebsocketCallTransport(
            websocket=websocket,
            serializer=serializer,
            direction=direction,
            sample_rate=self.SAMPLE_RATE,
        )
