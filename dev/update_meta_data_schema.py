"""
Update meta_data_schema for all service providers from dev-data.json.
Run from project root: python dev/update_meta_data_schema.py
"""
import os
import sys
import json

# Ensure project root is on path when run as script
if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()


def load_seed_data():
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_meta_data_schemas(db):
    from core.models.service_provider import ServiceProvider

    data = load_seed_data()

    all_providers = []
    all_providers.extend(data.get("llm_providers", []))
    all_providers.extend(data.get("stt_providers", []))
    all_providers.extend(data.get("tts_providers", []))

    updated = 0
    skipped = 0
    not_found = 0

    for config in all_providers:
        name = config["name"]
        provider_type = config["provider_type"]
        meta_data_schema = config.get("meta_data_schema")

        provider = (
            db.query(ServiceProvider)
            .filter(
                ServiceProvider.name == name,
                ServiceProvider.provider_type == provider_type,
            )
            .first()
        )

        if not provider:
            print(f"  NOT FOUND: {name} ({provider_type})")
            not_found += 1
            continue

        if meta_data_schema is not None:
            provider.meta_data_schema = meta_data_schema
            updated += 1
            print(f"  UPDATED: {name} ({provider_type})")
        else:
            skipped += 1
            print(f"  SKIPPED (no schema in JSON): {name} ({provider_type})")

    db.commit()
    return updated, skipped, not_found


def main():
    from core.database.session import get_db_script

    db = get_db_script()
    try:
        print("Updating meta_data_schema from dev-data.json...\n")
        updated, skipped, not_found = update_meta_data_schemas(db)
        print(f"\nDone: {updated} updated, {skipped} skipped, {not_found} not found in DB.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
