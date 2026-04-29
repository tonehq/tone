"""Raw PCM audio serializer for testing — no protocol overhead.

Sends/receives raw 16-bit PCM audio bytes over WebSocket.
Used by the test WebSocket endpoint (/ws/test) as a drop-in replacement
for TwilioFrameSerializer / TelnyxFrameSerializer.
"""

from pipecat.frames.frames import (
    EndFrame,
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    StartFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer


class RawPCMSerializer(FrameSerializer):
    """Serializer that sends/receives raw PCM audio bytes.

    No JSON wrapping, no base64 encoding, no protocol messages.
    Just raw 16-bit PCM audio in both directions.
    """

    def __init__(self, sample_rate: int = 16000, num_channels: int = 1):
        super().__init__()
        self._sample_rate = sample_rate
        self._num_channels = num_channels

    async def serialize(self, frame: Frame) -> bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, bytes) and len(data) > 0:
            return InputAudioRawFrame(
                audio=data,
                sample_rate=self._sample_rate,
                num_channels=self._num_channels,
            )
        return None
