import importlib
import sys
import types
from unittest import mock

import numpy as np
import pytest
from pipecat.audio.vad.vad_analyzer import VADParams

from core.config import settings
from core.services.pipeline import vad as vad_registry
from core.services.pipeline.vad import aic_quail, krisp, silero, ten


class _Recorder:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def all_sdks_present(monkeypatch):
    monkeypatch.setattr(ten, "TENVADAnalyzer", _Recorder)
    monkeypatch.setattr(krisp, "KrispVivaVadAnalyzer", _Recorder)
    monkeypatch.setattr(aic_quail, "AICQuailVADAnalyzer", _Recorder)


def test_registry_and_catalog():
    assert set(vad_registry.VAD_PROVIDERS) == {"silero", "ten", "krisp_viva", "aic_quail"}
    assert vad_registry.DEFAULT_VAD_PROVIDER == "silero"
    for cls in vad_registry.VAD_PROVIDERS.values():
        assert cls.display_name and cls.description
        assert all("name" in f and "data_type" in f for f in cls.schema)


def test_default_provider_builds_silero_with_the_pipeline_params(monkeypatch):
    monkeypatch.setattr(silero, "SileroVADAnalyzer", _Recorder)
    params = VADParams(confidence=0.6, stop_secs=0.3)
    analyzer = vad_registry.build_vad_analyzer(None, params)
    assert analyzer.kwargs == {"params": params}
    assert vad_registry.get_vad_provider({}).describe() == {"provider": "silero"}


def test_unknown_provider_fails_fast():
    with pytest.raises(ValueError, match="Unknown VAD provider"):
        vad_registry.get_vad_provider({"provider": "nope"})


def test_catalog_offers_only_providers_whose_sdk_and_config_are_present(all_sdks_present):
    with mock.patch.object(settings, "KRISP_VIVA_VAD_MODEL_PATH", ""), \
            mock.patch.object(settings, "AIC_SDK_LICENSE", ""):
        assert [c["id"] for c in vad_registry.list_vad_providers()] == ["silero", "ten"]
    with mock.patch.object(settings, "KRISP_VIVA_API_KEY", "krisp-key"), \
            mock.patch.object(settings, "KRISP_VIVA_VAD_MODEL_PATH", "/models/vad.kef"), \
            mock.patch.object(settings, "AIC_SDK_LICENSE", "key"):
        catalog = vad_registry.list_vad_providers()
    assert [c["id"] for c in catalog] == ["silero", "ten", "krisp_viva", "aic_quail"]
    assert catalog[1]["meta_data_schema"][0]["name"] == "hop_size"


def test_missing_sdk_hides_the_provider(monkeypatch):
    monkeypatch.setattr(ten, "TENVADAnalyzer", None)
    assert [c["id"] for c in vad_registry.list_vad_providers()] == ["silero"]
    with pytest.raises(ValueError, match="ten-vad"):
        vad_registry.build_vad_analyzer({"provider": "ten"}, VADParams())


def test_ten_settings_are_coerced_and_forwarded(all_sdks_present):
    params = VADParams()
    analyzer = vad_registry.build_vad_analyzer({"provider": "ten", "hop_size": "160"}, params)
    assert analyzer.kwargs == {"hop_size": 160, "params": params}
    analyzer = vad_registry.build_vad_analyzer({"provider": "ten", "hop_size": ""}, params)
    assert analyzer.kwargs["hop_size"] == 256


def test_krisp_and_aic_take_their_credentials_from_server_config(all_sdks_present):
    params = VADParams()
    with mock.patch.object(settings, "KRISP_VIVA_API_KEY", "krisp-key"), \
            mock.patch.object(settings, "KRISP_VIVA_VAD_MODEL_PATH", "/models/vad.kef"):
        analyzer = vad_registry.build_vad_analyzer({"provider": "krisp_viva", "frame_duration": "20"}, params)
    assert analyzer.kwargs == {"model_path": "/models/vad.kef", "frame_duration": 20, "params": params}
    with mock.patch.object(settings, "AIC_SDK_LICENSE", "key"):
        analyzer = vad_registry.build_vad_analyzer({"provider": "aic_quail", "model_id": ""}, params)
    assert analyzer.kwargs == {"license_key": "key", "model_id": "quail-vad-2.0-xxs-16khz", "params": params}
    with mock.patch.object(settings, "KRISP_VIVA_VAD_MODEL_PATH", ""):
        with pytest.raises(ValueError, match="KRISP_VIVA_VAD_MODEL_PATH"):
            vad_registry.build_vad_analyzer({"provider": "krisp_viva"}, params)


def test_validate_vad_provider(all_sdks_present):
    assert vad_registry.validate_vad_provider({}) == {}
    assert vad_registry.validate_vad_provider({"provider": "ten", "hop_size": "160"}) == {}
    assert "provider" in vad_registry.validate_vad_provider({"provider": "nope"})
    assert "provider" in vad_registry.validate_vad_provider("silero")
    assert "hop_size" in vad_registry.validate_vad_provider({"provider": "ten", "hop_size": "100"})
    with mock.patch.object(settings, "KRISP_VIVA_VAD_MODEL_PATH", ""):
        assert "provider" in vad_registry.validate_vad_provider({"provider": "krisp_viva"})


def _load_ten_analyzer_with_fake_sdk(monkeypatch, probability):
    fake = types.ModuleType("ten_vad")

    class FakeTenVad:
        def __init__(self, hop_size, threshold):
            self.hop_size = hop_size
            self.threshold = threshold
            self.frames = []

        def process(self, audio):
            self.frames.append(audio)
            return probability, int(probability >= self.threshold)

    fake.TenVad = FakeTenVad
    monkeypatch.setitem(sys.modules, "ten_vad", fake)
    sys.modules.pop("core.processors.ten_vad_analyzer", None)
    return importlib.import_module("core.processors.ten_vad_analyzer")


def test_ten_analyzer_returns_the_model_probability_at_16k(monkeypatch):
    module = _load_ten_analyzer_with_fake_sdk(monkeypatch, 0.9)
    analyzer = module.TENVADAnalyzer(hop_size=256, params=VADParams())
    analyzer.set_sample_rate(16000)
    assert analyzer.num_frames_required() == 256
    assert analyzer.voice_confidence(np.ones(256, dtype=np.int16).tobytes()) == 0.9
    assert analyzer._model.hop_size == 256
    assert len(analyzer._model.frames[0]) == 256


def test_ten_analyzer_upsamples_telephony_audio_to_the_model_rate(monkeypatch):
    module = _load_ten_analyzer_with_fake_sdk(monkeypatch, 0.4)
    analyzer = module.TENVADAnalyzer(hop_size=256, params=VADParams())
    analyzer.set_sample_rate(8000)
    assert analyzer.num_frames_required() == 128
    ramp = np.arange(128, dtype=np.int16) * 100
    assert analyzer.voice_confidence(ramp.tobytes()) == 0.4
    frame = analyzer._model.frames[0]
    assert len(frame) == 256
    assert frame.dtype == np.int16
    assert frame[2] == ramp[1]
    assert frame[1] == (ramp[0] + ramp[1]) // 2


def test_ten_analyzer_rejects_unsupported_sample_rates(monkeypatch):
    module = _load_ten_analyzer_with_fake_sdk(monkeypatch, 0.5)
    analyzer = module.TENVADAnalyzer(hop_size=256, params=VADParams())
    with pytest.raises(ValueError, match="TEN VAD sample rate"):
        analyzer.set_sample_rate(24000)
    analyzer.set_sample_rate(16000)
    assert analyzer.voice_confidence(b"") == 0.0
