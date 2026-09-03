"""Regression tests: never send both `max_tokens` and `max_completion_tokens`.

Bug: Cohere's OpenAI-compat endpoint rejects a request that carries both
token-limit fields ("setting max_tokens and max_completion_tokens at the same
time is not supported"). Pipecat's OpenAI-family `InputParams` expose BOTH
fields and default `max_tokens` to a non-``None`` value, so when the agent
config set the schema's single field (e.g. `max_completion_tokens`) the built
params object still carried the defaulted `max_tokens` and Pipecat serialized
both.

`build_input_params` now de-dupes: the token-limit field the agent config
actually set wins, and the defaulted counterpart is nulled so it isn't sent.
The fix is conservative — it only clears the counterpart of a field the user
explicitly set, and only for services that expose BOTH fields (Cohere / OpenAI
/ Groq etc.); single-field services (Anthropic / Google) are untouched.

The real Pipecat package isn't importable in unit-test envs, so we inject
lightweight fakes that mimic just what `build_input_params` touches: a
`model_fields` dict, a permissive constructor with pipecat's non-``None``
`max_tokens` default, and `model_copy(update=...)`.
"""

import copy

from core.services.pipeline.service_factory import build_input_params


class _OpenAIFamilyParams:
    """OpenAI-family InputParams: BOTH token fields; `max_tokens` defaults to a
    non-``None`` value (mirrors the pipecat default that caused the double-send)."""

    model_fields = {
        "temperature": None,
        "max_tokens": None,
        "max_completion_tokens": None,
    }

    def __init__(self, **kwargs):
        self.temperature = kwargs.get("temperature")
        self.max_tokens = kwargs.get("max_tokens", 4096)
        self.max_completion_tokens = kwargs.get("max_completion_tokens")

    def model_copy(self, update=None):
        clone = copy.copy(self)
        for key, value in (update or {}).items():
            setattr(clone, key, value)
        return clone


class _OpenAIFamilyService:
    InputParams = _OpenAIFamilyParams


class _SingleFieldParams:
    """Anthropic/Google-style InputParams: only `max_tokens` exists."""

    model_fields = {"temperature": None, "max_tokens": None}

    def __init__(self, **kwargs):
        self.temperature = kwargs.get("temperature")
        self.max_tokens = kwargs.get("max_tokens", 4096)

    def model_copy(self, update=None):
        clone = copy.copy(self)
        for key, value in (update or {}).items():
            setattr(clone, key, value)
        return clone


class _SingleFieldService:
    InputParams = _SingleFieldParams


def test_max_completion_tokens_nulls_defaulted_max_tokens():
    # Cohere / OpenAI / Groq schemas expose max_completion_tokens only.
    params = build_input_params(_OpenAIFamilyService, {"max_completion_tokens": 512})
    assert params.max_completion_tokens == 512
    assert params.max_tokens is None  # defaulted counterpart nulled → not serialized


def test_max_tokens_nulls_defaulted_max_completion_tokens():
    # Perplexity / Qwen / DeepSeek (OpenAI-family, schema uses max_tokens).
    params = build_input_params(_OpenAIFamilyService, {"max_tokens": 1024})
    assert params.max_tokens == 1024
    assert params.max_completion_tokens is None


def test_single_field_service_is_untouched():
    # Anthropic / Google: only max_tokens exists → no dedup, value preserved.
    params = build_input_params(_SingleFieldService, {"max_tokens": 2048})
    assert params.max_tokens == 2048
    assert not hasattr(params, "max_completion_tokens")


def test_neither_token_field_set_leaves_defaults():
    # User set neither → conservative no-op: pipecat defaults preserved exactly
    # as before (only max_tokens' default is sent, which every provider accepts).
    params = build_input_params(_OpenAIFamilyService, {"temperature": 0.5})
    assert params.max_tokens == 4096
    assert params.max_completion_tokens is None


def test_both_set_is_left_to_the_provider():
    # Both explicitly set can only happen via a mis-built schema; the helper does
    # not guess which to drop (kept conservative). Schema-level fix removes the
    # only source of this (openrouter openai/* models).
    params = build_input_params(
        _OpenAIFamilyService, {"max_tokens": 1024, "max_completion_tokens": 512}
    )
    assert params.max_tokens == 1024
    assert params.max_completion_tokens == 512
