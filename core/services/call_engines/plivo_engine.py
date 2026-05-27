from typing import Any, Dict

from pipecat.serializers.plivo import PlivoFrameSerializer

from core.services.call_engines.base import CallDirection, CallEngine, CallTransport
from core.services.call_engines.transports import WebsocketCallTransport


class PlivoCallEngine(CallEngine):
    SAMPLE_RATE = 8000

    def __init__(self, auth_id: str = "", auth_token: str = ""):
        self._auth_id = auth_id
        self._auth_token = auth_token

    @property
    def provider_name(self) -> str:
        return "plivo"

    def create_transport(
        self,
        websocket: Any,
        call_data: Dict[str, Any],
        direction: CallDirection = CallDirection.INBOUND,
    ) -> CallTransport:
        serializer = PlivoFrameSerializer(
            stream_id=call_data.get("stream_id", ""),
            call_id=call_data.get("call_id"),
            auth_id=self._auth_id,
            auth_token=self._auth_token,
        )
        return WebsocketCallTransport(
            websocket=websocket,
            serializer=serializer,
            direction=direction,
            sample_rate=self.SAMPLE_RATE,
        )
