"""Simple script to test Google Gemini LLM models."""

import os
import sys
import json
import time

try:
    from google import genai
except ImportError:
    print("Installing google-genai...")
    os.system(f"{sys.executable} -m pip install google-genai")
    from google import genai

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("ERROR: GOOGLE_API_KEY not found in .env")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

MODELS_TO_TEST = [
    # Gemini 3.x
    "gemini-3.1-pro-preview",
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    # # Gemini 2.5
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    # Gemma (open models)
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemma-3-27b-it",
    "gemma-3-12b-it",
    "gemma-3-4b-it",
    "gemma-3-1b-it",
    "gemma-3n-e4b-it",
    "gemma-3n-e2b-it",
]

TEST_PROMPT = "Say hello in one sentence."

results = []

print(f"Testing {len(MODELS_TO_TEST)} Google Gemini models...\n")
print("=" * 60)

for model_name in MODELS_TO_TEST:
    print(f"\nModel: {model_name}")
    print("-" * 40)
    try:
        start = time.time()
        response = client.models.generate_content(
            model=model_name,
            contents=TEST_PROMPT,
        )
        elapsed = time.time() - start

        text = response.text.strip()
        print(f"  Response: {text}")
        print(f"  Latency:  {elapsed:.2f}s")
        results.append({"model": model_name, "status": "OK", "response": text, "latency_s": round(elapsed, 2)})
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"model": model_name, "status": "FAILED", "error": str(e)})

print("\n" + "=" * 60)
print("\nSummary:")
for r in results:
    status = "PASS" if r["status"] == "OK" else "FAIL"
    print(f"  [{status}] {r['model']}", end="")
    if r["status"] == "OK":
        print(f" ({r['latency_s']}s)")
    else:
        print(f" - {r['error']}")

# Save results
output_path = os.path.join(os.path.dirname(__file__), "google_llm_test_results.json")
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {output_path}")
