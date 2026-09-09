import numpy as np
from loguru import logger
from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams
from ten_vad import TenVad

MODEL_SAMPLE_RATE = 16000
SUPPORTED_SAMPLE_RATES = (8000, 16000)
FLAG_THRESHOLD = 0.5


class TENVADAnalyzer(VADAnalyzer):
    def __init__(
        self,
        *,
        hop_size: int,
        sample_rate: int | None = None,
        params: VADParams | None = None,
    ):
        super().__init__(sample_rate=sample_rate, params=params)
        self._hop_size = hop_size
        self._model = TenVad(hop_size, FLAG_THRESHOLD)

    def set_sample_rate(self, sample_rate: int):
        if sample_rate not in SUPPORTED_SAMPLE_RATES:
            raise ValueError(
                f"TEN VAD sample rate needs to be one of {SUPPORTED_SAMPLE_RATES} (sample rate: {sample_rate})"
            )
        super().set_sample_rate(sample_rate)

    def num_frames_required(self) -> int:
        return self._hop_size * self.sample_rate // MODEL_SAMPLE_RATE

    def voice_confidence(self, buffer) -> float:
        try:
            audio = np.frombuffer(buffer, np.int16)
            if self.sample_rate != MODEL_SAMPLE_RATE:
                audio = self._to_model_rate(audio)
            if len(audio) != self._hop_size:
                return 0.0
            probability, _ = self._model.process(audio)
            return float(probability)
        except Exception as e:
            logger.error(f"Error analyzing audio with TEN VAD: {e}")
            return 0.0

    def _to_model_rate(self, audio: np.ndarray) -> np.ndarray:
        ratio = MODEL_SAMPLE_RATE // self.sample_rate
        positions = np.arange(len(audio) * ratio) / ratio
        return np.interp(positions, np.arange(len(audio)), audio.astype(np.float32)).astype(np.int16)
