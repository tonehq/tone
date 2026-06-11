import json
from typing import AsyncGenerator, Optional

from loguru import logger

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    ErrorFrame,
    Frame,
    StartFrame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService

_LANG_LABELS = {
    "en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "de": "German", "fr": "French", "ru": "Russian", "pt": "Portuguese",
    "es": "Spanish", "it": "Italian",
}

_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"]


def _qwen_language(value: str) -> str:
    if not value:
        return "English"
    v = value.strip()
    if v.title() in set(_LANG_LABELS.values()):
        return v.title()
    return _LANG_LABELS.get(v.lower().split("-")[0], "English")


try:
    import websockets
    from websockets.asyncio.client import connect as websocket_connect
    from websockets.protocol import State
except ModuleNotFoundError as e:
    logger.error(f"Exception: {e}")
    logger.error("In order to use Qwen websocket TTS, you need to `pip install websockets`.")
    raise Exception(f"Missing module: {e}")


class QwenWebSocketTTSService(TTSService):
    def __init__(
        self,
        *,
        url: str,
        voice_id: str = "Ryan",
        language: str = "English",
        sample_rate: Optional[int] = 24000,
        trace_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)

        self._url = url
        self._voice_id = voice_id
        self._language = _qwen_language(language)
        self._trace_id = trace_id
        self._websocket = None
        self.set_model_name("Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")

    def __str__(self):
        return f"{self.name}"

    def can_generate_metrics(self) -> bool:
        return True

    async def set_model(self, model: str):
        self.set_model_name(model)

    async def set_voice(self, voice: str):
        self._voice_id = voice

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self._connect()

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        await self._disconnect()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        await self._disconnect()

    async def _connect(self):
        try:
            if self._websocket and self._websocket.state is State.OPEN:
                return
            url = self._url
            if self._trace_id:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}trace_id={self._trace_id}"
            logger.debug(f"{self} connecting to Qwen TTS WebSocket {url}")
            self._websocket = await websocket_connect(url)
            logger.debug(f"{self} connected to Qwen TTS WebSocket")
        except Exception as e:
            self._websocket = None
            await self.push_error(error_msg=f"Unable to connect to Qwen TTS: {e}", exception=e)
            raise

    async def _disconnect(self):
        try:
            if self._websocket and self._websocket.state is State.OPEN:
                logger.debug(f"{self} disconnecting from Qwen TTS WebSocket")
                await self._websocket.close()
        except Exception as e:
            logger.warning(f"{self} error closing websocket: {e}")
        finally:
            self._websocket = None

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"{self}: Generating TTS [{text}]")
        try:
            if not self._websocket or self._websocket.state is not State.OPEN:
                await self._connect()

            await self.start_ttfb_metrics()
            await self._websocket.send(
                json.dumps({"text": text, "speaker": self._voice_id, "language": self._language})
            )

            started = False
            sample_rate = self.sample_rate
            async for message in self._websocket:
                if isinstance(message, (bytes, bytearray)):
                    if not started:
                        await self.start_tts_usage_metrics(text)
                        yield TTSStartedFrame()
                        started = True
                    await self.stop_ttfb_metrics()
                    yield TTSAudioRawFrame(bytes(message), sample_rate, 1)
                    continue

                try:
                    content = json.loads(message)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"{self} received non-JSON message: {message}")
                    continue

                msg_type = content.get("type")
                if msg_type == "start":
                    sample_rate = content.get("sample_rate") or self.sample_rate
                    await self.start_tts_usage_metrics(text)
                    yield TTSStartedFrame()
                    started = True
                elif msg_type == "end":
                    break
                elif msg_type == "error":
                    yield ErrorFrame(error=f"Qwen TTS error: {content.get('detail')}")
                    break

            yield TTSStoppedFrame()
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"{self} websocket closed during synthesis: {e}")
            await self._disconnect()
            yield TTSStoppedFrame()
        except Exception as e:
            logger.exception(f"{self} TTS generation failed")
            yield ErrorFrame(error=f"Qwen TTS generation failed: {e}")

    @classmethod
    def get_voices(cls, api_key: str = ""):
        return [
            {
                "name": s,
                "voice_id": s,
                "description": None,
                "gender": None,
                "language": None,
                "sample_url": None,
                "accent": None,
            }
            for s in _SPEAKERS
        ]
