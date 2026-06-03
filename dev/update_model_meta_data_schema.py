"""
Update meta_data_schema for all models from dev-data.json.
Run from project root: python dev/update_model_meta_data_schema.py

Reads the per-model meta_data_schema from each model entry in dev-data.json
and updates the corresponding Model row in the database.
Only updates models that have a meta_data_schema defined in dev-data.json.
Does NOT touch any other columns (meta_data, name, is_active, etc.).
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


def update_model_schemas(db):
    from core.models.model import Model
    from core.models.model_provider import ModelProvider

    data = load_seed_data()

    all_providers = []
    all_providers.extend(data.get("llm_providers", []))
    all_providers.extend(data.get("stt_providers", []))
    all_providers.extend(data.get("tts_providers", []))

    # Build lookup: provider_id (slug) -> ModelProvider UUID
    provider_map = {
        mp.provider_id: mp.id
        for mp in db.query(ModelProvider).all()
    }

    # Build lookup: (provider_uuid, model_name) -> Model row
    all_models = db.query(Model).all()
    model_map = {(m.provider_id, m.name): m for m in all_models}

    updated = 0
    skipped = 0
    not_found = 0

    for config in all_providers:
        provider_name = config["name"]
        provider_uuid = provider_map.get(provider_name)

        if not provider_uuid:
            for model_spec in config.get("models", []):
                if model_spec.get("meta_data_schema"):
                    print(f"  PROVIDER NOT FOUND: {provider_name}/{model_spec['name']}")
                    not_found += 1
            continue

        for model_spec in config.get("models", []):
            model_name = model_spec.get("name", "default")
            schema = model_spec.get("meta_data_schema")

            if not schema:
                skipped += 1
                continue

            model_row = model_map.get((provider_uuid, model_name))
            if not model_row:
                print(f"  MODEL NOT FOUND: {provider_name}/{model_name}")
                not_found += 1
                continue

            model_row.meta_data_schema = schema
            updated += 1
            field_names = [f["name"] for f in schema]
            print(f"  UPDATED: {provider_name}/{model_name} -> {field_names}")

    db.commit()
    return updated, skipped, not_found


def main():
    if DATABASE_URL == "postgresql://user:password@host:5432/dbname":
        print("ERROR: Set DATABASE_URL at the top of this script before running.")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        host = DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "local"
        print(f"Connecting to: {host}...")
        print("Updating model-level meta_data_schema from dev-data.json...\n")
        updated, skipped, not_found = update_model_schemas(db)
        print(f"\nDone: {updated} updated, {skipped} skipped (no schema), {not_found} not found in DB.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
