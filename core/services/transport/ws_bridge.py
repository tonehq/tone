"""Outbound WebSocket-bridge transport builder.

The inbound telephony path assembles a **server-side** ``FastAPIWebsocketTransport``
via ``TelephonyTransport`` (``base.py``) — the provider dials us and connects its media
stream INTO our socket. The outbound WS "test bridge" is its mirror image: a
**client-side** ``WebsocketClientTransport`` we dial OUT to the remote ``/ws/test``.

Both directions now live in this transport module so they differ only in the socket
source (server-accepted vs client-dialed) and the serializer; everything downstream of
``run_bot`` is identical. This construction used to be inline in
``call_engines/ws_bridge_runner.py::_run_bridge`` — it lives here so there is exactly one
place that assembles the outbound media transport.
"""

from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.client import (WebsocketClientParams,
                                                 WebsocketClientTransport)

from core.serializers.raw_pcm import RawPCMSerializer

# The one PCM rate for the whole bridge, raw PCM both ways. It MUST match the remote
# /ws/test rate (24 kHz = Cartesia's native TTS rate on both ends), so there is ZERO
# resampling on the TTS→wire→STT path — a 24→16 kHz resample keeps enough energy for VAD
# but degrades audio enough that Deepgram transcribes NOTHING. The bridge also declares
# this rate in the /ws/test URL so the two sides can never disagree.
BRIDGE_SAMPLE_RATE = 24000


def build_ws_bridge_transport(
    remote_uri: str, sample_rate: int = BRIDGE_SAMPLE_RATE
) -> BaseTransport:
    """Build the outbound-client media transport that dials the remote ``/ws/test``.

    Mirror of the inbound ``TelephonyTransport`` assembly: same pipeline, opposite socket
    direction — raw PCM at ``sample_rate`` both ways, no WAV header.
    """
    params = WebsocketClientParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=sample_rate,
        audio_out_sample_rate=sample_rate,
        add_wav_header=False,
        serializer=RawPCMSerializer(sample_rate=sample_rate, num_channels=1),
    )
    return WebsocketClientTransport(uri=remote_uri, params=params)
