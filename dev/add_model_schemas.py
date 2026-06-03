"""
Add per-model meta_data_schema to dev-data.json for LLM providers.

This script reads dev-data.json, adds a `meta_data_schema` array to each LLM model
based on the params that model actually supports, and writes the result back.

Run: python dev/add_model_schemas.py
"""

import json
import copy
import os

# ── Schema field templates ──────────────────────────────────────────────────

FIELD = {
    "temperature_0_2": {
        "name": "temperature",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0.0, "max": 2.0},
        "required": 0,
        "description": "Controls randomness in output. Range: 0.0 to 2.0",
    },
    "temperature_0_1": {
        "name": "temperature",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0.0, "max": 1.0},
        "required": 0,
        "description": "Controls randomness in output. Range: 0.0 to 1.0",
    },
    "top_p": {
        "name": "top_p",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": 0.0, "max": 1.0},
        "required": 0,
        "description": "Nucleus sampling threshold. Range: 0.0 to 1.0",
    },
    "top_k": {
        "name": "top_k",
        "data_type": "integer",
        "type": "input number",
        "format": "integer",
        "validator": {"min": 0},
        "required": 0,
        "description": "Top-K sampling parameter. Min: 0",
    },
    "frequency_penalty": {
        "name": "frequency_penalty",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": -2.0, "max": 2.0},
        "required": 0,
        "description": "Penalizes new tokens based on their frequency in the text so far. Range: -2.0 to 2.0",
    },
    "presence_penalty": {
        "name": "presence_penalty",
        "data_type": "float",
        "type": "input number",
        "format": "float",
        "validator": {"min": -2.0, "max": 2.0},
        "required": 0,
        "description": "Penalizes new tokens based on whether they appear in the text so far. Range: -2.0 to 2.0",
    },
    "seed": {
        "name": "seed",
        "data_type": "integer",
        "type": "input number",
        "format": "integer",
        "validator": {"min": 0},
        "required": 0,
        "description": "Seed for deterministic generation. Min: 0",
    },
    "max_completion_tokens": {
        "name": "max_completion_tokens",
        "data_type": "integer",
        "type": "input number",
        "format": "integer",
        "validator": {"min": 1},
        "required": 0,
        "description": "Maximum number of completion tokens to generate. Min: 1",
    },
    "max_tokens": {
        "name": "max_tokens",
        "data_type": "integer",
        "type": "input number",
        "format": "integer",
        "validator": {"min": 1},
        "required": 0,
        "description": "Maximum number of tokens to generate. Min: 1",
    },
    "thinking_budget_tokens": {
        "name": "thinking_budget_tokens",
        "data_type": "integer",
        "type": "input number",
        "format": "integer",
        "validator": {"min": 1024},
        "required": 0,
        "description": "Enable extended thinking with a token budget. The model will think before responding. Min: 1024",
    },
    "enable_prompt_caching": {
        "name": "enable_prompt_caching",
        "data_type": "boolean",
        "type": "radio",
        "format": "boolean",
        "validator": None,
        "required": 0,
        "description": "Enable Anthropic prompt caching to reduce costs on repeated prompts",
    },
}


def make_schema(field_names, meta_data=None):
    """Build a meta_data_schema array from field name list.

    If meta_data contains a key matching a field's validator max (e.g.
    max_completion_tokens: 128000), use that as the validator max.
    """
    schema = []
    for name in field_names:
        entry = copy.deepcopy(FIELD[name])
        # Apply model-level max from meta_data
        if meta_data and entry["name"] in meta_data and entry.get("validator"):
            val = meta_data[entry["name"]]
            if isinstance(val, (int, float)):
                entry["validator"]["max"] = val
        schema.append(entry)
    return schema


# ── Model classification rules ──────────────────────────────────────────────
# Each rule: (provider, model_name_pattern) -> list of field template keys

def classify_openai_direct(model_name):
    """Classify OpenAI direct provider models."""
    reasoning = ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5.5", "gpt-5.4",
                 "gpt-5.4-mini", "o3", "o3-pro"]
    if model_name in reasoning:
        return ["max_completion_tokens"]
    # Should not happen for current data but fallback
    return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
            "seed", "max_completion_tokens"]


def classify_groq(model_name):
    """Classify Groq models."""
    # All Groq models: temperature, top_p, seed, max_completion_tokens
    # No frequency_penalty, presence_penalty (accepted but not supported)
    return ["temperature_0_2", "top_p", "seed", "max_completion_tokens"]


def classify_anthropic(model_name):
    """Classify Anthropic Claude models."""
    # All Claude: temperature (0-1), top_p, top_k, max_tokens, thinking_budget_tokens
    return ["temperature_0_1", "top_p", "top_k", "max_tokens",
            "thinking_budget_tokens", "enable_prompt_caching"]


def classify_google(model_name):
    """Classify Google Gemini/Gemma models."""
    # All: temperature (0-2), top_p, top_k, max_tokens
    return ["temperature_0_2", "top_p", "top_k", "max_tokens"]


def classify_deepseek_direct(model_name):
    """Classify DeepSeek direct API models."""
    # temperature, top_p, max_tokens (frequency/presence_penalty deprecated)
    return ["temperature_0_2", "top_p", "max_tokens"]


def classify_grok(model_name):
    """Classify Grok (xAI) models."""
    # temperature, top_p, seed, max_completion_tokens
    # frequency/presence_penalty partial — safer to exclude
    return ["temperature_0_2", "top_p", "seed", "max_completion_tokens"]


def classify_perplexity(model_name):
    """Classify Perplexity models."""
    # temperature, top_p, max_tokens
    return ["temperature_0_2", "top_p", "max_tokens"]


def classify_qwen_direct(model_name):
    """Classify Qwen direct API models."""
    # temperature, top_p, presence_penalty, seed, max_tokens
    return ["temperature_0_2", "top_p", "presence_penalty", "seed", "max_tokens"]


def classify_openrouter(model_name):
    """Classify OpenRouter models by their underlying model family."""
    name = model_name.lower()

    # OpenAI reasoning models
    if name.startswith("openai/o1") or name.startswith("openai/o3") or name.startswith("openai/o4"):
        return ["seed", "max_tokens"]
    if name.startswith("openai/gpt-5"):
        return ["seed", "max_completion_tokens"]

    # OpenAI standard models
    if name.startswith("openai/gpt-4") or name.startswith("openai/gpt-3"):
        return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
                "seed", "max_tokens", "max_completion_tokens"]

    # Anthropic via OpenRouter
    if name.startswith("anthropic/"):
        return ["temperature_0_1", "top_p", "max_tokens"]

    # Meta Llama
    if name.startswith("meta-llama/"):
        return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
                "seed", "max_tokens"]

    # Qwen
    if name.startswith("qwen/"):
        # Qwen thinking models
        if "thinking" in name:
            return ["temperature_0_2", "top_p", "presence_penalty", "seed", "max_tokens"]
        return ["temperature_0_2", "top_p", "presence_penalty", "seed", "max_tokens"]

    # Mistral
    if name.startswith("mistralai/"):
        return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
                "seed", "max_tokens"]

    # DeepSeek reasoning (r1)
    if name.startswith("deepseek/deepseek-r1"):
        return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
                "seed", "max_tokens"]

    # DeepSeek standard
    if name.startswith("deepseek/"):
        return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
                "max_tokens"]

    # Google via OpenRouter
    if name.startswith("google/"):
        return ["temperature_0_2", "top_p", "seed", "max_tokens"]

    # Cohere
    if name.startswith("cohere/"):
        return ["temperature_0_2", "top_p", "top_k", "frequency_penalty",
                "presence_penalty", "seed", "max_tokens"]

    # Default fallback for other OpenRouter models (microsoft, ai21, inflection, etc.)
    return ["temperature_0_2", "top_p", "presence_penalty", "seed", "max_tokens"]


def classify_aws_bedrock(model_name):
    """Classify AWS Bedrock models — all support standard params."""
    return ["temperature_0_2", "top_p", "max_tokens"]


def classify_openai_realtime(model_name):
    """Classify OpenAI Realtime S2S models."""
    return ["temperature_0_2", "max_completion_tokens"]


def classify_gemini_live(model_name):
    """Classify Gemini Live S2S models."""
    return ["temperature_0_2", "top_p", "top_k", "frequency_penalty",
            "presence_penalty", "max_tokens"]


# Provider -> classifier function
PROVIDER_CLASSIFIERS = {
    "openai": classify_openai_direct,
    "groq": classify_groq,
    "anthropic": classify_anthropic,
    "google": classify_google,
    "openrouter": classify_openrouter,
    "qwen": classify_qwen_direct,
    "deepseek": classify_deepseek_direct,
    "grok": classify_grok,
    "perplexity": classify_perplexity,
    "aws_bedrock": classify_aws_bedrock,
    "openai_realtime": classify_openai_realtime,
    "gemini_live": classify_gemini_live,
}

# OpenAI-compatible providers that share standard OpenAI param set
# These use BaseOpenAILLMService — support standard OpenAI params
OPENAI_COMPATIBLE_PROVIDERS = {
    "azure", "cerebras", "nvidia_nim", "fireworks", "together",
    "sambanova", "mistral",
}


def classify_openai_compatible(model_name):
    """Standard OpenAI-compatible models support all standard params."""
    return ["temperature_0_2", "top_p", "frequency_penalty", "presence_penalty",
            "seed", "max_completion_tokens"]


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "dev-data.json")

    with open(json_path, "r") as f:
        data = json.load(f)

    modified_count = 0

    for provider in data.get("llm_providers", []):
        provider_name = provider["name"]
        classifier = PROVIDER_CLASSIFIERS.get(provider_name)

        if not classifier and provider_name in OPENAI_COMPATIBLE_PROVIDERS:
            classifier = classify_openai_compatible

        if not classifier:
            # For unknown providers, try to use their existing provider-level schema
            print(f"  SKIP: No classifier for provider '{provider_name}', skipping")
            continue

        for model in provider.get("models", []):
            model_name = model["name"]
            meta_data = model.get("meta_data", {})
            field_keys = classifier(model_name)
            model["meta_data_schema"] = make_schema(field_keys, meta_data)
            modified_count += 1

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Done. Added meta_data_schema to {modified_count} LLM models.")


if __name__ == "__main__":
    main()
