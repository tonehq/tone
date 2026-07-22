"""Telephony-free "test" provider.

Rides the same ``TelephonyTransport`` / ``FastAPIWebsocketTransport`` assembly as the
real telephony providers (twilio/telnyx/plivo/exotel) but swaps the provider serializer
for ``RawPCMSerializer`` — raw 16-bit PCM in/out, no Twilio Media-Streams framing, no
phone number. This backs the ``/ws/test`` WebSocket endpoint (``main.py``), letting a
client (``test-cases/pipeline/ws_test_client.py``) drive an agent's pipeline directly
for testing.

The agent is resolved by the ``agent_id`` promoted from ``call_data["body"]`` (or by
``call_data["to"]`` when a ``phone_number`` is supplied) — exactly the same seam the
outbound telephony path uses, so no bespoke resolution logic is needed.
"""

from core.serializers.raw_pcm import RawPCMSerializer
from core.services.transport.base import TelephonyProvider

# Default input rate for the raw-PCM test stream (matches the test client's WAV output).
DEFAULT_TEST_SAMPLE_RATE = 16000


class TestTransport(TelephonyProvider):
    transport_type = "test"

    def create_serializer(self, call_data: dict):
        sample_rate = int((call_data or {}).get("sample_rate") or DEFAULT_TEST_SAMPLE_RATE)
        return RawPCMSerializer(sample_rate=sample_rate, num_channels=1)

    # resolve_from_to: inherit the no-op default — a test call has no PSTN from/to.
