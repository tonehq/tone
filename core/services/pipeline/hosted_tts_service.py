import base64
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from loguru import logger

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService

try:
    from pipecat.services.tts_service import TTSSettings
except ImportError:
    TTSSettings = None

_CHUNK_BYTES = 4800
_WAV_HEADER_BYTES = 44


class HostedTTSService(TTSService):

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: Optional[str] = None,
        voice_id: Optional[str] = None,
        sample_rate: Optional[int] = 24000,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
        text_field: str = "text",
        model_field: Optional[str] = "model",
        voice_field: Optional[str] = "voice",
        audio_field: Optional[str] = None,
        audio_url_field: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        strip_wav_header: bool = False,
        trace_id: Optional[str] = None,
        **kwargs,
    ):
        if TTSSettings is not None:
            super().__init__(
                sample_rate=sample_rate,
                push_start_frame=True,
                push_stop_frames=True,
                settings=TTSSettings(model=model, voice=voice_id, language=None),
                **kwargs,
            )
        else:
            super().__init__(sample_rate=sample_rate, **kwargs)

        self._api_key = api_key
        self._base_url = (base_url or "").rstrip("/")
        self._model = model
        self._voice_id = voice_id
        self._auth_header = auth_header
        self._auth_prefix = auth_prefix
        self._text_field = text_field
        self._model_field = model_field
        self._voice_field = voice_field
        self._audio_field = audio_field
        self._audio_url_field = audio_url_field
        self._extra_body = dict(extra_body or {})
        self._extra_headers = dict(extra_headers or {})
        self._strip_wav_header = strip_wav_header
        self._trace_id = trace_id
        if model:
            self._apply_model_name(model)

    def _apply_model_name(self, model: str):
        if hasattr(self, "set_model_name"):
            self.set_model_name(model)
        else:
            self._settings.model = model
            self._sync_model_name_to_metrics()

    def __str__(self):
        return f"{self.name}"

    def can_generate_metrics(self) -> bool:
        return True

    async def set_model(self, model: str):
        self._model = model
        self._apply_model_name(model)

    async def set_voice(self, voice: str):
        self._voice_id = voice

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", **self._extra_headers}
        if self._api_key:
            headers[self._auth_header] = f"{self._auth_prefix}{self._api_key}"
        return headers

    def _payload(self, text: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {self._text_field: text, **self._extra_body}
        if self._model_field and self._model:
            payload[self._model_field] = self._model
        if self._voice_field and self._voice_id:
            payload[self._voice_field] = self._voice_id
        return payload

    async def _extract_audio(self, resp: httpx.Response, client: httpx.AsyncClient) -> bytes:
        if not (self._audio_field or self._audio_url_field):
            return resp.content

        body = resp.json()
        if self._audio_url_field:
            url = body
            for part in self._audio_url_field.split("."):
                if not isinstance(url, dict):
                    return b""
                url = url.get(part)
            if not isinstance(url, str) or not url:
                return b""
            fetched = await client.get(url)
            if fetched.status_code != 200:
                return b""
            return fetched.content

        encoded = body
        for part in self._audio_field.split("."):
            if not isinstance(encoded, dict):
                return b""
            encoded = encoded.get(part)
        if not isinstance(encoded, str) or not encoded:
            return b""
        if "," in encoded and encoded.lstrip().startswith("data:"):
            encoded = encoded.split(",", 1)[1]
        return base64.b64decode(encoded)

    async def run_tts(self, text: str, context_id: str = "") -> AsyncGenerator[Frame, None]:
        new_api = TTSSettings is not None
        audio_kwargs = {"context_id": context_id} if new_api else {}
        logger.debug(f"{self}: Generating TTS [{text}]")

        try:
            await self.start_ttfb_metrics()
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                resp = await client.post(
                    self._base_url, json=self._payload(text), headers=self._headers()
                )
                if resp.status_code != 200:
                    detail = resp.text[:400]
                    logger.error(f"{self} TTS request failed ({resp.status_code}): {detail}")
                    yield ErrorFrame(error=f"Hosted TTS error {resp.status_code}: {detail}")
                    return
                audio = await self._extract_audio(resp, client)

            if not audio:
                yield ErrorFrame(error="Hosted TTS returned no audio")
                return

            if self._strip_wav_header and audio[:4] == b"RIFF":
                audio = audio[_WAV_HEADER_BYTES:]

            await self.stop_ttfb_metrics()
            await self.start_tts_usage_metrics(text)

            if not new_api:
                yield TTSStartedFrame()
            for i in range(0, len(audio), _CHUNK_BYTES):
                chunk = audio[i : i + _CHUNK_BYTES]
                if chunk:
                    yield TTSAudioRawFrame(chunk, self.sample_rate, 1, **audio_kwargs)
            if not new_api:
                yield TTSStoppedFrame()
        except Exception as e:  # noqa: BLE001
            logger.exception(f"{self} TTS generation failed")
            yield ErrorFrame(error=f"Hosted TTS generation failed: {e}")
