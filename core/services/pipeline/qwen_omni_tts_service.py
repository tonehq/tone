import base64
import json
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

_LANG_LABELS = {
    "en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "de": "German", "fr": "French", "ru": "Russian", "pt": "Portuguese",
    "es": "Spanish", "it": "Italian",
}

_SPEAKERS = ["vivian", "serena", "uncle_fu", "dylan", "eric", "ryan", "aiden", "ono_anna", "sohee"]

_DEFAULT_SPEAKER = "vivian"


def _qwen_language(value: str) -> str:
    if not value:
        return "English"
    v = value.strip()
    if v.title() in set(_LANG_LABELS.values()):
        return v.title()
    return _LANG_LABELS.get(v.lower().split("-")[0], "English")


def _qwen_voice(value: Optional[str]) -> str:
    if not value:
        return _DEFAULT_SPEAKER
    v = value.strip().lower()
    return v if v in _SPEAKERS else _DEFAULT_SPEAKER


class QwenOmniTTSService(TTSService):
    """Self-hosted Qwen3-TTS served by vLLM-Omni (`vllm serve <model> --omni`).

    Speaks the OpenAI-compatible `/v1/audio/speech` API, which streams
    `speech.audio.delta` SSE events carrying base64-encoded PCM (24kHz mono
    s16le) rather than raw audio bytes.
    """

    def __init__(
        self,
        *,
        base_url: str,
        voice_id: str = _DEFAULT_SPEAKER,
        language: str = "English",
        model: str = "qwen3-tts",
        sample_rate: Optional[int] = 24000,
        trace_id: Optional[str] = None,
        **kwargs,
    ):
        voice = _qwen_voice(voice_id)
        if TTSSettings is not None:
            super().__init__(
                sample_rate=sample_rate,
                push_start_frame=True,
                push_stop_frames=True,
                settings=TTSSettings(
                    model=model,
                    voice=voice,
                    language=_qwen_language(language),
                ),
                **kwargs,
            )
        else:
            super().__init__(sample_rate=sample_rate, **kwargs)

        self._base_url = (base_url or "").rstrip("/")
        self._voice_id = voice
        self._language = _qwen_language(language)
        self._model = model
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
        self._voice_id = _qwen_voice(voice)

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
            "language": self._language,
            "response_format": "pcm",
            "stream": True,
        }
        params = {"trace_id": self._trace_id} if self._trace_id else None
        started = False

        try:
            await self.start_ttfb_metrics()
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/audio/speech",
                    json=payload,
                    params=params,
                    headers={"Accept": "text/event-stream"},
                ) as resp:
                    if resp.status_code != 200:
                        detail = (await resp.aread()).decode(errors="replace")[:400]
                        logger.error(f"{self} TTS request failed ({resp.status_code}): {detail}")
                        yield ErrorFrame(error=f"Qwen TTS error {resp.status_code}: {detail}")
                        return

                    await self.start_tts_usage_metrics(text)

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            logger.warning(f"{self} received non-JSON SSE data: {data[:120]}")
                            continue

                        event_type = event.get("type")
                        if event_type == "speech.audio.delta":
                            audio_b64 = event.get("audio")
                            if not audio_b64:
                                continue
                            try:
                                chunk = base64.b64decode(audio_b64)
                            except (ValueError, TypeError) as e:
                                logger.warning(f"{self} failed to decode audio delta: {e}")
                                continue
                            if not chunk:
                                continue
                            if not started:
                                if not new_api:
                                    yield TTSStartedFrame()
                                started = True
                            await self.stop_ttfb_metrics()
                            yield TTSAudioRawFrame(chunk, self.sample_rate, 1, **audio_kwargs)
                        elif event_type == "speech.audio.done":
                            break
                        elif event_type == "error":
                            detail = event.get("error") or event.get("detail")
                            logger.error(f"{self} TTS stream error: {detail}")
                            yield ErrorFrame(error=f"Qwen TTS error: {detail}")
                            break

            if not new_api:
                yield TTSStoppedFrame()
        except Exception as e:  # noqa: BLE001
            logger.exception(f"{self} TTS generation failed")
            yield ErrorFrame(error=f"Qwen TTS generation failed: {e}")

    @classmethod
    def get_voices(cls, api_key: str = ""):
        return [
            {
                "name": s.replace("_", " ").title(),
                "voice_id": s,
                "description": None,
                "gender": None,
                "language": None,
                "sample_url": None,
                "accent": None,
            }
            for s in _SPEAKERS
        ]
