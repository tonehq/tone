from typing import Any, Dict

from pipecat.serializers.telnyx import TelnyxFrameSerializer

from core.services.call_engines.base import CallDirection, CallEngine, CallTransport
from core.services.call_engines.transports import WebsocketCallTransport


class TelnyxCallEngine(CallEngine):
    SAMPLE_RATE = 8000

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "telnyx"

    def create_transport(
        self,
        websocket: Any,
        call_data: Dict[str, Any],
        direction: CallDirection = CallDirection.INBOUND,
    ) -> CallTransport:
        serializer = TelnyxFrameSerializer(
            stream_id=call_data.get("stream_id", ""),
            call_control_id=call_data.get("call_control_id"),
            outbound_encoding=call_data.get("outbound_encoding", "PCMU"),
            inbound_encoding="PCMU",
            api_key=self._api_key,
        )
        return WebsocketCallTransport(
            websocket=websocket,
            serializer=serializer,
            direction=direction,
            sample_rate=self.SAMPLE_RATE,
        )
