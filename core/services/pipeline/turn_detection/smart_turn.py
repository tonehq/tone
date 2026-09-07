from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy

from core.services.pipeline.turn_detection.base import TurnDetectionContext, TurnDetector


class SmartTurnDetector(TurnDetector):
    slug = "smart_turn"
    display_name = "Smart Turn v3"
    description = "Pipecat's local audio end-of-turn model. Runs on CPU with no external service."
    schema = [
        {
            "name": "confidence_threshold",
            "data_type": "float",
            "type": "input number",
            "format": "float",
            "validator": {"min": 0.1, "max": 1},
            "required": 0,
            "default": 0.7,
            "description": "Probability above which the model treats the turn as complete",
        },
        {
            "name": "stop_secs",
            "data_type": "float",
            "type": "input number",
            "format": "float",
            "validator": {"min": 0.1, "max": 3},
            "required": 0,
            "default": 0.8,
            "description": "Silence in seconds that ends the turn when the model stays undecided",
        },
    ]

    @property
    def fallback_timeout_secs(self) -> float:
        return 0.6

    def build(self, context: TurnDetectionContext) -> list:
        analyzer = LocalSmartTurnAnalyzerV3(
            confidence_threshold=self.settings["confidence_threshold"],
            params=SmartTurnParams(stop_secs=self.settings["stop_secs"]),
        )
        return [TurnAnalyzerUserTurnStopStrategy(turn_analyzer=analyzer)]
