from typing import Any, Dict, List, Optional

from core.services.meta_data_schema_validator import MetaDataSchemaValidator, coerce_settings
from core.services.pipeline.turn_detection import (
    DEFAULT_TURN_DETECTOR,
    list_turn_detectors,
    validate_turn_detection,
)
from core.services.pipeline.vad import (
    DEFAULT_VAD_PROVIDER,
    PROVIDER_KEY,
    list_vad_providers,
    validate_vad_provider,
)

TURN_DETECTION_KEY = "turn_detection"
VAD_KEY = "vad"

VAD_SCHEMA: List[dict] = [
    {
        "name": "confidence",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0.3, "max": 1},
        "required": 0,
        "default": 0.7,
        "description": "Speech probability above which audio counts as the caller talking",
    },
    {
        "name": "start_secs",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0.1, "max": 2},
        "required": 0,
        "default": 0.2,
        "description": "Seconds of continuous speech before the caller counts as speaking",
    },
    {
        "name": "stop_secs",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0.1, "max": 3},
        "required": 0,
        "default": 0.2,
        "description": "Seconds of silence before the caller counts as done speaking",
    },
    {
        "name": "min_volume",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0, "max": 1},
        "required": 0,
        "default": 0.6,
        "description": "Minimum audio level for speech detection",
    },
    {
        "name": "speaking_max_secs",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 3, "max": 60},
        "required": 0,
        "default": 8.0,
        "description": "Longest continuous speech before the pipeline forces a stop on noisy lines",
    },
]


def resolve_vad(raw: Optional[dict]) -> dict:
    source = raw if isinstance(raw, dict) else {}
    return {
        PROVIDER_KEY: source.get(PROVIDER_KEY) or DEFAULT_VAD_PROVIDER,
        **coerce_settings(VAD_SCHEMA, source),
    }


def turn_settings_options() -> dict:
    return {
        "turn_detectors": list_turn_detectors(),
        "default_turn_detector": DEFAULT_TURN_DETECTOR,
        "vad_providers": list_vad_providers(),
        "default_vad_provider": DEFAULT_VAD_PROVIDER,
        "vad_schema": VAD_SCHEMA,
    }


def _validate_vad(raw: Any) -> Dict[str, List[str]]:
    if not isinstance(raw, dict):
        return {VAD_KEY: ["vad must be an object"]}
    errors = MetaDataSchemaValidator().validate_settings(VAD_SCHEMA, raw)
    errors.update(validate_vad_provider(raw))
    return errors


def validate_turn_settings(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"turn_settings": ["turn_settings must be an object"]}
    errors: Dict[str, Any] = {}
    turn_detection = raw.get(TURN_DETECTION_KEY)
    if turn_detection is not None:
        detection_errors = validate_turn_detection(turn_detection)
        if detection_errors:
            errors[TURN_DETECTION_KEY] = detection_errors
    vad = raw.get(VAD_KEY)
    if vad is not None:
        vad_errors = _validate_vad(vad)
        if vad_errors:
            errors[VAD_KEY] = vad_errors
    return errors
