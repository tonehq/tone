from core.config import settings
from core.processors.ten_turn_detection_turn_stop import (
    TENTurnDetectionParams,
    TENTurnDetectionUserTurnStopStrategy,
)
from core.services.pipeline.turn_detection.base import TurnDetectionContext, TurnDetector


class TENTurnDetector(TurnDetector):
    slug = "ten"
    display_name = "TEN Turn Detection"
    description = (
        "Text-based turn detection served from an OpenAI-compatible endpoint. "
        "Configure TEN_TURN_DETECTION_BASE_URL on the server."
    )
    schema = [
        {
            "name": "unfinished_timeout",
            "data_type": "float",
            "type": "input number",
            "format": "float",
            "validator": {"min": 0.5, "max": 15},
            "required": 0,
            "default": 5.0,
            "description": "Seconds to keep listening after the model says the user is not done",
        },
        {
            "name": "request_timeout",
            "data_type": "float",
            "type": "input number",
            "format": "float",
            "validator": {"min": 0.2, "max": 5},
            "required": 0,
            "default": 2.0,
            "description": "Seconds to wait for the endpoint before ending the turn anyway",
        },
        {
            "name": "strip_punctuation",
            "data_type": "boolean",
            "type": "switch",
            "format": "boolean",
            "validator": None,
            "required": 0,
            "default": True,
            "description": "Remove punctuation from the transcript before classification",
        },
    ]

    @classmethod
    def available(cls) -> bool:
        return bool(settings.TEN_TURN_DETECTION_BASE_URL)

    def build(self, context: TurnDetectionContext) -> list:
        if not self.available():
            raise ValueError("TEN turn detection requires TEN_TURN_DETECTION_BASE_URL")
        params = TENTurnDetectionParams(
            base_url=settings.TEN_TURN_DETECTION_BASE_URL,
            api_key=settings.TEN_TURN_DETECTION_API_KEY or "TEN_Turn_Detection",
            model=settings.TEN_TURN_DETECTION_MODEL or "TEN_Turn_Detection",
            request_timeout=self.settings["request_timeout"],
            strip_punctuation=self.settings["strip_punctuation"],
        )
        return [
            TENTurnDetectionUserTurnStopStrategy(
                params=params,
                unfinished_timeout=self.settings["unfinished_timeout"],
                language=context.language,
            )
        ]
