"""
Test script to validate LLM models configured in dev-data.json.
Instantiates Pipecat LLM services exactly like get_llm_for_agent() in
agent_factory_service.py and calls run_inference() on each model.

Usage:
    python dev/test_llm_models.py                                    # Test all
    python dev/test_llm_models.py --provider openai                  # One provider
    python dev/test_llm_models.py --provider openai --model gpt-4o   # One model
"""

import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add project root to sys.path so pipecat and core imports work
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipecat" / "src"))

DEV_DATA_PATH = Path(__file__).resolve().parent / "dev-data.json"

TEST_PROMPT = "Say hello in one word."

# ── Hardcoded service providers to test ──────────────────────────
# Add or remove providers here to control which ones get tested.
# Models are auto-picked from dev-data.json for each provider listed.
SERVICE_PROVIDERS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY", # All pass
    },
    "groq": {
        "api_key_env": "GROQ_API_KEY", # All pass
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY", # All pass
    },
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY", # Need credits
    },
    "cerebras": {
        "api_key_env": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1", # all pass
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",  # Need credits
    },
    "fireworks": {
        "api_key_env": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1", #All pass
    },
    "grok": {
        "api_key_env": "GROK_API_KEY",  #Permission issue
        "base_url": "https://api.x.ai/v1",
    },
    "nvidia_nim": {
        "api_key_env": "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",  # Issues
    },
}


def load_llm_providers():
    with open(DEV_DATA_PATH) as f:
        data = json.load(f)
    return data.get("llm_providers", [])


def create_llm_service(provider_name, api_key, model_name, base_url=None):
    """
    Instantiate a Pipecat LLM service exactly like get_llm_for_agent() does.
    Returns the service instance.
    """
    if provider_name == "openai":
        from pipecat.services.openai.llm import OpenAILLMService
        return OpenAILLMService(api_key=api_key, model=model_name)

    if provider_name == "anthropic":
        from pipecat.services.anthropic.llm import AnthropicLLMService
        return AnthropicLLMService(api_key=api_key, model=model_name)

    if provider_name == "groq":
        from pipecat.services.groq.llm import GroqLLMService
        return GroqLLMService(api_key=api_key, model=model_name)

    if provider_name == "openrouter":
        from pipecat.services.openrouter.llm import OpenRouterLLMService
        return OpenRouterLLMService(api_key=api_key, model=model_name)

    # All other providers use BaseOpenAILLMService with base_url
    # (cerebras, nvidia_nim, fireworks, deepseek, grok, etc.)
    from pipecat.services.openai.llm import BaseOpenAILLMService
    return BaseOpenAILLMService(api_key=api_key, model=model_name, base_url=base_url)


async def test_model_via_pipecat(provider_name, api_key, model_name, base_url=None):
    """
    Create the Pipecat LLM service and call run_inference() — the same code
    path that the voice pipeline uses in production.
    """
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

    service = create_llm_service(provider_name, api_key, model_name, base_url)
    context = OpenAILLMContext(
        messages=[{"role": "user", "content": TEST_PROMPT}]
    )
    response = await service.run_inference(context)
    return response


def main():
    parser = argparse.ArgumentParser(description="Test LLM models from dev-data.json via Pipecat services")
    parser.add_argument("--provider", help="Test only this provider")
    parser.add_argument("--model", help="Test only this model (requires --provider)")
    args = parser.parse_args()

    # Load models from dev-data.json, indexed by provider name
    all_providers = load_llm_providers()
    dev_data_models = {p["name"]: p for p in all_providers}

    results = []
    total = 0
    passed = 0
    failed = 0
    skipped = 0

    for name, cfg in SERVICE_PROVIDERS.items():
        # Filter by --provider
        if args.provider and name != args.provider:
            continue

        # Resolve API key from env
        api_key = os.getenv(cfg["api_key_env"], "")
        if not api_key:
            print(f"\n{'='*60}")
            print(f"SKIP  {name} — {cfg['api_key_env']} not set in .env")
            print(f"{'='*60}")
            continue

        # Get models from dev-data.json for this provider
        dev_entry = dev_data_models.get(name)
        if not dev_entry:
            print(f"\n{'='*60}")
            print(f"SKIP  {name} — not found in dev-data.json")
            print(f"{'='*60}")
            continue

        models = dev_entry.get("models", [])
        display_name = dev_entry.get("display_name", name)
        base_url = cfg.get("base_url")

        print(f"\n{'='*60}")
        print(f"Testing {display_name} ({len(models)} models)")
        print(f"{'='*60}")

        for model_entry in models:
            model_name = model_entry.get("meta_data", {}).get("model") or model_entry["name"]

            # Filter by --model
            if args.model and model_name != args.model:
                continue

            total += 1
            sys.stdout.write(f"  {model_name:50s} ... ")
            sys.stdout.flush()

            try:
                start = time.time()
                response = asyncio.run(
                    test_model_via_pipecat(name, api_key, model_name, base_url)
                )
                elapsed = time.time() - start

                if response:
                    passed += 1
                    print(f"PASS ({elapsed:.1f}s) — \"{response[:40].strip()}\"")
                    results.append((name, model_name, "PASS", response.strip()))
                else:
                    failed += 1
                    print(f"FAIL ({elapsed:.1f}s) — Empty response")
                    results.append((name, model_name, "FAIL", "Empty response"))
            except Exception as e:
                elapsed = time.time() - start
                failed += 1
                err = str(e)[:120]
                print(f"FAIL ({elapsed:.1f}s) — {err}")
                results.append((name, model_name, "FAIL", str(e)))

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Tested:  {total}")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print()

    if failed > 0:
        print("Failed models:")
        for prov, model, status, detail in results:
            if status == "FAIL":
                print(f"  [{prov}] {model}: {detail[:120]}")

    # Write results to JSON
    output_path = Path(__file__).resolve().parent / "llm_test_results.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "tested": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "results": [
                    {"provider": r[0], "model": r[1], "status": r[2], "detail": r[3]}
                    for r in results
                ],
            },
            f,
            indent=2,
        )
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
