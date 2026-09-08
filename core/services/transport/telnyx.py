"""Telnyx call engine."""

from pipecat.serializers.telnyx import TelnyxFrameSerializer

from core.services.transport.base import TelephonyProvider


class TelnyxTransport(TelephonyProvider):
    transport_type = "telnyx"

    def create_serializer(self, call_data: dict):
        # This repo runs Telnyx over TeXML (Twilio-compatible), so the live call
        # id is a TeXML CallSid (e.g. "v3:..."), NOT a Call-Control ID. pipecat's
        # TelnyxFrameSerializer.auto_hang_up uses the Call-Control API, which
        # rejects a TeXML SID with 422 "Invalid Call Control ID" (code 90015).
        # Disable it and let the call_termination terminator hang up via the
        # correct TeXML API (TelnyxCallEngine.end_call). With auto_hang_up off the
        # serializer needs no api_key.
        return TelnyxFrameSerializer(
            stream_id=call_data["stream_id"],
            call_control_id=call_data.get("call_control_id") or call_data.get("call_id"),
            outbound_encoding=call_data.get("outbound_encoding", "PCMU"),
            inbound_encoding="PCMU",
            params=TelnyxFrameSerializer.InputParams(auto_hang_up=False),
        )
