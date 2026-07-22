"""Raw PCM audio serializer for testing — no protocol overhead.

Sends/receives raw 16-bit PCM audio bytes over WebSocket.
Used by the test WebSocket endpoint (/ws/test) as a drop-in replacement
for TwilioFrameSerializer / TelnyxFrameSerializer.
"""

from loguru import logger
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
        self._logged_out = False
        self._logged_in = False
        self._out_chunks = 0
        self._in_chunks = 0

    async def serialize(self, frame: Frame) -> bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            self._out_chunks += 1
            if not self._logged_out:
                self._logged_out = True
                # KEY diagnostic: if the frame's rate != our declared rate, the audio is NOT
                # resampled here → the receiver mislabels it → ASR gets wrong-speed audio.
                logger.info(
                    "[raw-pcm] first OUT frame: bytes={} frame_rate={} serializer_rate={} ch={}",
                    len(frame.audio or b""), frame.sample_rate, self._sample_rate, frame.num_channels,
                )
            elif self._out_chunks % 250 == 0:  # ~every 5s of audio: confirms flow doesn't stall
                logger.info("[raw-pcm] OUT flowing: {} chunks sent", self._out_chunks)
            return frame.audio
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, bytes) and len(data) > 0:
            self._in_chunks += 1
            if not self._logged_in:
                self._logged_in = True
                logger.info(
                    "[raw-pcm] first IN chunk: bytes={} tagged_rate={} ch={}",
                    len(data), self._sample_rate, self._num_channels,
                )
            elif self._in_chunks % 250 == 0:
                logger.info("[raw-pcm] IN flowing: {} chunks received", self._in_chunks)
            return InputAudioRawFrame(
                audio=data,
                sample_rate=self._sample_rate,
                num_channels=self._num_channels,
            )
        return None
