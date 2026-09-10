from importlib.util import find_spec

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams

from core.config import settings
from core.services.pipeline.vad.base import VADProvider

if find_spec("aic_sdk"):
    from pipecat.audio.vad.aic_quail_vad import DEFAULT_QUAIL_VAD_MODEL_ID, AICQuailVADAnalyzer
else:
    AICQuailVADAnalyzer = None
    DEFAULT_QUAIL_VAD_MODEL_ID = None


class AICQuailVADProvider(VADProvider):
    slug = "aic_quail"
    display_name = "ai-coustics VAD"
    description = (
        "ai-coustics' standalone VAD model (formerly Quail VAD). Needs aic_sdk and AIC_SDK_LICENSE "
        "on the call workers; the model downloads from their CDN on first use."
    )
    schema = [
        {
            "name": "model_id",
            "data_type": "string",
            "type": "input",
            "format": "string",
            "validator": None,
            "required": 0,
            "default": DEFAULT_QUAIL_VAD_MODEL_ID,
            "description": (
                "ai-coustics VAD model identifier; the default matches the SDK version the worker image ships"
            ),
        },
    ]

    @classmethod
    def available(cls) -> bool:
        return AICQuailVADAnalyzer is not None and bool(settings.AIC_SDK_LICENSE)

    def build(self, params: VADParams) -> VADAnalyzer:
        if not self.available():
            raise ValueError("ai-coustics Quail VAD requires aic_sdk and AIC_SDK_LICENSE")
        return AICQuailVADAnalyzer(
            license_key=settings.AIC_SDK_LICENSE,
            model_id=self.settings["model_id"],
            params=params,
        )
