from importlib.util import find_spec

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams

from core.config import settings
from core.services.pipeline.vad.base import VADProvider

if find_spec("aic_sdk"):
    from pipecat.audio.vad.aic_quail_vad import AICQuailVADAnalyzer
else:
    AICQuailVADAnalyzer = None


class AICQuailVADProvider(VADProvider):
    slug = "aic_quail"
    display_name = "ai-coustics Quail VAD"
    description = (
        "ai-coustics' standalone Quail VAD model. Needs aic_sdk and AIC_LICENSE_KEY on the "
        "call workers; the model downloads on first use."
    )
    schema = [
        {
            "name": "model_id",
            "data_type": "string",
            "type": "input",
            "format": "string",
            "validator": None,
            "required": 0,
            "default": "quail-vad-2.0-xxs-16khz",
            "description": "Quail VAD model identifier published by ai-coustics",
        },
    ]

    @classmethod
    def available(cls) -> bool:
        return AICQuailVADAnalyzer is not None and bool(settings.AIC_LICENSE_KEY)

    def build(self, params: VADParams) -> VADAnalyzer:
        if not self.available():
            raise ValueError("ai-coustics Quail VAD requires aic_sdk and AIC_LICENSE_KEY")
        return AICQuailVADAnalyzer(
            license_key=settings.AIC_LICENSE_KEY,
            model_id=self.settings["model_id"],
            params=params,
        )
