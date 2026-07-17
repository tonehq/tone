from typing import AsyncGenerator, Optional

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

try:  # pipecat >= 1.4.0 — settings object + run_tts(text, context_id)
    from pipecat.services.tts_service import TTSSettings
except ImportError:  # older pipecat — set_model_name() + run_tts(text)
    TTSSettings = None

_CHUNK_BYTES = 4800

_SPEED_WORDS = {
    "very_slow": 0.6, "very slow": 0.6, "slowest": 0.6,
    "slow": 0.8,
    "normal": 1.0, "medium": 1.0, "default": 1.0, "standard": 1.0,
    "fast": 1.2,
    "very_fast": 1.5, "very fast": 1.5, "fastest": 1.5,
}


def _coerce_speed(value) -> float:
    """Map the agent's `speed` setting to the float the server requires.

    The UI stores words ("normal"), the API validates a float and 422s on a string.
    Anything unparseable falls back to 1.0 rather than failing the call.
    """
    if value is None:
        return 1.0
    if isinstance(value, bool):
        return 1.0
    if isinstance(value, (int, float)):
        speed = float(value)
    else:
        text = str(value).strip().lower()
        if text in _SPEED_WORDS:
            speed = _SPEED_WORDS[text]
        else:
            try:
                speed = float(text)
            except ValueError:
                logger.warning("CosyVoice: unknown speed {!r}, using 1.0", value)
                return 1.0
    return min(max(speed, 0.5), 2.0)


class CosyVoiceTTSService(TTSService):
    """Self-hosted Fun-CosyVoice3 served by the neosun/cosyvoice FastAPI image.

    Speaks `/v1/audio/speech` with `response_format=pcm`, which returns the whole
    utterance as raw 24kHz mono s16le in one response. The server exposes no
    streaming variant and no `stream` field, so synthesis is fully buffered before
    any audio is pushed — expect seconds of latency, not milliseconds.

    `voice` must be a voice **id** returned by `/v1/voices/create` (CosyVoice3 ships
    with no preset voices; every voice is zero-shot cloned from reference audio).
    """

    def __init__(
        self,
        *,
        base_url: str,
        voice_id: str,
        model: str = "cosyvoice-v3",
        sample_rate: Optional[int] = 24000,
        speed: float = 1.0,
        instruct: Optional[str] = None,
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

        self._base_url = (base_url or "").rstrip("/")
        self._voice_id = voice_id
        self._model = model
        self._speed = _coerce_speed(speed)
        self._instruct = instruct
        self._trace_id = trace_id
        self._apply_model_name(model)

    def _apply_model_name(self, model: str):
        # pipecat < 0.0.104 had set_model_name(); newer versions store the
        # model on _settings and sync it to metrics separately.
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

    async def run_tts(self, text: str, context_id: str = "") -> AsyncGenerator[Frame, None]:
        # New pipecat calls run_tts(text, context_id) and pushes
        # TTSStarted/StoppedFrames itself (push_start_frame/push_stop_frames);
        # old pipecat calls run_tts(text) and expects us to yield them.
        new_api = TTSSettings is not None
        audio_kwargs = {"context_id": context_id} if new_api else {}
        logger.debug(f"{self}: Generating TTS [{text}]")

        payload = {
            "model": self._model,
            "input": text,
            "voice": self._voice_id,
            "response_format": "pcm",
            "speed": self._speed,
        }
        if self._instruct:
            payload["instruct"] = self._instruct
        params = {"trace_id": self._trace_id} if self._trace_id else None

        try:
            await self.start_ttfb_metrics()
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                resp = await client.post(
                    f"{self._base_url}/audio/speech", json=payload, params=params
                )
                if resp.status_code != 200:
                    detail = resp.text[:400]
                    logger.error(f"{self} TTS request failed ({resp.status_code}): {detail}")
                    yield ErrorFrame(error=f"CosyVoice TTS error {resp.status_code}: {detail}")
                    return
                audio = resp.content

            if not audio:
                yield ErrorFrame(error="CosyVoice TTS returned no audio")
                return

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
            yield ErrorFrame(error=f"CosyVoice TTS generation failed: {e}")

    @classmethod
    def get_voices(cls, api_key: str = ""):
        return []
