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

from core.services.pipeline.service_factory import build_llm, build_stt, build_tts


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

    @dataclasses.dataclass
    class Settings:
        model: str = None
        voice: str = None
        language: str = None
        generation_config: object = None
        pronunciation_dict_id: str = None
        extra: dict = None

    def __init__(self, api_key=None, settings=None, **kwargs):
        self.api_key = api_key
        self.settings = settings
        self.kwargs = kwargs


class _FakeLiveOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeDeepgram:

    @dataclasses.dataclass
    class Settings:
        model: str = None
        language: str = None
        smart_format: bool = None
        diarize: bool = None
        utterance_end_ms: int = None
        extra: dict = None

    def __init__(self, api_key=None, settings=None, **kwargs):
        self.api_key = api_key
        self.settings = settings
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


class _FakeGroq:

    @dataclasses.dataclass
    class Settings:
        model: str = None
        temperature: float = None
        top_p: float = None
        seed: int = None
        max_completion_tokens: int = None
        extra: dict = None

    class InputParams(_FakeParams):
        model_fields = {
            "temperature": None, "top_p": None, "seed": None,
            "max_completion_tokens": None, "extra": None,
        }

    def __init__(self, api_key=None, settings=None, model=None, params=None, base_url=None):
        self.api_key = api_key
        self.settings = settings
        self.model = model
        self.params = params
        self.base_url = base_url


class _FakeOpenRouter(_FakeGroq):
    pass


class _FakeNvidia:
    """Stand-in for NvidiaSTTService, which selects models via `model_function_map`.

    Mirrors the real class's trap: it has no `model=` kwarg at all, so a branch
    passing only `model` leaves every agent on the class-default function id.
    """

    class InputParams(_FakeParams):
        model_fields = {"language": None}

    def __init__(self, api_key=None, params=None, model_function_map=None,
                 sample_rate=None, server=None, **kwargs):
        self.kwargs = kwargs
        self.api_key = api_key
        self.params = params
        self.model_function_map = model_function_map
        self.sample_rate = sample_rate
        self.server = server


class _FakeHostedTTS:

    def __init__(self, api_key=None, base_url=None, model=None, voice_id=None,
                 trace_id=None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.voice_id = voice_id
        self.kwargs = kwargs


class _FakeOpenAISTT:

    def __init__(self, api_key=None, model=None, language=None, prompt=None,
                 temperature=None, base_url=None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url


def _module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


class _FakeMistralSettings:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeMistralSTT:
    Settings = _FakeMistralSettings

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _fake_nvidia_language(language):
    """Mirror pipecat's mapper: bare codes resolve to a regional Riva code."""
    return {"en": "en-US", "es": "es-ES", "hi": "hi-IN"}.get(str(language), str(language))


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
        "pipecat.services.groq.llm": _module(
            "pipecat.services.groq.llm", GroqLLMService=_FakeGroq,
        ),
        "pipecat.services.openrouter.llm": _module(
            "pipecat.services.openrouter.llm", OpenRouterLLMService=_FakeOpenRouter,
        ),
        "pipecat.services.nvidia.stt": _module(
            "pipecat.services.nvidia.stt",
            NvidiaSTTService=_FakeNvidia,
            language_to_nvidia_nemotron_speech_language=_fake_nvidia_language,
        ),
        "pipecat.services.openai.stt": _module(
            "pipecat.services.openai.stt", OpenAISTTService=_FakeOpenAISTT,
        ),
        "pipecat.services.mistral.stt": _module(
            "pipecat.services.mistral.stt", MistralSTTService=_FakeMistralSTT,
        ),
        "core.services.pipeline.hosted_tts_service": _module(
            "core.services.pipeline.hosted_tts_service", HostedTTSService=_FakeHostedTTS,
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
    with _patched_modules():
        svc = build_stt(_spec("deepgram", model="nova-2-phonecall", metadata={
            "language": "en", "smart_format": True, "diarize": False,
            "filler_words": True, "utterance_end_ms": 1000,
        }))
    assert isinstance(svc, _FakeDeepgram)
    assert svc.settings.model == "nova-2-phonecall"
    assert svc.settings.language == "en"
    assert svc.settings.smart_format is True
    assert svc.settings.diarize is False
    assert svc.settings.utterance_end_ms == 1000
    assert svc.settings.extra == {"filler_words": True}


def test_deepgram_no_options_yields_no_settings():
    with _patched_modules():
        svc = build_stt(_spec("deepgram", model="", metadata={}))
    assert isinstance(svc, _FakeDeepgram)
    assert svc.settings is None


def test_anthropic_enables_thinking_from_budget():
    with _patched_modules():
        svc = build_llm(_spec("anthropic", model="claude-x", metadata={
            "temperature": 0.5, "thinking_budget_tokens": 2048,
        }))
    assert isinstance(svc, _FakeAnthropic)
    assert isinstance(svc.params.thinking, _FakeAnthropic.ThinkingConfig)
    assert svc.params.thinking.type == "enabled"
    assert svc.params.thinking.budget_tokens == 2048


def test_anthropic_no_thinking_when_budget_absent_or_zero():
    with _patched_modules():
        svc_absent = build_llm(_spec("anthropic", metadata={"temperature": 0.5}))
        svc_zero = build_llm(_spec("anthropic", metadata={"thinking_budget_tokens": 0}))
    assert svc_absent.params.thinking is None
    assert svc_zero.params.thinking is None


def test_cartesia_wires_speed_and_emotion_into_generation_config():
    with _patched_modules():
        svc = build_tts(_spec("cartesia", model="sonic-3", metadata={
            "speed": 1.1, "emotion": "happy",
        }))
    assert isinstance(svc, _FakeCartesia)
    assert svc.settings.model == "sonic-3"
    assert svc.settings.voice == "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
    assert isinstance(svc.settings.generation_config, _FakeGenerationConfig)
    assert svc.settings.generation_config.speed == 1.1
    assert svc.settings.generation_config.emotion == "happy"


def test_cartesia_without_speed_leaves_generation_config_unset():
    with _patched_modules():
        svc = build_tts(_spec("cartesia", model="sonic-3", metadata={}))
    assert isinstance(svc, _FakeCartesia)
    assert svc.settings.generation_config is None


def test_assemblyai_parses_comma_separated_keyterms():
    with _patched_modules():
        svc = build_stt(_spec("assemblyai", metadata={
            "keyterms_prompt": "acme corp, refund, billing",
        }))
    assert isinstance(svc, _FakeAssembly)
    assert svc.connection_params.kwargs["keyterms_prompt"] == [
        "acme corp", "refund", "billing",
    ]


def test_assemblyai_parses_json_list_keyterms():
    with _patched_modules():
        svc = build_stt(_spec("assemblyai", metadata={
            "keyterms_prompt": '["alpha", "beta"]',
        }))
    assert svc.connection_params.kwargs["keyterms_prompt"] == ["alpha", "beta"]


def test_sarvam_ai_forwards_model_and_settings_not_params():
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
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-105b",
                              metadata={"model": "sarvam-30b"}))
    # `model` is a structural key the resolver always passes through and also a
    # Settings field, so the resolved model row must win over the agent's copy.
    assert svc.settings.model == "sarvam-105b"


def test_sarvam_ai_falls_back_to_default_model():
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="", metadata={}))
    assert svc.settings.model == "sarvam-30b"


def test_sarvam_ai_forwards_base_url_from_model_row():
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-30b",
                              metadata={"base_url": "https://api.sarvam.ai/v1"}))
    assert svc.base_url == "https://api.sarvam.ai/v1"
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-30b", metadata={}))
    assert svc.base_url is None                   # class keeps its own default


def test_sarvam_ai_drops_unknown_metadata_fields():
    with _patched_modules():
        svc = build_llm(_spec("sarvam-ai", model="sarvam-30b", metadata={
            "temperature": 0.2, "not_a_sarvam_field": "x",
        }))
    assert svc is not None                        # one stray key must not kill the service
    assert svc.settings.temperature == 0.2


def test_groq_forwards_model_and_settings_not_params():
    with _patched_modules():
        svc = build_llm(_spec("groq", model="openai/gpt-oss-120b", metadata={
            "temperature": 0.3, "top_p": 0.9, "seed": 7, "max_completion_tokens": 4096,
        }))
    assert isinstance(svc, _FakeGroq)
    assert svc.params is None
    assert svc.model is None
    assert svc.settings.model == "openai/gpt-oss-120b"
    assert svc.settings.temperature == 0.3
    assert svc.settings.top_p == 0.9
    assert svc.settings.seed == 7
    assert svc.settings.max_completion_tokens == 4096


def test_groq_routes_reasoning_effort_into_settings_extra():
    with _patched_modules():
        svc = build_llm(_spec("groq", model="openai/gpt-oss-120b",
                              metadata={"temperature": 0.3, "reasoning_effort": "low"}))
    assert svc.settings.extra == {"reasoning_effort": "low"}
    assert svc.settings.temperature == 0.3
    assert not hasattr(svc.settings, "reasoning_effort")


def test_groq_routes_reasoning_format_into_extra_body():
    with _patched_modules():
        svc = build_llm(_spec("groq", model="qwen/qwen3.8-27b", metadata={
            "reasoning_effort": "none", "reasoning_format": "hidden",
        }))
    assert svc.settings.extra == {
        "reasoning_effort": "none",
        "extra_body": {"reasoning_format": "hidden"},
    }


def test_groq_leaves_extra_unset_without_reasoning_effort():
    with _patched_modules():
        svc = build_llm(_spec("groq", model="llama-3.3-70b-versatile",
                              metadata={"temperature": 0.5, "reasoning_effort": ""}))
    assert svc.settings.model == "llama-3.3-70b-versatile"
    assert svc.settings.extra is None


def test_groq_falls_back_to_default_model():
    with _patched_modules():
        svc = build_llm(_spec("groq", model="", metadata={}))
    assert svc.settings.model == "llama-3.3-70b-versatile"


def test_openrouter_forwards_settings_and_reasoning_effort():
    with _patched_modules():
        svc = build_llm(_spec("openrouter", model="qwen/qwen3-32b", metadata={
            "temperature": 0.2, "reasoning_effort": "medium", "base_url": "https://openrouter.ai/api/v1",
        }))
    assert isinstance(svc, _FakeOpenRouter)
    assert svc.params is None
    assert svc.settings.model == "qwen/qwen3-32b"
    assert svc.settings.temperature == 0.2
    assert svc.settings.extra == {"extra_body": {"reasoning": {"effort": "medium"}}}
    assert svc.base_url == "https://openrouter.ai/api/v1"


def test_openrouter_disables_thinking_through_reasoning_enabled():
    with _patched_modules():
        svc = build_llm(_spec("openrouter", model="z-ai/glm-4.7",
                              metadata={"reasoning_enabled": "false", "temperature": 0.7}))
    assert svc.settings.extra == {"extra_body": {"reasoning": {"enabled": False}}}
    assert svc.settings.temperature == 0.7


def test_openrouter_leaves_extra_unset_without_reasoning_fields():
    with _patched_modules():
        svc = build_llm(_spec("openrouter", model="meta-llama/llama-3.3-70b-instruct",
                              metadata={"temperature": 0.7, "reasoning_effort": ""}))
    assert svc.settings.extra is None


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


def test_nvidia_stt_forwards_function_id_and_model_name():
    with _patched_modules():
        svc = build_stt(_spec(
            "nvidia", "nvidia/Parakeet 0.6b TDT v2",
            model_meta={"function_id": "abc-123", "model_name": "parakeet-tdt-0.6b"},
        ))
    assert svc.model_function_map == {
        "function_id": "abc-123", "model_name": "parakeet-tdt-0.6b",
    }


def test_nvidia_stt_falls_back_to_model_name_when_only_function_id_given():
    with _patched_modules():
        svc = build_stt(_spec(
            "nvidia", "canary-1b", model_meta={"function_id": "def-456"},
        ))
    assert svc.model_function_map == {
        "function_id": "def-456", "model_name": "canary-1b",
    }


def test_nvidia_stt_omits_map_without_function_id():
    with _patched_modules():
        svc = build_stt(_spec("nvidia", "nvidia/Canary 1B"))
    assert svc.model_function_map is None


def test_nvidia_stt_forwards_sample_rate_and_server():
    with _patched_modules():
        svc = build_stt(_spec(
            "nvidia", "x",
            metadata={"sample_rate": 16000, "base_url": "grpc.example.com:443"},
            model_meta={"function_id": "f", "model_name": "m"},
        ))
    assert svc.sample_rate == 16000
    assert svc.server == "grpc.example.com:443"


def test_hosted_tts_forwards_fal_style_response_shape():
    with _patched_modules():
        svc = build_tts(_spec(
            "maya1", "maya1-3b", metadata={"voice_id": "v1"},
            model_meta={"base_url": "https://fal.run/fal-ai/maya",
                        "audio_url_field": "audio.url"},
        ))
    assert svc.base_url == "https://fal.run/fal-ai/maya"
    assert svc.kwargs["audio_url_field"] == "audio.url"
    assert svc.voice_id == "v1"


def test_hosted_tts_forwards_custom_auth_prefix_and_fields():
    with _patched_modules():
        svc = build_tts(_spec(
            "higgs-audio", "higgs-v2",
            model_meta={"base_url": "https://api.replicate.com/v1/predictions",
                        "auth_prefix": "Token ", "text_field": "input"},
        ))
    assert svc.kwargs["auth_prefix"] == "Token "
    assert svc.kwargs["text_field"] == "input"


def test_hosted_tts_forwards_extra_body_and_headers():
    with _patched_modules():
        svc = build_tts(_spec(
            "indextts", "indextts-2",
            model_meta={"base_url": "https://api.siliconflow.cn/v1/audio/speech",
                        "extra_body": {"response_format": "pcm"},
                        "extra_headers": {"X-Region": "in"}},
        ))
    assert svc.kwargs["extra_body"] == {"response_format": "pcm"}
    assert svc.kwargs["extra_headers"] == {"X-Region": "in"}


def test_hosted_tts_returns_none_without_base_url():
    with _patched_modules():
        svc = build_tts(_spec("maya1", "maya1-3b"))
    assert svc is None


def test_hosted_tts_voxtral_uses_base64_audio_field():
    with _patched_modules():
        svc = build_tts(_spec(
            "voxtral-hosted", "voxtral-mini-tts-2603", metadata={"voice_id": "en_paul_neutral"},
            model_meta={"base_url": "https://api.mistral.ai/v1/audio/speech",
                        "model_field": "model", "text_field": "input", "voice_field": "voice",
                        "audio_field": "audio_data", "strip_wav_header": True,
                        "extra_body": {"response_format": "wav"}},
        ))
    assert svc.base_url == "https://api.mistral.ai/v1/audio/speech"
    assert svc.kwargs["text_field"] == "input"
    assert svc.kwargs["audio_field"] == "audio_data"
    assert svc.kwargs["strip_wav_header"] is True
    assert svc.kwargs["extra_body"] == {"response_format": "wav"}
    assert svc.voice_id == "en_paul_neutral"


def test_hosted_tts_covers_deepinfra_qwen3():
    with _patched_modules():
        svc = build_tts(_spec(
            "qwen3-tts-hosted", "Qwen/Qwen3-TTS",
            model_meta={"base_url": "https://api.deepinfra.com/v1/inference/Qwen/Qwen3-TTS",
                        "audio_field": "audio"},
        ))
    assert svc.base_url == "https://api.deepinfra.com/v1/inference/Qwen/Qwen3-TTS"
    assert svc.kwargs["audio_field"] == "audio"


def test_openai_compatible_stt_covers_aggregators_with_base_url():
    with _patched_modules():
        svc = build_stt(_spec(
            "openrouter", "openai/whisper-large-v3",
            metadata={"base_url": "https://openrouter.ai/api/v1"},
        ))
    assert svc.base_url == "https://openrouter.ai/api/v1"
    assert svc.model == "openai/whisper-large-v3"


def test_openai_stt_without_base_url_uses_vendor_default():
    with _patched_modules():
        svc = build_stt(_spec("openai", "gpt-4o-transcribe"))
    assert svc.base_url is None


def test_mistral_stt_forwards_streaming_delay_and_base_url():
    with _patched_modules():
        svc = build_stt(_spec(
            "mistral", "voxtral-mini-transcribe-realtime-2602",
            metadata={"target_streaming_delay_ms": 250, "base_url": "https://self.hosted/v1"},
        ))
    assert svc.kwargs["target_streaming_delay_ms"] == 250
    assert svc.kwargs["base_url"] == "https://self.hosted/v1"
    assert svc.kwargs["settings"].kwargs["model"] == "voxtral-mini-transcribe-realtime-2602"


def test_mistral_stt_omits_streaming_delay_when_unset():
    with _patched_modules():
        svc = build_stt(_spec("mistral", "voxtral-mini-transcribe-realtime-2602"))
    assert "target_streaming_delay_ms" not in svc.kwargs
    assert "base_url" not in svc.kwargs


def test_nvidia_stt_forwards_endpointing_from_model_meta():
    with _patched_modules():
        svc = build_stt(_spec(
            "nvidia", "nvidia/Nemotron 3.5 ASR Streaming",
            model_meta={"function_id": "abc-123", "model_name": "nemotron-asr-streaming",
                        "stop_history": 120, "stop_threshold_eou": 0.5},
        ))
    assert svc.kwargs["stop_history"] == 120
    assert svc.kwargs["stop_threshold_eou"] == 0.5


def test_nvidia_stt_omits_endpointing_when_unset():
    with _patched_modules():
        svc = build_stt(_spec("nvidia", "x", model_meta={"function_id": "f", "model_name": "m"}))
    for key in ("start_history", "stop_history", "stop_threshold_eou"):
        assert key not in svc.kwargs


def test_nvidia_stt_coerces_endpointing_strings_from_ui():
    with _patched_modules():
        svc = build_stt(_spec(
            "nvidia", "nvidia/Parakeet 0.6b CTC",
            model_meta={"function_id": "f", "model_name": "m"},
            metadata={"stop_history": "160", "stop_threshold": "0.5"},
        ))
    assert svc.kwargs["stop_history"] == 160
    assert isinstance(svc.kwargs["stop_history"], int)
    assert svc.kwargs["stop_threshold"] == 0.5


def test_nvidia_stt_drops_blank_and_invalid_endpointing():
    with _patched_modules():
        svc = build_stt(_spec(
            "nvidia", "nvidia/Parakeet 0.6b CTC",
            model_meta={"function_id": "f", "model_name": "m"},
            metadata={"stop_history_eou": "", "start_history": "abc"},
        ))
    assert "stop_history_eou" not in svc.kwargs
    assert "start_history" not in svc.kwargs
