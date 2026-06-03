"""
Test LLM model params against real APIs.

For each LLM model in dev-data.json that has a meta_data_schema and an API key,
this script:
1. Generates valid test values from the schema
2. Runs them through MetaDataSchemaValidator (same as backend save)
3. Runs them through build_input_params (same as pipeline builder)
4. Makes a real API call to verify the provider accepts the params

Run from project root: python dev/test_llm_model_params.py
"""
import asyncio
import json
import os
import sys
import traceback

if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

# ── API Keys (parsed from .env, including commented-out lines with ;) ───────
API_KEYS = {}


def load_api_keys():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        print("ERROR: .env file not found")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Handle both normal and ;-commented lines
            if line.startswith(";"):
                line = line[1:].strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Remove inline comments
            if " #" in value:
                value = value[:value.index(" #")].strip()
            if key.endswith("_API_KEY") or key.endswith("_JSON"):
                API_KEYS[key] = value


# Map provider name -> env var name
PROVIDER_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "together": "TOGETHER_API_KEY",
    "sambanova": "SAMBANOVA_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "grok": "GROK_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "qwen": "QWEN_API_KEY",
}

# Base URLs for OpenAI-compatible providers
PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "together": "https://api.together.xyz/v1",
    "sambanova": "https://api.sambanova.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "grok": "https://api.x.ai/v1",
    "perplexity": "https://api.perplexity.ai",
    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
}


def load_seed_data():
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path) as f:
        return json.load(f)


def generate_test_values(schema):
    """Generate valid test values from a meta_data_schema."""
    values = {}
    for field in schema:
        name = field["name"]
        data_type = field.get("data_type", "string")
        validator = field.get("validator") or {}
        options = field.get("options")

        if options:
            values[name] = options[0]
        elif data_type == "float":
            min_val = validator.get("min", 0.0)
            max_val = validator.get("max", 1.0)
            # Use midpoint as safe test value
            values[name] = round((min_val + max_val) / 2, 2)
        elif data_type in ("integer", "int"):
            min_val = validator.get("min", 1)
            max_val = validator.get("max")
            if max_val:
                values[name] = min(min_val + 10, max_val)
            else:
                values[name] = min_val + 10
        elif data_type == "boolean":
            values[name] = True
        elif data_type == "string":
            values[name] = "test"
        elif data_type in ("array", "list"):
            values[name] = ["test"]
    return values


def test_backend_validation(schema, test_values):
    """Test MetaDataSchemaValidator with the values."""
    from core.services.meta_data_schema_validator import MetaDataSchemaValidator
    validator = MetaDataSchemaValidator()
    errors = validator.validate_settings(schema, test_values)
    return errors


def test_build_input_params(provider_name, model_name, metadata):
    """Test build_input_params for the provider's builder."""
    from core.services.pipeline_builders.base import build_input_params, BuildContext
    from core.services.pipeline_builders.llm_builders import LLM_BUILDERS

    # Find the builder
    builder_map = {
        "openai": "openai", "groq": "groq", "anthropic": "anthropic",
        "google": "google", "openrouter": "openrouter",
        "fireworks": "fireworks", "cerebras": "cerebras",
        "together": "together", "sambanova": "sambanova",
        "deepseek": "deepseek", "grok": "grok",
        "perplexity": "perplexity", "qwen": "qwen",
    }
    slug = builder_map.get(provider_name)
    if not slug:
        return None, f"No builder mapping for {provider_name}"

    builder = LLM_BUILDERS.get(slug)
    if not builder:
        return None, f"No builder for slug {slug}"

    # Try to create the service object
    api_key = API_KEYS.get(PROVIDER_KEY_MAP.get(provider_name, ""), "dummy")
    ctx = BuildContext(
        provider_name=slug,
        api_key=api_key,
        model=model_name,
        metadata=dict(metadata),
        model_meta={},
    )
    try:
        service = builder.build(ctx)
        return service, None
    except Exception as e:
        return None, str(e)


async def test_real_api_call(provider_name, model_name, test_values, schema):
    """Make a real API call to test if the provider accepts the params."""
    import openai

    api_key = API_KEYS.get(PROVIDER_KEY_MAP.get(provider_name, ""))
    if not api_key:
        return "SKIP", "No API key"

    base_url = PROVIDER_BASE_URLS.get(provider_name)

    # Anthropic uses a different SDK
    if provider_name == "anthropic":
        return await _test_anthropic(api_key, model_name, test_values, schema)

    # Google uses a different SDK
    if provider_name == "google":
        return await _test_google(model_name, test_values, schema)

    if not base_url:
        return "SKIP", f"No base URL for {provider_name}"

    # Build params dict from schema fields
    params = {}
    for field in schema:
        name = field["name"]
        if name in test_values:
            params[name] = test_values[name]

    # Separate max_tokens / max_completion_tokens
    kwargs = {}
    if "temperature" in params:
        kwargs["temperature"] = params["temperature"]
    if "top_p" in params:
        kwargs["top_p"] = params["top_p"]
    if "frequency_penalty" in params:
        kwargs["frequency_penalty"] = params["frequency_penalty"]
    if "presence_penalty" in params:
        kwargs["presence_penalty"] = params["presence_penalty"]
    if "seed" in params:
        kwargs["seed"] = int(params["seed"])
    if "max_completion_tokens" in params:
        kwargs["max_completion_tokens"] = int(params["max_completion_tokens"])
    elif "max_tokens" in params:
        kwargs["max_tokens"] = int(params["max_tokens"])

    # For thinking models
    if "thinking_budget_tokens" in params:
        kwargs["max_tokens"] = int(params.get("max_tokens", 4096))

    try:
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Say hello in one word."}],
            stream=False,
            **kwargs,
        )
        content = response.choices[0].message.content[:50] if response.choices else "no content"
        return "PASS", content
    except openai.BadRequestError as e:
        return "FAIL", f"400: {e.message}"
    except openai.AuthenticationError as e:
        return "AUTH_FAIL", f"Auth: {e.message}"
    except openai.RateLimitError:
        return "RATE_LIMIT", "Rate limited"
    except openai.APIConnectionError as e:
        return "CONN_FAIL", str(e)[:100]
    except Exception as e:
        return "ERROR", f"{type(e).__name__}: {str(e)[:100]}"


async def _test_anthropic(api_key, model_name, test_values, schema):
    """Test Anthropic API."""
    try:
        import anthropic
    except ImportError:
        return "SKIP", "anthropic package not installed"

    kwargs = {}
    if "temperature" in test_values:
        kwargs["temperature"] = test_values["temperature"]
    if "top_p" in test_values:
        kwargs["top_p"] = test_values["top_p"]
    if "top_k" in test_values:
        kwargs["top_k"] = int(test_values["top_k"])
    max_tokens = int(test_values.get("max_tokens", 100))

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=30)
        response = await client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": "Say hello in one word."}],
            **kwargs,
        )
        content = response.content[0].text[:50] if response.content else "no content"
        return "PASS", content
    except anthropic.BadRequestError as e:
        return "FAIL", f"400: {str(e)[:100]}"
    except anthropic.AuthenticationError as e:
        return "AUTH_FAIL", f"Auth: {str(e)[:100]}"
    except anthropic.RateLimitError:
        return "RATE_LIMIT", "Rate limited"
    except Exception as e:
        return "ERROR", f"{type(e).__name__}: {str(e)[:100]}"


async def _test_google(model_name, test_values, schema):
    """Test Google Gemini API."""
    api_key = API_KEYS.get("GOOGLE_API_KEY")
    if not api_key:
        return "SKIP", "No GOOGLE_API_KEY"

    try:
        from google import genai
    except ImportError:
        return "SKIP", "google-genai package not installed"

    kwargs = {}
    if "temperature" in test_values:
        kwargs["temperature"] = test_values["temperature"]
    if "top_p" in test_values:
        kwargs["top_p"] = test_values["top_p"]
    if "top_k" in test_values:
        kwargs["top_k"] = int(test_values["top_k"])
    if "max_tokens" in test_values:
        kwargs["max_output_tokens"] = int(test_values["max_tokens"])

    try:
        client = genai.Client(api_key=api_key)
        config = genai.types.GenerateContentConfig(**kwargs) if kwargs else None
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents="Say hello in one word.",
            config=config,
        )
        content = response.text[:50] if response.text else "no content"
        return "PASS", content
    except Exception as e:
        err = str(e)[:100]
        if "400" in err or "invalid" in err.lower():
            return "FAIL", f"400: {err}"
        if "403" in err or "auth" in err.lower() or "permission" in err.lower():
            return "AUTH_FAIL", f"Auth: {err}"
        if "429" in err:
            return "RATE_LIMIT", "Rate limited"
        return "ERROR", f"{type(e).__name__}: {err}"


async def main():
    load_api_keys()
    data = load_seed_data()

    print("=" * 80)
    print("LLM Model Parameter Test")
    print("=" * 80)
    print(f"API keys loaded: {[k for k in API_KEYS if k.endswith('_API_KEY')]}")
    print()

    results = {"PASS": 0, "FAIL": 0, "SKIP": 0, "AUTH_FAIL": 0,
               "RATE_LIMIT": 0, "CONN_FAIL": 0, "ERROR": 0,
               "VALIDATION_FAIL": 0, "BUILD_FAIL": 0}
    failures = []

    for provider in data.get("llm_providers", []):
        provider_name = provider["name"]
        key_env = PROVIDER_KEY_MAP.get(provider_name)
        api_key = API_KEYS.get(key_env, "") if key_env else ""

        if not api_key:
            continue

        models = provider.get("models", [])
        print(f"\n── {provider_name} ({len(models)} models) ──")

        for model in models:
            model_name = model["name"]
            schema = model.get("meta_data_schema")
            meta_data = model.get("meta_data", {})

            if not schema:
                print(f"  {model_name}: SKIP (no schema)")
                results["SKIP"] += 1
                continue

            # 1. Generate test values
            test_values = generate_test_values(schema)

            # 2. Backend validation
            val_errors = test_backend_validation(schema, test_values)
            if val_errors:
                print(f"  {model_name}: VALIDATION_FAIL {val_errors}")
                results["VALIDATION_FAIL"] += 1
                failures.append((provider_name, model_name, "VALIDATION", str(val_errors)))
                continue

            # 3. Build input params (tests Pydantic validation)
            # Add structural keys needed by builder
            build_metadata = dict(test_values)
            build_metadata["model"] = meta_data.get("model", model_name)
            _, build_err = test_build_input_params(provider_name, model_name, build_metadata)
            if build_err:
                print(f"  {model_name}: BUILD_FAIL {build_err}")
                results["BUILD_FAIL"] += 1
                failures.append((provider_name, model_name, "BUILD", build_err))
                continue

            # 4. Real API call
            api_model = meta_data.get("model", model_name)
            status, detail = await test_real_api_call(
                provider_name, api_model, test_values, schema
            )
            results[status] += 1

            icon = {"PASS": "OK", "FAIL": "FAIL", "SKIP": "SKIP",
                    "AUTH_FAIL": "AUTH", "RATE_LIMIT": "RATE",
                    "CONN_FAIL": "CONN", "ERROR": "ERR"}.get(status, status)

            param_names = [f["name"] for f in schema]
            print(f"  {model_name}: {icon} | params={param_names} | {detail[:60]}")

            if status == "FAIL":
                failures.append((provider_name, model_name, "API", detail))

            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for status, count in sorted(results.items()):
        if count > 0:
            print(f"  {status}: {count}")
    total = sum(results.values())
    print(f"  TOTAL: {total}")

    if failures:
        print(f"\n{'=' * 80}")
        print("FAILURES")
        print("=" * 80)
        for provider, model, stage, detail in failures:
            print(f"  {provider}/{model} [{stage}]: {detail}")

    return len(failures) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
