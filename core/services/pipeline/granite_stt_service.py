import json
from typing import AsyncGenerator, Optional

from loguru import logger
from websockets.protocol import State

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InterimTranscriptionFrame,
    StartFrame,
    TranscriptionFrame,
)
from pipecat.services.stt_service import WebsocketSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt

try:
    import websockets
    from websockets.asyncio.client import connect as websocket_connect
except ModuleNotFoundError as e:
    logger.exception("Granite websocket STT import failed")
    logger.error("To use the Granite websocket STT, you need to `pip install websockets`.")
    raise Exception(f"Missing module: {e}")


class GraniteWebSocketSTTService(WebsocketSTTService):
    def __init__(
        self,
        *,
        url: str,
        sample_rate: Optional[int] = 16000,
        language: Language = Language.EN,
        model: str = "ibm-granite/granite-speech-3.3-2b",
        trace_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)

        self._url = url
        self._language = language
        self._trace_id = trace_id
        # pipecat < 0.0.104 had set_model_name(); newer versions store the
        # model on _settings and sync it to metrics separately.
        if hasattr(self, "set_model_name"):
            self.set_model_name(model)
        else:
            self._settings.model = model
            self._sync_model_name_to_metrics()

        self._receive_task = None
        self._last_partial: str = ""

    def __str__(self):
        return f"{self.name}"

    def can_generate_metrics(self) -> bool:
        return True

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._connect()

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        await self._send_eof()
        await self._disconnect()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        await self._disconnect()

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        await self.start_processing_metrics()

        if self._websocket and self._websocket.state is State.OPEN:
            try:
                await self._websocket.send(audio)
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"{self} websocket closed while sending audio: {e}")

        yield None

    async def _connect(self):
        await super()._connect()
        await self._connect_websocket()

        if self._websocket and not self._receive_task:
            self._receive_task = self.create_task(self._receive_task_handler(self._report_error))

    async def _disconnect(self):
        await super()._disconnect()

        if self._receive_task:
            await self.cancel_task(self._receive_task)
            self._receive_task = None

        await self._disconnect_websocket()

    async def _connect_websocket(self):
        try:
            if self._websocket and self._websocket.state is State.OPEN:
                return

            url = self._url
            if self._trace_id:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}trace_id={self._trace_id}"
            logger.debug(f"{self} connecting to Granite WebSocket {url}")
            self._websocket = await websocket_connect(url)
            self._last_partial = ""
            await self._call_event_handler("on_connected")
            logger.debug(f"{self} connected to Granite WebSocket")
        except Exception as e:
            await self.push_error(error_msg=f"Unable to connect to Granite STT: {e}", exception=e)
            raise

    async def _disconnect_websocket(self):
        try:
            if self._websocket and self._websocket.state is State.OPEN:
                logger.debug(f"{self} disconnecting from Granite WebSocket")
                await self._websocket.close()
        except Exception as e:
            await self.push_error(error_msg=f"Error closing websocket: {e}", exception=e)
        finally:
            self._websocket = None
            await self._call_event_handler("on_disconnected")

    async def _send_eof(self):
        if self._websocket and self._websocket.state is State.OPEN:
            try:
                await self._websocket.send("eof")
            except websockets.exceptions.ConnectionClosed as exc:
                logger.debug("{} websocket already closed sending eof: {}", self, exc)

    def _get_websocket(self):
        if self._websocket:
            return self._websocket
        raise Exception("Websocket not connected")

    @traced_stt
    async def _handle_transcription(
        self, transcript: str, is_final: bool, language: Optional[str] = None
    ):
        await self.stop_processing_metrics()

    async def _receive_messages(self):
        async for message in self._get_websocket():
            try:
                content = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"{self} received non-JSON message: {message}")
                continue

            msg_type = content.get("type")
            text = content.get("text", "")

            if msg_type == "partial":
                self._last_partial = text
                await self.push_frame(
                    InterimTranscriptionFrame(
                        text, self._user_id, time_now_iso8601(), self._language, result=content
                    )
                )
            elif msg_type == "final":
                final_text = text or self._last_partial
                self._last_partial = ""
                await self.push_frame(
                    TranscriptionFrame(
                        final_text, self._user_id, time_now_iso8601(), self._language, result=content
                    )
                )
                await self._handle_transcription(
                    transcript=final_text, is_final=True, language=self._language
                )
            elif msg_type == "error":
                await self.push_error(error_msg=f"Granite STT error: {content.get('detail')}")
