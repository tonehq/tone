from unittest import mock

from core.config import settings
from core.services.pipeline.vad import ten
from core.services.pipeline.turn_settings import (
    TURN_DETECTION_KEY,
    VAD_KEY,
    VAD_SCHEMA,
    resolve_vad,
    turn_settings_options,
    validate_turn_settings,
)


def test_vad_defaults_match_previous_hardcoded_pipeline_values():
    assert resolve_vad(None) == {
        "provider": "silero",
        "confidence": 0.7,
        "start_secs": 0.2,
        "stop_secs": 0.2,
        "min_volume": 0.6,
        "speaking_max_secs": 8.0,
    }


def test_vad_coerces_strings_and_fills_blanks():
    vad = resolve_vad({"stop_secs": "0.35", "speaking_max_secs": "", "confidence": 0.5})
    assert vad["stop_secs"] == 0.35
    assert vad["speaking_max_secs"] == 8.0
    assert vad["confidence"] == 0.5
    assert vad["provider"] == "silero"
    assert resolve_vad({"provider": "ten"})["provider"] == "ten"
    assert resolve_vad("garbage") == resolve_vad(None)


def test_options_expose_detectors_vad_providers_and_vad_schema():
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", ""), \
            mock.patch.object(ten, "TENVADAnalyzer", None):
        options = turn_settings_options()
    assert [d["id"] for d in options["turn_detectors"]] == ["smart_turn", "livekit"]
    assert options["default_turn_detector"] == "smart_turn"
    assert [p["id"] for p in options["vad_providers"]] == ["silero"]
    assert options["default_vad_provider"] == "silero"
    assert options["vad_schema"] is VAD_SCHEMA
    assert [f["name"] for f in VAD_SCHEMA] == [
        "confidence",
        "start_secs",
        "stop_secs",
        "min_volume",
        "speaking_max_secs",
    ]


def test_validate_turn_settings():
    assert validate_turn_settings({}) == {}
    assert validate_turn_settings({TURN_DETECTION_KEY: {"provider": "smart_turn"}, VAD_KEY: {}}) == {}
    assert validate_turn_settings({VAD_KEY: {"provider": "silero", "stop_secs": 0.3}}) == {}
    assert validate_turn_settings([]) == {"turn_settings": ["turn_settings must be an object"]}
    errors = validate_turn_settings(
        {TURN_DETECTION_KEY: {"provider": "nope"}, VAD_KEY: {"start_secs": 0, "min_volume": 2}}
    )
    assert "provider" in errors[TURN_DETECTION_KEY]
    assert set(errors[VAD_KEY]) == {"start_secs", "min_volume"}
    assert "provider" in validate_turn_settings({VAD_KEY: {"provider": "nope"}})[VAD_KEY]
    assert validate_turn_settings({VAD_KEY: "fast"}) == {VAD_KEY: {"vad": ["vad must be an object"]}}


def test_vad_bounds_reject_values_that_cancel_turns():
    errors = validate_turn_settings(
        {VAD_KEY: {"confidence": 0.1, "start_secs": 0.05, "stop_secs": 0.05, "speaking_max_secs": 1}}
    )
    assert set(errors[VAD_KEY]) == {"confidence", "start_secs", "stop_secs", "speaking_max_secs"}
