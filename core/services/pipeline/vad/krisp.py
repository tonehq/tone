from importlib.util import find_spec

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams

from core.config import settings
from core.services.pipeline.vad.base import VADProvider

if find_spec("krisp_audio"):
    from pipecat.audio.vad.krisp_viva_vad import KrispVivaVadAnalyzer
else:
    KrispVivaVadAnalyzer = None


class KrispVivaVADProvider(VADProvider):
    slug = "krisp_viva"
    display_name = "Krisp VIVA VAD"
    description = (
        "Krisp's licensed VAD model from the VIVA SDK. Needs krisp_audio and "
        "KRISP_VIVA_VAD_MODEL_PATH on the call workers."
    )
    schema = [
        {
            "name": "frame_duration",
            "data_type": "integer",
            "type": "select",
            "format": "integer",
            "validator": None,
            "required": 0,
            "default": "10",
            "options": ["10", "20", "30"],
            "description": "Milliseconds of audio per analysis frame",
        },
    ]

    @classmethod
    def available(cls) -> bool:
        return KrispVivaVadAnalyzer is not None and bool(settings.KRISP_VIVA_VAD_MODEL_PATH)

    def build(self, params: VADParams) -> VADAnalyzer:
        if not self.available():
            raise ValueError("Krisp VIVA VAD requires krisp_audio and KRISP_VIVA_VAD_MODEL_PATH")
        return KrispVivaVadAnalyzer(
            model_path=settings.KRISP_VIVA_VAD_MODEL_PATH,
            frame_duration=self.settings["frame_duration"],
            params=params,
        )
