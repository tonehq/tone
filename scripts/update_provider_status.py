"""
Update service_providers status based on the PROVIDERS list in run_call_combinations.py.
- Providers in the list → set status = 'active'
- Providers NOT in the list → set status = 'inactive'

Usage:
    python scripts/update_provider_status.py          # runs on all 3 DBs
    python scripts/update_provider_status.py dev       # runs on dev only
    python scripts/update_provider_status.py staging   # runs on staging only
    python scripts/update_provider_status.py local     # runs on local only
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

# Providers that should remain active, grouped by type
# Edit this list to control which providers are active across all environments
PROVIDERS = {
    "llm": ["openai", "anthropic", "groq", "fireworks"],
    "stt": ["deepgram", "speechmatics", "openai", "groq", "cartesia", "elevenlabs", "gladia"],
    "tts": ["cartesia", "openai", "rime", "sarvam", "hathora", "inworld"],
}

# Hardcoded DB URLs — change these as needed
DB_URLS = {
    "dev": "postgresql://neondb_owner:npg_XFStP7eh4jZY@ep-blue-truth-an3xdo3i-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require",
    "staging": "postgresql://neondb_owner:npg_tVwEx73KXolm@ep-divine-bonus-anek55ly-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require",
    "local": "postgresql://neondb_owner:npg_iNWhZLF0gHt7@ep-holy-wind-ad79pdco-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require",
}


def update_providers(db_name: str, db_url: str) -> None:

    print(f"\n{'='*50}")
    print(f"Updating: {db_name}")
    print(f"{'='*50}")

    # Build a set of (name, provider_type) tuples that should stay active
    active_set: set[tuple[str, str]] = set()
    for provider_type, names in PROVIDERS.items():
        for name in names:
            active_set.add((name, provider_type))

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # Get all service providers
            cur.execute("SELECT id, name, provider_type, status FROM service_providers ORDER BY name")
            all_providers = cur.fetchall()

            to_activate = []
            to_deactivate = []

            for sp_id, name, provider_type, current_status in all_providers:
                should_be_active = (name, provider_type) in active_set
                if should_be_active and current_status != "active":
                    to_activate.append((sp_id, name, provider_type))
                elif not should_be_active and current_status != "inactive":
                    to_deactivate.append((sp_id, name, provider_type))

            # Print summary
            print(f"Total providers: {len(all_providers)}")
            print(f"Active (in PROVIDERS list): {len(active_set)}")
            print(f"Will activate: {len(to_activate)}")
            print(f"Will deactivate: {len(to_deactivate)}")

            if to_activate:
                print("\nActivating:")
                for sp_id, name, ptype in to_activate:
                    print(f"  id={sp_id} name={name} type={ptype}")
                activate_ids = [sp_id for sp_id, _, _ in to_activate]
                cur.execute(
                    "UPDATE service_providers SET status = 'active' WHERE id = ANY(%s)",
                    (activate_ids,),
                )

            if to_deactivate:
                print("\nDeactivating:")
                for sp_id, name, ptype in to_deactivate:
                    print(f"  id={sp_id} name={name} type={ptype}")
                deactivate_ids = [sp_id for sp_id, _, _ in to_deactivate]
                cur.execute(
                    "UPDATE service_providers SET status = 'inactive' WHERE id = ANY(%s)",
                    (deactivate_ids,),
                )

            conn.commit()
            print(f"\n{db_name} done.")

    finally:
        conn.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None

    if target:
        if target not in DB_URLS:
            print(f"Unknown target '{target}'. Choose from: {', '.join(DB_URLS.keys())}")
            sys.exit(1)
        update_providers(target, DB_URLS[target])
    else:
        for db_name, db_url in DB_URLS.items():
            update_providers(db_name, db_url)
