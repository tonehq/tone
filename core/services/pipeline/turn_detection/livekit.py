from functools import lru_cache

from loguru import logger

from core.config import settings
from core.processors.livekit_turn_detector_turn_stop import (
    LiveKitTurnDetectorParams,
    LiveKitTurnDetectorUserTurnStopStrategy,
)
from core.services.pipeline.turn_detection.base import TurnDetectionContext, TurnDetector
from core.utils.pod_resources import memory_usage

MIN_MEMORY_MIB_DEFAULT = 1536


def minimum_memory_mib() -> int:
    return settings.LIVEKIT_TURN_DETECTOR_MIN_MEMORY_MIB or MIN_MEMORY_MIB_DEFAULT


@lru_cache(maxsize=1)
def _host_has_memory(minimum_mib: int) -> bool:
    _, limit_mib = memory_usage()
    if limit_mib is None or limit_mib >= minimum_mib:
        return True
    logger.warning(
        "LiveKit turn detector hidden: container memory limit {:.0f} MiB is below the {} MiB it needs",
        limit_mib, minimum_mib,
    )
    return False


class LiveKitTurnDetector(TurnDetector):
    slug = "livekit"
    display_name = "LiveKit Turn Detector"
    description = (
        "LiveKit's end-of-utterance language model. Runs locally on CPU, downloads from "
        "Hugging Face on first use and needs about 1.5 GB of memory on the call worker."
    )
    schema = [
        {
            "name": "model_type",
            "data_type": "string",
            "type": "select",
            "format": "string",
            "validator": None,
            "required": 0,
            "default": "multilingual",
            "options": ["multilingual", "en"],
            "description": "Multilingual covers 14 languages including English. The en variant is deprecated",
        },
        {
            "name": "threshold",
            "data_type": "float",
            "type": "input number",
            "format": "float",
            "validator": {"min": 0},
            "required": 0,
            "description": "Overrides the per-language end-of-utterance threshold. Leave empty for the tuned value",
        },
        {
            "name": "language",
            "data_type": "string",
            "type": "input",
            "format": "string",
            "validator": None,
            "required": 0,
            "description": "Language code used when the transcript carries none, e.g. en or hi",
        },
        {
            "name": "unfinished_timeout",
            "data_type": "float",
            "type": "input number",
            "format": "float",
            "validator": {"min": 0.5, "max": 15},
            "required": 0,
            "default": 3.0,
            "description": "Seconds to keep listening after the model says the user is not done",
        },
        {
            "name": "max_history_turns",
            "data_type": "integer",
            "type": "input number",
            "format": "integer",
            "validator": {"min": 1, "max": 20},
            "required": 0,
            "default": 6,
            "description": "Previous conversation turns given to the model",
        },
    ]

    @classmethod
    def available(cls) -> bool:
        return _host_has_memory(minimum_memory_mib())

    def build(self, context: TurnDetectionContext) -> list:
        if not self.available():
            raise ValueError(
                f"LiveKit turn detector needs at least {minimum_memory_mib()} MiB of container memory; "
                "raise the call worker memory limit or lower LIVEKIT_TURN_DETECTOR_MIN_MEMORY_MIB"
            )
        params = LiveKitTurnDetectorParams(
            model_type=self.settings["model_type"],
            threshold=self.settings.get("threshold"),
            max_history_turns=self.settings["max_history_turns"],
        )
        return [
            LiveKitTurnDetectorUserTurnStopStrategy(
                params=params,
                context=context.llm_context,
                unfinished_timeout=self.settings["unfinished_timeout"],
                language=self.settings.get("language") or context.language,
            )
        ]
