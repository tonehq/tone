"""
Test all LLM x STT x TTS combinations:
  1. Query DB for active providers and their models.
  2. Generate all combinations in memory.
  3. Create one agent per combination.
  4. Trigger test calls via the test-runs API.
  5. Poll call_logs until completed calls are found.
  6. Repeat in batches until all combinations are tested.
"""
import argparse
import sys
import time
from itertools import product
from pathlib import Path

# Add project root to path so we can import shared.config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import redis
import requests
from shared.config import settings

BASE_URL = settings.BASE_API_URL
AUTH_TOKEN = settings.AUTH_TOKEN
DB_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL

BATCH_SIZE = 10
POLL_INTERVAL_S = 60
POLL_TIMEOUT_S = 10 * 60

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json",
}

TEST_RUNS_URL = "https://staging-test.trytone.ai/test-runs"

DEFAULT_SYSTEM_PROMPT = (
    "You are a polite and professional hotel receptionist. When the caller calls, "
    "greet them warmly and introduce the hotel. Help the caller with room booking enquiries. "
    "Ask the following questions one by one, in a natural conversation: "
    "1. Check-in date 2. Check-out date 3. Number of guests "
    "4. Type of room needed (single, double, deluxe, etc.). "
    "If the caller asks about price, give a reasonable estimate and clearly say that "
    "final pricing will be confirmed by the hotel staff. If the caller wants to make a booking, "
    "collect their full name, phone number, and email address"
)


def flush_redis_cache(agent_ids: list[int]) -> None:
    """Delete all agent_bot_data cache keys for the given agents."""
    try:
        r = redis.from_url(REDIS_URL)
        deleted = 0
        for agent_id in agent_ids:
            keys = r.keys(f"agent_bot_data:{agent_id}:*")
            if keys:
                deleted += r.delete(*keys)
        if deleted:
            print(f"  Flushed {deleted} Redis cache keys")
    except Exception as e:
        print(f"  WARNING: Redis flush failed: {e}")


def create_agent(name: str, combo: dict) -> dict:
    """Create a new agent with the given LLM/STT/TTS config. Returns the API response."""
    tts_meta = {"model_id": combo["tts"]["model_id"]}
    # Use the voice_id from the combo (already matched by language)
    if combo["tts"].get("voice_id"):
        tts_meta["voice_id"] = combo["tts"]["voice_id"]

    payload = {
        "name": name,
        "status": "active",
        "agent_type": "INBOUND",
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "first_message": "Hello",
        "llm_service_id": combo["llm"]["sp_id"],
        "stt_service_id": combo["stt"]["sp_id"],
        "tts_service_id": combo["tts"]["sp_id"],
        "llm_metadata": {"model_id": combo["llm"]["model_id"]},
        "stt_metadata": {"model_id": combo["stt"]["model_id"]},
        "tts_metadata": tts_meta,
    }
    for attempt in range(1, 4):
        r = requests.post(f"{BASE_URL}/agent/upsert_agent", json=payload, headers=HEADERS)
        if r.status_code >= 500 and attempt < 3:
            print(f"    create agent '{name}': {r.status_code} error, retrying ({attempt}/3)...")
            time.sleep(2)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()  # Final attempt failed


def poll_completed_calls(agent_ids: list[int], batch_start_ts: int) -> dict[int, dict]:
    """Return mapping of agent_id -> {id, metrics, to_number, transcript} for completed calls."""
    deadline = time.time() + POLL_TIMEOUT_S
    found: dict[int, dict] = {}
    conn = psycopg2.connect(DB_URL)
    try:
        while time.time() < deadline:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (agent_id)
                        agent_id, id, metrics, to_number, transcript
                    FROM call_logs
                    WHERE agent_id = ANY(%s)
                      AND created_at >= %s
                      AND status = 'completed'
                    ORDER BY agent_id, created_at DESC
                    """,
                    (agent_ids, batch_start_ts),
                )
                for agent_id, call_log_id, metrics, to_number, transcript in cur.fetchall():
                    found[agent_id] = {
                        "id": call_log_id,
                        "metrics": metrics,
                        "to_number": to_number,
                        "transcript": transcript,
                    }
            conn.commit()
            missing = [a for a in agent_ids if a not in found]
            print(
                f"  poll: {len(found)}/{len(agent_ids)} completed"
                + (f" (waiting on {missing})" if missing else "")
            )
            if not missing:
                return found
            if time.time() >= deadline:
                print(f"  timeout reached — {len(found)} completed, {len(missing)} not completed")
                return found
            time.sleep(POLL_INTERVAL_S)
    finally:
        conn.close()
    return found


def trigger_test_run(agent_id: str, dataset_id: str) -> dict:
    """Trigger a test run via the test-runs API."""
    payload = {
        "agent_id": agent_id,
        "dataset_id": dataset_id,
        "name": "Full Dataset Run",
        "max_concurrency": 15,
    }
    for attempt in range(1, 4):
        r = requests.post(TEST_RUNS_URL, json=payload, headers=HEADERS)
        if r.status_code >= 500 and attempt < 3:
            print(f"  test-runs API returned {r.status_code}, retrying ({attempt}/3)...")
            time.sleep(3)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()  # Final attempt failed


# STT providers to test (hardcoded — only these three)
STT_PROVIDERS = ["deepgram", "speechmatics", "soniox"]

# Language for test calls — voices must match this
TEST_LANGUAGE = "en"

# Known working models per provider (first match wins).
# If a provider is not listed here, the first active model from DB is used.
PREFERRED_MODELS = {
    "llm": {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-sonnet-4-5",
        "groq": "llama-3.3-70b-versatile",
        "fireworks": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    },
    "stt": {
        "deepgram": "nova-3",
        "speechmatics": "default",
        "soniox": "soniox_en",
    },
    "tts": {
        "cartesia": "sonic-2",
        "openai": "tts-1",
        "rime": "mistv2",
        "sarvam": "bulbul:v2",
        "hathora": "hexgrad-kokoro-82m",
        "inworld": "inworld-tts-1.5-mini",
    },
}


def fetch_providers_and_models() -> dict[str, list[dict]]:
    """Query DB for one working model per active provider, grouped by type.
    For STT, only fetches providers in STT_PROVIDERS list.
    For TTS, also fetches an English voice_id for each provider/model.

    Returns: {
        "llm": [{"sp_id": 58, "sp_name": "openai", "model_id": 548, "model_name": "gpt-4o-mini"}, ...],
        "stt": [...],
        "tts": [{"sp_id": 92, "sp_name": "cartesia", "model_id": 1008, "model_name": "sonic-2", "voice_id": "e07c..."}, ...],
    }
    """
    conn = psycopg2.connect(DB_URL)
    result: dict[str, list[dict]] = {"llm": [], "stt": [], "tts": []}
    try:
        with conn.cursor() as cur:
            for provider_type in ("llm", "stt", "tts"):
                if provider_type == "stt":
                    cur.execute(
                        """
                        SELECT sp.id, sp.name, m.id, m.name
                        FROM service_providers sp
                        JOIN models m ON m.service_provider_id = sp.id
                        WHERE sp.name = ANY(%s)
                          AND sp.provider_type = 'stt'
                          AND m.service_type = 'stt'
                          AND m.status = 'active'
                        ORDER BY sp.name, m.name
                        """,
                        (STT_PROVIDERS,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT sp.id, sp.name, m.id, m.name
                        FROM service_providers sp
                        JOIN models m ON m.service_provider_id = sp.id
                        WHERE sp.status = 'active'
                          AND sp.provider_type = %s
                          AND m.service_type = %s
                          AND m.status = 'active'
                        ORDER BY sp.name, m.name
                        """,
                        (provider_type, provider_type),
                    )

                # Group models by provider, pick preferred or first
                provider_models: dict[str, list[dict]] = {}
                for sp_id, sp_name, model_id, model_name in cur.fetchall():
                    provider_models.setdefault(sp_name, []).append({
                        "sp_id": sp_id,
                        "sp_name": sp_name,
                        "model_id": model_id,
                        "model_name": model_name,
                    })

                preferred = PREFERRED_MODELS.get(provider_type, {})
                for sp_name, models in provider_models.items():
                    # Pick preferred model if it exists, otherwise first
                    pref_name = preferred.get(sp_name)
                    picked = None
                    if pref_name:
                        picked = next((m for m in models if m["model_name"] == pref_name), None)
                    if not picked:
                        picked = models[0]
                    result[provider_type].append(picked)

            # For TTS: fetch an English voice for each picked provider
            for tts_entry in result["tts"]:
                cur.execute(
                    """
                    SELECT voice_id FROM voices
                    WHERE service_provider_id = %s
                      AND language = %s
                      AND is_active = true
                    LIMIT 1
                    """,
                    (tts_entry["sp_id"], TEST_LANGUAGE),
                )
                row = cur.fetchone()
                tts_entry["voice_id"] = row[0] if row else None
                if not row:
                    print(f"  WARNING: no '{TEST_LANGUAGE}' voice found for TTS provider {tts_entry['sp_name']}")

    finally:
        conn.close()

    for ptype, items in result.items():
        print(f"  {ptype}: {len(items)} providers — "
              + ", ".join(f"{i['sp_name']}/{i['model_name']}" for i in items))

    return result


def generate_combinations(limit: int = 0) -> list[dict]:
    """Query DB and generate LLM x STT x TTS combinations in memory."""
    print("Fetching active providers and models from DB...")
    data = fetch_providers_and_models()

    if not data["llm"] or not data["stt"] or not data["tts"]:
        raise RuntimeError("No active providers/models found for one or more types (llm/stt/tts).")

    combos = [
        {"llm": llm, "stt": stt, "tts": tts}
        for llm, stt, tts in product(data["llm"], data["stt"], data["tts"])
    ]

    total = len(combos)
    if limit and limit < total:
        combos = combos[:limit]
        print(f"\nGenerated {total} total combinations, limited to {limit}")
    else:
        print(f"\nGenerated {total} combinations "
              f"({len(data['llm'])} LLM x {len(data['stt'])} STT x {len(data['tts'])} TTS)")

    return combos


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run call combinations test")
    parser.add_argument("--agent-id", required=True, help="Agent ID for triggering test runs")
    parser.add_argument("--dataset-id", required=True, help="Dataset ID for triggering test runs")
    parser.add_argument("--limit", type=int, default=0, help="Max number of combinations to test (0 = all)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Validate required settings upfront
    if not AUTH_TOKEN:
        raise RuntimeError("AUTH_TOKEN is not set in .env or Infisical")
    if not DB_URL:
        raise RuntimeError("DATABASE_URL is not set in .env or Infisical")

    # Unique run ID to avoid agent name conflicts across runs
    run_id = int(time.time())
    print(f"Run ID: {run_id}")

    # Step 1: Generate combinations from DB
    combos = generate_combinations(limit=args.limit)

    created_agents = []  # list of (combo_index, agent_id)

    # Step 2: Create one agent per combination
    for idx, combo in enumerate(combos):
        agent_name = (
            f"run{run_id}-{idx}-"
            f"{combo['llm']['sp_name']}-{combo['llm']['model_name']}-"
            f"{combo['stt']['sp_name']}-{combo['stt']['model_name']}-"
            f"{combo['tts']['sp_name']}-{combo['tts']['model_name']}"
        )
        try:
            result = create_agent(agent_name, combo)
            agent_id = result["id"]
            created_agents.append((idx, agent_id))
            print(
                f"  [{idx + 1}/{len(combos)}] created agent {agent_id}: "
                f"llm={combo['llm']['sp_name']}/{combo['llm']['model_name']} "
                f"stt={combo['stt']['sp_name']}/{combo['stt']['model_name']} "
                f"tts={combo['tts']['sp_name']}/{combo['tts']['model_name']}"
            )
        except requests.HTTPError as e:
            status = e.response.status_code
            if status == 409:
                print(f"  [{idx + 1}/{len(combos)}] SKIPPED — agent name already exists")
            elif status == 400:
                print(f"  [{idx + 1}/{len(combos)}] SKIPPED — bad request: {e.response.text}")
            else:
                print(f"  [{idx + 1}/{len(combos)}] FAILED: {e} | {e.response.text}")
            continue

    print(f"\nCreated {len(created_agents)}/{len(combos)} agents.")

    if not created_agents:
        print("No agents created, nothing to test.")
        return

    # Step 3: Flush Redis cache for all created agents
    flush_redis_cache([aid for _, aid in created_agents])

    # Step 4: Trigger test runs and poll in batches
    for batch_start in range(0, len(created_agents), BATCH_SIZE):
        batch = created_agents[batch_start : batch_start + BATCH_SIZE]
        batch_agent_ids = [aid for _, aid in batch]

        print(f"\n=== Batch {batch_start // BATCH_SIZE + 1}: {len(batch)} agents ===")

        batch_start_ts = int(time.time())
        print(f"Triggering test run (agent_id={args.agent_id}, dataset_id={args.dataset_id})...")
        try:
            result = trigger_test_run(args.agent_id, args.dataset_id)
            print(f"  Test run triggered: {result}")
        except requests.HTTPError as e:
            print(f"  FAILED to trigger test run: {e} | {e.response.text}")
            raise

        # Step 5: Poll for results
        results = poll_completed_calls(batch_agent_ids, batch_start_ts)

        # Log results
        for combo_idx, agent_id in batch:
            if agent_id in results:
                print(f"  agent {agent_id} (combo {combo_idx}): completed")
            else:
                print(f"  WARNING: agent {agent_id} (combo {combo_idx}): not completed")

    print("\nAll done.")


if __name__ == "__main__":
    main()
