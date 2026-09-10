from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams

from core.services.pipeline.vad.base import VADProvider


class SileroVADProvider(VADProvider):
    slug = "silero"
    display_name = "Silero VAD"
    description = "Pipecat's bundled Silero ONNX model. Runs on CPU at 8 or 16 kHz with no external service."

    def build(self, params: VADParams) -> VADAnalyzer:
        return SileroVADAnalyzer(params=params)
