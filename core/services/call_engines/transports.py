from typing import Any, Optional

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from core.services.call_engines.base import CallDirection, CallTransport


class WebsocketCallTransport(CallTransport):
    def __init__(
        self,
        websocket: Any,
        serializer: FrameSerializer,
        direction: CallDirection,
        sample_rate: int = 8000,
    ):
        self._websocket = websocket
        self._serializer = serializer
        self._direction = direction
        self._sample_rate = sample_rate
        self._pipeline_task = None
        self._inner: Optional[FastAPIWebsocketTransport] = None

    def _build(self) -> FastAPIWebsocketTransport:
        if self._inner is None:
            vad_analyzer = SileroVADAnalyzer()
            self._inner = FastAPIWebsocketTransport(
                websocket=self._websocket,
                params=FastAPIWebsocketParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    add_wav_header=False,
                    vad_analyzer=vad_analyzer,
                    serializer=self._serializer,
                ),
            )
        return self._inner

    def input(self) -> FrameProcessor:
        return self._build().input()

    def output(self) -> FrameProcessor:
        return self._build().output()

    def get_pipecat_transport(self) -> BaseTransport:
        return self._build()

    async def setup(self) -> None:
        self._build()

    async def teardown(self) -> None:
        if self._websocket is not None:
            try:
                await self._websocket.close()
            except Exception as exc:
                logger.debug(f"[WebsocketCallTransport] websocket close failed: {exc}")

    def set_pipeline_task(self, task) -> None:
        self._pipeline_task = task

    @property
    def audio_sample_rate(self) -> int:
        return self._sample_rate

    @property
    def direction(self) -> CallDirection:
        return self._direction
