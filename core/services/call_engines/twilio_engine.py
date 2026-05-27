from typing import Any, Dict

from pipecat.serializers.twilio import TwilioFrameSerializer

from core.services.call_engines.base import CallDirection, CallEngine, CallTransport
from core.services.call_engines.transports import WebsocketCallTransport


class TwilioCallEngine(CallEngine):
    SAMPLE_RATE = 8000

    def __init__(self, account_sid: str = "", auth_token: str = ""):
        self._account_sid = account_sid
        self._auth_token = auth_token

    @property
    def provider_name(self) -> str:
        return "twilio"

    def create_transport(
        self,
        websocket: Any,
        call_data: Dict[str, Any],
        direction: CallDirection = CallDirection.INBOUND,
    ) -> CallTransport:
        has_creds = bool(self._account_sid and self._auth_token)
        serializer_kwargs: Dict[str, Any] = {
            "stream_sid": call_data.get("stream_id", ""),
            "call_sid": call_data.get("call_id", ""),
            "account_sid": self._account_sid,
            "auth_token": self._auth_token,
        }
        if not has_creds:
            serializer_kwargs["params"] = TwilioFrameSerializer.InputParams(
                auto_hang_up=False
            )

        serializer = TwilioFrameSerializer(**serializer_kwargs)
        return WebsocketCallTransport(
            websocket=websocket,
            serializer=serializer,
            direction=direction,
            sample_rate=self.SAMPLE_RATE,
        )
