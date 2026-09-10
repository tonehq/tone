from unittest import mock

import pytest
from fastapi import HTTPException

from core.config import settings
from core.processors.transcription_timeout_turn_stop import TranscriptionTimeoutUserTurnStopStrategy
from core.services.agent_service import AgentService
from core.services.pipeline import turn_detection as td
from core.services.pipeline.builder.pipecat import _build_turn_detection
from core.services.pipeline.params.base import PipelineParams
from core.services.pipeline.service_resolver import _turn_settings
from core.services.pipeline.turn_detection import livekit, smart_turn, ten


class _Recorder:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__dict__.update(kwargs)


@pytest.fixture
def fake_pipecat(monkeypatch):
    monkeypatch.setattr(smart_turn, "LocalSmartTurnAnalyzerV3", _Recorder)
    monkeypatch.setattr(smart_turn, "SmartTurnParams", _Recorder)
    monkeypatch.setattr(smart_turn, "TurnAnalyzerUserTurnStopStrategy", _Recorder)
    monkeypatch.setattr(ten, "TENTurnDetectionParams", _Recorder)
    monkeypatch.setattr(ten, "TENTurnDetectionUserTurnStopStrategy", _Recorder)
    monkeypatch.setattr(livekit, "LiveKitTurnDetectorParams", _Recorder)
    monkeypatch.setattr(livekit, "LiveKitTurnDetectorUserTurnStopStrategy", _Recorder)


def test_registry_and_catalog():
    assert set(td.TURN_DETECTORS) == {"smart_turn", "ten", "livekit"}
    assert td.DEFAULT_TURN_DETECTOR == "smart_turn"
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", ""):
        assert [c["id"] for c in td.list_turn_detectors()] == ["smart_turn", "livekit"]
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", "http://ten.local/v1"):
        catalog = td.list_turn_detectors()
    assert [c["id"] for c in catalog] == ["smart_turn", "ten", "livekit"]
    for entry in catalog:
        assert entry["display_name"] and entry["description"]
        assert all("name" in f and "data_type" in f for f in entry["meta_data_schema"])


def test_default_detector_uses_schema_defaults():
    detector = td.get_turn_detector(None)
    assert detector.slug == "smart_turn"
    assert detector.settings == {"confidence_threshold": 0.7, "stop_secs": 0.8}
    assert detector.fallback_timeout_secs == 0.6


def test_settings_are_coerced_from_strings_and_blanks():
    detector = td.get_turn_detector(
        {"provider": "livekit", "max_history_turns": "4", "threshold": "", "unfinished_timeout": "2.5"}
    )
    assert detector.settings["max_history_turns"] == 4
    assert detector.settings["threshold"] is None
    assert detector.settings["unfinished_timeout"] == 2.5
    assert detector.settings["model_type"] == "multilingual"
    assert detector.fallback_timeout_secs is None

    detector = td.get_turn_detector({"provider": "ten", "strip_punctuation": "false"})
    assert detector.settings["strip_punctuation"] is False


def test_unknown_provider_fails_fast():
    with pytest.raises(ValueError, match="Unknown turn detector"):
        td.get_turn_detector({"provider": "nope"})


def test_validate_turn_detection():
    assert td.validate_turn_detection({"provider": "smart_turn", "stop_secs": 1.2}) == {}
    assert td.validate_turn_detection({}) == {}
    assert "provider" in td.validate_turn_detection({"provider": "nope"})
    assert "provider" in td.validate_turn_detection("smart_turn")
    errors = td.validate_turn_detection({"provider": "smart_turn", "confidence_threshold": 5})
    assert errors == {"confidence_threshold": ["confidence_threshold must be at most 1"]}
    errors = td.validate_turn_detection(
        {"provider": "livekit", "model_type": "xx", "max_history_turns": 0}
    )
    assert set(errors) == {"model_type", "max_history_turns"}


def test_ten_is_selectable_only_when_endpoint_configured():
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", ""):
        errors = td.validate_turn_detection({"provider": "ten"})
    assert errors == {"provider": ["provider must be one of: smart_turn, livekit"]}
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", "http://ten.local/v1"):
        assert td.validate_turn_detection({"provider": "ten"}) == {}
        errors = td.validate_turn_detection({"provider": "ten", "strip_punctuation": "yes"})
    assert errors == {"strip_punctuation": ["strip_punctuation must be true or false"]}


def test_smart_turn_build_passes_tuning(fake_pipecat):
    strategies, detector = td.build_user_turn_stop_strategies(
        {"provider": "smart_turn", "confidence_threshold": 0.55, "stop_secs": 1.1},
        td.TurnDetectionContext(),
    )
    assert detector.slug == "smart_turn"
    assert len(strategies) == 1
    analyzer = strategies[0].turn_analyzer
    assert analyzer.confidence_threshold == 0.55
    assert analyzer.params.kwargs == {"stop_secs": 1.1}


def test_ten_build_requires_endpoint(fake_pipecat):
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", ""):
        with pytest.raises(ValueError, match="TEN_TURN_DETECTION_BASE_URL"):
            td.build_user_turn_stop_strategies({"provider": "ten"}, td.TurnDetectionContext())


def test_ten_build_uses_server_endpoint_and_agent_tuning(fake_pipecat):
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", "http://ten.local/v1"), \
            mock.patch.object(settings, "TEN_TURN_DETECTION_API_KEY", "key"), \
            mock.patch.object(settings, "TEN_TURN_DETECTION_MODEL", ""):
        strategies, detector = td.build_user_turn_stop_strategies(
            {"provider": "ten", "unfinished_timeout": 4, "request_timeout": 1.5, "strip_punctuation": False},
            td.TurnDetectionContext(language="en"),
        )
    assert len(strategies) == 1
    strategy = strategies[0]
    assert strategy.unfinished_timeout == 4.0
    assert strategy.language == "en"
    assert strategy.params.kwargs == {
        "base_url": "http://ten.local/v1",
        "api_key": "key",
        "model": "TEN_Turn_Detection",
        "request_timeout": 1.5,
        "strip_punctuation": False,
    }
    assert detector.fallback_timeout_secs is None


def test_livekit_build_passes_context_and_language(fake_pipecat):
    llm_context = object()
    strategies, _ = td.build_user_turn_stop_strategies(
        {"provider": "livekit", "model_type": "en", "threshold": 0.02, "language": "hi", "max_history_turns": 3},
        td.TurnDetectionContext(llm_context=llm_context, language="en"),
    )
    assert len(strategies) == 1
    strategy = strategies[0]
    assert strategy.context is llm_context
    assert strategy.language == "hi"
    assert strategy.unfinished_timeout == 3.0
    assert strategy.params.kwargs == {"model_type": "en", "threshold": 0.02, "max_history_turns": 3}


def test_builder_appends_transcription_fallback_only_for_audio_detectors(fake_pipecat):
    strategies, detector = _build_turn_detection(None, object(), "en")
    assert detector.slug == "smart_turn"
    assert isinstance(strategies[-1], TranscriptionTimeoutUserTurnStopStrategy)
    assert strategies[-1]._timeout == 0.6

    strategies, detector = _build_turn_detection({"provider": "livekit"}, object(), None)
    assert detector.slug == "livekit"
    assert len(strategies) == 1


def test_builder_reraises_bad_provider(fake_pipecat):
    with pytest.raises(ValueError):
        _build_turn_detection({"provider": "nope"}, object(), None)


def test_pipeline_params_carry_turn_settings():
    payload = {"turn_detection": {"provider": "ten"}, "vad": {"stop_secs": 0.3}}
    params = PipelineParams.from_cache_dict({"llm": {}, "turn_settings": payload})
    assert params.turn_settings == payload
    assert PipelineParams.from_cache_dict({"llm": {}}).turn_settings is None


def test_resolver_reads_turn_settings_column():
    config = mock.Mock(turn_settings={"turn_detection": {"provider": "livekit"}, "vad": {}})
    assert _turn_settings(config) == {"turn_detection": {"provider": "livekit"}, "vad": {}}
    assert _turn_settings(mock.Mock(turn_settings=None)) is None
    assert _turn_settings(mock.Mock(turn_settings="livekit")) is None


def test_agent_service_rejects_invalid_turn_settings():
    service = AgentService(mock.MagicMock(), org_id="00000000-0000-0000-0000-000000000001")
    service._validate_turn_settings({"turn_settings": {"turn_detection": {"provider": "smart_turn"}}})
    service._validate_turn_settings({"turn_settings": {"vad": {"stop_secs": 0.4}}})
    service._validate_turn_settings({"conversation_settings": {"max_duration_seconds": 10}})
    service._validate_turn_settings({})
    with pytest.raises(HTTPException) as exc:
        service._validate_turn_settings(
            {
                "turn_settings": {
                    "turn_detection": {"provider": "livekit", "max_history_turns": 99},
                    "vad": {"confidence": 3},
                }
            }
        )
    assert exc.value.status_code == 400
    assert exc.value.detail["errors"]["turn_settings"] == {
        "turn_detection": {"max_history_turns": ["max_history_turns must be at most 20"]},
        "vad": {"confidence": ["confidence must be at most 1"]},
    }


def test_livekit_is_hidden_when_the_container_memory_limit_is_too_small(monkeypatch):
    monkeypatch.setattr(livekit, "memory_usage", lambda: (300.0, 1024.0))
    livekit._host_has_memory.cache_clear()
    with mock.patch.object(settings, "TEN_TURN_DETECTION_BASE_URL", ""):
        assert [c["id"] for c in td.list_turn_detectors()] == ["smart_turn"]
    assert "provider" in td.validate_turn_detection({"provider": "livekit"})
    with pytest.raises(ValueError, match="1536 MiB"):
        td.get_turn_detector({"provider": "livekit"}).build(td.TurnDetectionContext())
    livekit._host_has_memory.cache_clear()


def test_livekit_memory_gate_respects_the_configured_minimum_and_unlimited_hosts(monkeypatch):
    monkeypatch.setattr(livekit, "memory_usage", lambda: (300.0, 1024.0))
    with mock.patch.object(settings, "LIVEKIT_TURN_DETECTOR_MIN_MEMORY_MIB", 1000):
        livekit._host_has_memory.cache_clear()
        assert livekit.LiveKitTurnDetector.available() is True
    monkeypatch.setattr(livekit, "memory_usage", lambda: (None, None))
    livekit._host_has_memory.cache_clear()
    assert livekit.LiveKitTurnDetector.available() is True
    livekit._host_has_memory.cache_clear()
