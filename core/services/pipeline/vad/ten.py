from importlib.util import find_spec

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams

from core.services.pipeline.vad.base import VADProvider

if find_spec("ten_vad"):
    from core.processors.ten_vad_analyzer import TENVADAnalyzer, library_loads
else:
    TENVADAnalyzer = None

    def library_loads() -> bool:
        return False


class TENVADProvider(VADProvider):
    slug = "ten"
    display_name = "TEN VAD"
    description = (
        "TEN framework's frame-level VAD, Apache 2.0, with faster speech-to-silence transitions "
        "than Silero. Needs the ten-vad package on the call workers."
    )
    schema = [
        {
            "name": "hop_size",
            "data_type": "integer",
            "type": "select",
            "format": "integer",
            "validator": None,
            "required": 0,
            "default": "256",
            "options": ["160", "256"],
            "description": "Samples per analysis frame at 16 kHz: 160 is 10 ms, 256 is 16 ms",
        },
    ]

    @classmethod
    def available(cls) -> bool:
        return TENVADAnalyzer is not None and library_loads()

    def build(self, params: VADParams) -> VADAnalyzer:
        if not self.available():
            raise ValueError("TEN VAD requires the ten-vad package and its native library on the call worker")
        return TENVADAnalyzer(hop_size=self.settings["hop_size"], params=params)
