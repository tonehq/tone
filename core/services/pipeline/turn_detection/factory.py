from typing import Any, Dict, List, Optional, Tuple, Type

from core.services.meta_data_schema_validator import MetaDataSchemaValidator
from core.services.pipeline.turn_detection.base import TurnDetectionContext, TurnDetector
from core.services.pipeline.turn_detection.livekit import LiveKitTurnDetector
from core.services.pipeline.turn_detection.smart_turn import SmartTurnDetector
from core.services.pipeline.turn_detection.ten import TENTurnDetector

TURN_DETECTORS: Dict[str, Type[TurnDetector]] = {
    cls.slug: cls for cls in (SmartTurnDetector, TENTurnDetector, LiveKitTurnDetector)
}

DEFAULT_TURN_DETECTOR = SmartTurnDetector.slug

PROVIDER_KEY = "provider"

_COERCERS = {
    "float": float,
    "integer": lambda v: int(float(v)),
    "int": lambda v: int(float(v)),
    "boolean": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in ("true", "1", "yes"),
}


def _resolve_settings(schema: List[dict], raw: dict) -> dict:
    resolved = {}
    for field in schema:
        name = field["name"]
        value = raw.get(name)
        if value is None or value == "":
            value = field.get("default")
        if value is not None:
            coerce = _COERCERS.get(field.get("data_type"))
            if coerce:
                value = coerce(value)
        resolved[name] = value
    return resolved


def _detector_class(raw: Optional[dict]) -> Type[TurnDetector]:
    slug = (raw or {}).get(PROVIDER_KEY) or DEFAULT_TURN_DETECTOR
    try:
        return TURN_DETECTORS[slug]
    except KeyError:
        raise ValueError(
            f"Unknown turn detector: {slug!r}. Available: {sorted(TURN_DETECTORS)}"
        )


def get_turn_detector(raw: Optional[dict]) -> TurnDetector:
    cls = _detector_class(raw)
    return cls(_resolve_settings(cls.schema, raw or {}))


def build_user_turn_stop_strategies(
    raw: Optional[dict], context: TurnDetectionContext
) -> Tuple[list, TurnDetector]:
    detector = get_turn_detector(raw)
    return detector.build(context), detector


def available_turn_detectors() -> Dict[str, Type[TurnDetector]]:
    return {slug: cls for slug, cls in TURN_DETECTORS.items() if cls.available()}


def list_turn_detectors() -> List[dict]:
    return [
        {
            "id": cls.slug,
            "display_name": cls.display_name,
            "description": cls.description,
            "meta_data_schema": cls.schema,
        }
        for cls in available_turn_detectors().values()
    ]


def validate_turn_detection(raw: Any) -> Dict[str, List[str]]:
    if not isinstance(raw, dict):
        return {PROVIDER_KEY: ["turn_detection must be an object"]}
    slug = raw.get(PROVIDER_KEY) or DEFAULT_TURN_DETECTOR
    available = available_turn_detectors()
    cls = available.get(slug)
    if cls is None:
        return {PROVIDER_KEY: [f"provider must be one of: {', '.join(available)}"]}
    return MetaDataSchemaValidator().validate_settings(cls.schema, raw)
