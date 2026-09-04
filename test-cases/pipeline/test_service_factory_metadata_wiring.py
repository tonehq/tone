"""Regression tests for provider metadata wiring in service_factory.

These cover four bugs where per-agent config values were saved + loaded correctly
but silently dropped at Pipecat-service construction time:

- Deepgram STT: selected model tier + transcription options were ignored (only
  `language` reached LiveOptions).
- Anthropic LLM: `thinking_budget_tokens` never enabled extended thinking (field
  name differs from Pipecat's structured `thinking` config).
- Cartesia TTS: numeric `speed`/`emotion` were dropped (they live under
  `generation_config`, not flat InputParams fields).
- AssemblyAI STT: `keyterms_prompt` was dropped.
- Sarvam LLM: the class is configured through `settings=` and lets it win over the
  deprecated `model=`/`params=` kwargs, so the usual branch shape would have pinned
  every agent to the default model with none of its tuning.

The real Pipecat package isn't importable in unit-test envs, so we inject
lightweight fakes for the exact modules each branch imports lazily, then assert the
values now reach the constructors. The fakes only record kwargs — no network I/O.
"""

import dataclasses
import sys
import types
from unittest import mock


# --- Fakes -----------------------------------------------------------------

class _FakeParams:
    """Minimal stand-in for a Pipecat InputParams pydantic model.

    Implements just what `build_input_params` and our translation code touch:
    a `model_fields` dict, a permissive constructor, and `model_copy(update=...)`.
    """

    model_fields: dict = {}

    def __init__(self, **kwargs):
        for key in type(self).model_fields:
            setattr(self, key, kwargs.get(key))

    def model_copy(self, update=None):
        import copy
        clone = copy.copy(self)
        for key, value in (update or {}).items():
            setattr(clone, key, value)
        return clone


class _FakeAnthropic:
    class ThinkingConfig:
        def __init__(self, type=None, budget_tokens=None):
            self.type = type
            self.budget_tokens = budget_tokens

    class InputParams(_FakeParams):
        model_fields = {
            "temperature": None, "top_p": None, "top_k": None, "max_tokens": None,
            "thinking": None, "enable_prompt_caching": None, "extra": None,
        }

    def __init__(self, api_key=None, model=None, params=None):
        self.api_key = api_key
        self.model = model
        self.params = params


class _FakeGenerationConfig:
    def __init__(self, speed=None, emotion=None, volume=None):
        self.speed = speed
        self.emotion = emotion
        self.volume = volume


class _FakeCartesia:
    class InputParams(_FakeParams):
        model_fields = {"generation_config": None}

    def __init__(self, api_key=None, model=None, params=None, **voice_kwargs):
        self.api_key = api_key
        self.model = model
        self.params = params
        self.voice_kwargs = voice_kwargs


class _FakeLiveOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeDeepgram:
    def __init__(self, api_key=None, live_options=None, **kwargs):
        self.api_key = api_key
        self.live_options = live_options
        self.kwargs = kwargs


class _FakeAssemblyConnectionParams:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeAssembly:
    def __init__(self, api_key=None, connection_params=None, language=None, **kwargs):
        self.api_key = api_key
        self.connection_params = connection_params
        self.language = language
        self.kwargs = kwargs


class _FakeSarvam:
    """Stand-in for SarvamLLMService, which is configured through `settings=`.

    Mirrors the real class's trap: it accepts the deprecated `model=`/`params=`
    kwargs but always lets `settings` win, so a branch passing the former loses
    every value with no error. `wiki_grounding` and `reasoning_effort` exist only
    on Settings, never on InputParams.
    """

    @dataclasses.dataclass
    class Settings:
        model: str = None
        temperature: float = None
        max_tokens: int = None
        top_p: float = None
        seed: int = None
        wiki_grounding: bool = None
        reasoning_effort: str = None

    class InputParams(_FakeParams):
        model_fields = {
            "temperature": None, "max_tokens": None, "top_p": None, "seed": None,
        }

    def __init__(self, api_key=None, settings=None, model=None, params=None, base_url=None):
        self.api_key = api_key
        self.settings = settings
        self.model = model
        self.params = params
        self.base_url = base_url


def _module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _patched_modules():
    """Inject fake Pipecat submodules for the imports done inside the factory."""
    return mock.patch.dict(sys.modules, {
        "pipecat.services.deepgram.stt": _module(
            "pipecat.services.deepgram.stt",
            DeepgramSTTService=_FakeDeepgram, LiveOptions=_FakeLiveOptions,
        ),
        "pipecat.services.anthropic.llm": _module(
            "pipecat.services.anthropic.llm", AnthropicLLMService=_FakeAnthropic,
        ),
        "pipecat.services.cartesia.tts": _module(
            "pipecat.services.cartesia.tts",
            CartesiaTTSService=_FakeCartesia, GenerationConfig=_FakeGenerationConfig,
        ),
        "pipecat.services.assemblyai.stt": _module(
            "pipecat.services.assemblyai.stt", AssemblyAISTTService=_FakeAssembly,
        ),
        "pipecat.services.sarvam.llm": _module(
            "pipecat.services.sarvam.llm", SarvamLLMService=_FakeSarvam,
        ),
        "pipecat.services.assemblyai.models": _module(
            "pipecat.services.assemblyai.models",
            AssemblyAIConnectionParams=_FakeAssemblyConnectionParams,
        ),
    })


def _spec(provider, model="", metadata=None, model_meta=None):
    return {
        "provider_name": provider,
        "api_key": "test-key",
        "model_name": model,
        "metadata": metadata or {},
        "model_meta_data": model_meta or {},
    }


# --- Tests -----------------------------------------------------------------

def test_deepgram_forwards_model_and_options():
    from core.services.pipeline.service_factory import build_stt
    with _patched_modules():
        svc = build_stt(_spec("deepgram", model="nova-2-phonecall", metadata={
            "language": "en", "smart_format": True, "diarize": False,
            "filler_words": True, "utterance_end_ms": 1000,
        }))
    assert isinstance(svc, _FakeDeepgram)
    lo = svc.live_options.kwargs
    assert lo["model"] == "nova-2-phonecall"      # was ignored before the fix
    assert lo["language"] == "en"
    assert lo["smart_format"] is True
    assert lo["diarize"] is False                 # False must survive (not treated as unset)
    assert lo["filler_words"] is True
    assert lo["utterance_end_ms"] == 1000


def test_deepgram_no_options_yields_no_live_options():
    from core.services.pipeline.service_factory import build_stt
    with _patched_modules():
        svc = build_stt(_spec("deepgram", model="", metadata={}))
    assert isinstance(svc, _FakeDeepgram)
    assert svc.live_options is None               # unchanged behavior when nothing is set


def test_anthropic_enables_thinking_from_budget():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc = build_llm(_spec("anthropic", model="claude-x", metadata={
            "temperature": 0.5, "thinking_budget_tokens": 2048,
        }))
    assert isinstance(svc, _FakeAnthropic)
    assert isinstance(svc.params.thinking, _FakeAnthropic.ThinkingConfig)
    assert svc.params.thinking.type == "enabled"
    assert svc.params.thinking.budget_tokens == 2048


def test_anthropic_no_thinking_when_budget_absent_or_zero():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc_absent = build_llm(_spec("anthropic", metadata={"temperature": 0.5}))
        svc_zero = build_llm(_spec("anthropic", metadata={"thinking_budget_tokens": 0}))
    assert svc_absent.params.thinking is None
    assert svc_zero.params.thinking is None


def test_cartesia_wires_speed_and_emotion_into_generation_config():
    from core.services.pipeline.service_factory import build_tts
    with _patched_modules():
        svc = build_tts(_spec("cartesia", model="sonic-3", metadata={
            "speed": 1.1, "emotion": "happy",
        }))
    assert isinstance(svc, _FakeCartesia)
    assert isinstance(svc.params.generation_config, _FakeGenerationConfig)
    assert svc.params.generation_config.speed == 1.1
    assert svc.params.generation_config.emotion == "happy"


def test_cartesia_without_speed_leaves_generation_config_unset():
    from core.services.pipeline.service_factory import build_tts
    with _patched_modules():
        svc = build_tts(_spec("cartesia", model="sonic-3", metadata={}))
    assert isinstance(svc, _FakeCartesia)
    assert getattr(svc.params, "generation_config", None) is None


def test_assemblyai_parses_comma_separated_keyterms():
    from core.services.pipeline.service_factory import build_stt
    with _patched_modules():
        svc = build_stt(_spec("assemblyai", metadata={
            "keyterms_prompt": "acme corp, refund, billing",
        }))
    assert isinstance(svc, _FakeAssembly)
    assert svc.connection_params.kwargs["keyterms_prompt"] == [
        "acme corp", "refund", "billing",
    ]


def test_assemblyai_parses_json_list_keyterms():
    from core.services.pipeline.service_factory import build_stt
    with _patched_modules():
        svc = build_stt(_spec("assemblyai", metadata={
            "keyterms_prompt": '["alpha", "beta"]',
        }))
    assert svc.connection_params.kwargs["keyterms_prompt"] == ["alpha", "beta"]


def test_sarvam_ai_forwards_model_and_settings_not_params():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-105b-32k", metadata={
            "temperature": 0.4, "max_tokens": 1024, "seed": 42,
            "wiki_grounding": True, "reasoning_effort": "high",
        }))
    assert isinstance(svc, _FakeSarvam)
    assert svc.params is None                     # the deprecated path must stay unused
    assert svc.settings.model == "sarvam-105b-32k"  # via params= this pinned the default
    assert svc.settings.temperature == 0.4
    assert svc.settings.max_tokens == 1024
    assert svc.settings.seed == 42
    assert svc.settings.wiki_grounding is True    # Settings-only, absent from InputParams
    assert svc.settings.reasoning_effort == "high"


def test_sarvam_ai_model_name_beats_stray_metadata_model():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-105b",
                              metadata={"model": "sarvam-30b"}))
    # `model` is a structural key the resolver always passes through and also a
    # Settings field, so the resolved model row must win over the agent's copy.
    assert svc.settings.model == "sarvam-105b"


def test_sarvam_ai_falls_back_to_default_model():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="", metadata={}))
    assert svc.settings.model == "sarvam-30b"


def test_sarvam_ai_forwards_base_url_from_model_row():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-30b",
                              metadata={"base_url": "https://api.sarvam.ai/v1"}))
    assert svc.base_url == "https://api.sarvam.ai/v1"
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-30b", metadata={}))
    assert svc.base_url is None                   # class keeps its own default


def test_sarvam_ai_drops_unknown_metadata_fields():
    from core.services.pipeline.service_factory import build_llm
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-30b", metadata={
            "temperature": 0.2, "not_a_sarvam_field": "x",
        }))
    assert svc is not None                        # one stray key must not kill the service
    assert svc.settings.temperature == 0.2


if __name__ == "__main__":
    # Allow running without pytest in constrained envs. Under pytest these come
    # from test-cases/conftest.py; mirror the minimum needed to import the package.
    import os
    for _k, _v in {
        "ENV": "test",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/tone_test",
        "JWT_SECRET_KEY": "test-jwt-secret-not-the-placeholder-value",
        "DEFAULT_ORG_ID": "00000000-0000-0000-0000-000000000001",
    }.items():
        os.environ.setdefault(_k, _v)

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 - test harness
            failed += 1
            print(f"FAIL {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
