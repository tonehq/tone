"""
Reseed script: Update meta_data_schema on service providers, delete and
repopulate models and voices from dev-data.json.

Does NOT delete or recreate service providers or API keys.

Steps per provider:
  1. Update meta_data_schema on the existing ServiceProvider
  2. Delete all voices for this provider (voices reference models, so delete first)
  3. Delete all models for this provider
  4. Recreate models from dev-data.json
  5. Re-link models to existing API key
  6. Recreate voices from dev-data.json (with model_id resolution)

Usage:
    python dev/reseed_models_voices.py
"""

import os
import sys
import json

# Ensure project root is on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()


def load_seed_data():
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    from core.database.session import get_db_script
    from core.models.service_provider import ServiceProvider
    from core.models.models import Model
    from core.models.voice import Voice
    from core.models.api_key import ApiKey

    db = get_db_script()

    try:
        data = load_seed_data()

        all_providers = []
        all_providers.extend(data.get("llm_providers", []))
        all_providers.extend(data.get("stt_providers", []))
        all_providers.extend(data.get("tts_providers", []))

        stats = {
            "providers_updated": 0,
            "providers_not_found": 0,
            "models_deleted": 0,
            "models_created": 0,
            "voices_deleted": 0,
            "voices_created": 0,
            "api_keys_linked": 0,
        }

        print(f"Loaded {len(all_providers)} providers from dev-data.json\n")

        for config in all_providers:
            name = config["name"]
            provider_type = config["provider_type"]
            display_name = config.get("display_name", name)
            meta_data_schema = config.get("meta_data_schema")
            models_spec = config.get("models") or []
            voices_spec = config.get("voices") or []

            # Find existing provider
            provider = (
                db.query(ServiceProvider)
                .filter(
                    ServiceProvider.name == name,
                    ServiceProvider.provider_type == provider_type,
                )
                .first()
            )

            if not provider:
                print(f"  SKIP  {display_name} ({provider_type}) — not found in DB")
                stats["providers_not_found"] += 1
                continue

            provider_id = provider.id
            print(f"  Processing {display_name} ({provider_type}, id={provider_id})")

            # 1. Update meta_data_schema
            if meta_data_schema is not None:
                provider.meta_data_schema = meta_data_schema
            stats["providers_updated"] += 1

            # 2. Delete voices first (voices.model_id FK → models.id)
            voice_count = (
                db.query(Voice)
                .filter(Voice.service_provider_id == provider_id)
                .delete(synchronize_session=False)
            )
            stats["voices_deleted"] += voice_count

            # 3. Delete models
            model_count = (
                db.query(Model)
                .filter(Model.service_provider_id == provider_id)
                .delete(synchronize_session=False)
            )
            stats["models_deleted"] += model_count

            # Flush deletes before inserting new records
            db.flush()

            # 4. Recreate models
            for model_spec in models_spec:
                model_name = model_spec.get("name") or "default"
                meta_data = model_spec.get("meta_data")
                model = Model(
                    service_provider_id=provider_id,
                    name=model_name,
                    service_type=provider_type,
                    status="active",
                    meta_data=meta_data,
                    api_key_id=None,
                )
                db.add(model)
            db.flush()

            stats["models_created"] += len(models_spec)

            # 5. Re-link models to existing API key
            existing_key = (
                db.query(ApiKey)
                .filter(
                    ApiKey.service_provider_id == provider_id,
                    ApiKey.status == "active",
                )
                .first()
            )
            if existing_key:
                linked = (
                    db.query(Model)
                    .filter(
                        Model.service_provider_id == provider_id,
                        Model.status == "active",
                    )
                    .update(
                        {Model.api_key_id: existing_key.id},
                        synchronize_session=False,
                    )
                )
                stats["api_keys_linked"] += linked

            # 6. Recreate voices
            # Build model_name → model_id lookup
            provider_models = (
                db.query(Model)
                .filter(Model.service_provider_id == provider_id)
                .all()
            )
            model_name_to_id = {m.name: m.id for m in provider_models}

            seen_voice_ids = set()
            for voice_spec in voices_spec:
                voice_id = voice_spec.get("voice_id")
                if not voice_id or voice_id in seen_voice_ids:
                    continue
                seen_voice_ids.add(voice_id)

                voice_model_id = None
                voice_model_name = voice_spec.get("model_name")
                if voice_model_name:
                    voice_model_id = model_name_to_id.get(voice_model_name)

                voice = Voice(
                    service_provider_id=provider_id,
                    model_id=voice_model_id,
                    voice_id=voice_id,
                    name=voice_spec.get("name"),
                    language=voice_spec.get("language") or "",
                    language_list=voice_spec.get("language_list"),
                    gender=voice_spec.get("gender"),
                    accent=voice_spec.get("accent"),
                    description=voice_spec.get("description"),
                    sample_url=voice_spec.get("sample_url"),
                    is_active=True,
                )
                db.add(voice)
                stats["voices_created"] += 1

        db.commit()

        print(f"\n{'='*50}")
        print(f"DONE")
        print(f"{'='*50}")
        print(f"  Providers updated:    {stats['providers_updated']}")
        print(f"  Providers not found:  {stats['providers_not_found']}")
        print(f"  Models deleted:       {stats['models_deleted']}")
        print(f"  Models created:       {stats['models_created']}")
        print(f"  Models linked to key: {stats['api_keys_linked']}")
        print(f"  Voices deleted:       {stats['voices_deleted']}")
        print(f"  Voices created:       {stats['voices_created']}")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
