"""
Update meta_data_schema for all model providers from dev-data.json.
Run from project root: python dev/update_meta_data_schema.py

Reads the meta_data_schema from each provider entry in dev-data.json,
merges them by provider name (keyed by kind: llm/stt/tts), and updates
the corresponding ModelProvider row in the database.
"""
import os
import sys
import json

if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

# ── Hardcode the target database URL here ──
DATABASE_URL = "postgresql://neondb_owner:npg_6MIP1wKAkFQh@ep-round-pond-anxl0114-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"  # <-- paste your DB URL here

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def load_seed_data():
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_meta_data_schemas(db):
    from core.models.model_provider import ModelProvider

    data = load_seed_data()

    all_providers = []
    all_providers.extend(data.get("llm_providers", []))
    all_providers.extend(data.get("stt_providers", []))
    all_providers.extend(data.get("tts_providers", []))

    # Build merged schema dict per provider: {provider_name: {kind: [...]}}
    provider_schemas = {}
    for config in all_providers:
        name = config["name"]
        kind = config["provider_type"]
        schema = config.get("meta_data_schema")
        if schema is not None:
            provider_schemas.setdefault(name, {})[kind] = schema

    updated = 0
    not_found = 0

    for provider_name, schema_dict in provider_schemas.items():
        provider = (
            db.query(ModelProvider)
            .filter(ModelProvider.provider_id == provider_name)
            .first()
        )

        if not provider:
            print(f"  NOT FOUND: {provider_name}")
            not_found += 1
            continue

        provider.meta_data_schema = schema_dict
        updated += 1
        kinds = ", ".join(schema_dict.keys())
        print(f"  UPDATED: {provider_name} ({kinds})")

    db.commit()
    return updated, not_found


def main():
    if not DATABASE_URL:
        print("ERROR: Set DATABASE_URL at the top of this script before running.")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        print(f"Connecting to: {DATABASE_URL.split('@')[1].split('/')[0]}...")
        print("Updating meta_data_schema from dev-data.json...\n")
        updated, not_found = update_meta_data_schemas(db)
        print(f"\nDone: {updated} updated, {not_found} not found in DB.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
