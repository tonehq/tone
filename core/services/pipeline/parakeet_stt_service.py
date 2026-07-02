from typing import AsyncGenerator, Optional

import httpx
from loguru import logger

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601


class ParakeetSTTService(SegmentedSTTService):
    def __init__(
        self,
        *,
        url: str,
        sample_rate: Optional[int] = 16000,
        language: Language = Language.EN,
        model: str = "nvidia/parakeet-tdt-0.6b-v2",
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

    def can_generate_metrics(self) -> bool:
        return True

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        await self.start_processing_metrics()
        await self.start_ttfb_metrics()
        text = ""
        try:
            params = {"trace_id": self._trace_id} if self._trace_id else None
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._url,
                    content=audio,
                    headers={"Content-Type": "application/octet-stream"},
                    params=params,
                )
                resp.raise_for_status()
                text = (resp.json().get("text") or "").strip()
        except Exception as e:  # noqa: BLE001
            logger.error(f"{self} Parakeet ASR request failed: {e}")
        await self.stop_ttfb_metrics()
        await self.stop_processing_metrics()
        if text:
            yield TranscriptionFrame(text, self._user_id, time_now_iso8601(), self._language)
