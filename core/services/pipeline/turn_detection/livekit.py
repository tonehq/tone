from core.processors.livekit_turn_detector_turn_stop import (
    LiveKitTurnDetectorParams,
    LiveKitTurnDetectorUserTurnStopStrategy,
)
from core.services.pipeline.turn_detection.base import TurnDetectionContext, TurnDetector


class LiveKitTurnDetector(TurnDetector):
    slug = "livekit"
    display_name = "LiveKit Turn Detector"
    description = (
        "LiveKit's end-of-utterance language model. Runs locally on CPU and downloads "
        "from Hugging Face on first use."
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

    def build(self, context: TurnDetectionContext) -> list:
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
