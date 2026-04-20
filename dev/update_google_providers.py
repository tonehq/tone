"""
Update Google LLM, STT, and TTS service providers in the database.

Reads the latest models, voices, and metadata from dev-data.json and syncs
them into the database for the Google providers:
  - google (provider_type=llm)
  - google (provider_type=stt)
  - google_base (provider_type=tts)

Usage:
    python dev/update_google_providers.py
"""

import json
import os
import sys

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
# Change this to your database URL
DB_URL = "postgresql://postgres:postgres@localhost:5432/tone"
# ─────────────────────────────────────────────────────────────────────────────

# Ensure project root is on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.models.service_provider import ServiceProvider
from core.models.models import Model
from core.models.voice import Voice

# Google providers to update: (name, provider_type)
GOOGLE_PROVIDERS = [
    ("google", "llm"),
    ("google", "stt"),
    ("google", "tts"),
]


def load_dev_data():
    """Load dev-data.json and return a lookup of Google provider configs."""
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build lookup: (name, provider_type) -> config
    lookup = {}
    for section in ("llm_providers", "stt_providers", "tts_providers"):
        for config in data.get(section, []):
            key = (config["name"], config["provider_type"])
            if key in dict(GOOGLE_PROVIDERS):
                pass
            lookup[key] = config

    return lookup


def update_provider(db, provider, config):
    """Update a single provider's models, voices, and metadata_schema."""
    provider_name = provider.name
    provider_type = provider.provider_type
    provider_id = provider.id

    # ── Update provider fields ──
    if config.get("display_name"):
        provider.display_name = config["display_name"]
    if config.get("description"):
        provider.description = config["description"]
    if config.get("meta_data_schema") is not None:
        provider.meta_data_schema = config["meta_data_schema"]

    # ── Update models ──
    config_models = config.get("models") or []
    config_model_names = {m["name"] for m in config_models}

    # Get existing models
    existing_models = (
        db.query(Model)
        .filter(
            Model.service_provider_id == provider_id,
            Model.service_type == provider_type,
        )
        .all()
    )
    existing_model_names = {m.name for m in existing_models}

    # Deactivate models no longer in config
    removed = existing_model_names - config_model_names
    for m in existing_models:
        if m.name in removed:
            m.status = "inactive"
            print(f"  [model] deactivated: {m.name}")

    # Add new models / reactivate existing
    for model_spec in config_models:
        model_name = model_spec["name"]
        existing = next((m for m in existing_models if m.name == model_name), None)
        if existing:
            existing.meta_data = model_spec.get("meta_data")
            existing.status = "active"
        else:
            new_model = Model(
                service_provider_id=provider_id,
                name=model_name,
                service_type=provider_type,
                status="active",
                meta_data=model_spec.get("meta_data"),
            )
            db.add(new_model)
            print(f"  [model] added: {model_name}")

    db.flush()

    # ── Update voices (TTS only) ──
    config_voices = config.get("voices") or []
    if not config_voices:
        return

    existing_voices = (
        db.query(Voice)
        .filter(Voice.service_provider_id == provider_id)
        .all()
    )
    existing_voice_map = {v.voice_id: v for v in existing_voices}
    config_voice_ids = {v["voice_id"] for v in config_voices}

    # Deactivate voices no longer in config
    for v in existing_voices:
        if v.voice_id not in config_voice_ids:
            v.is_active = False
            print(f"  [voice] deactivated: {v.voice_id}")

    # Add new voices / update existing
    for voice_spec in config_voices:
        voice_id = voice_spec["voice_id"]
        existing = existing_voice_map.get(voice_id)
        if existing:
            existing.name = voice_spec.get("name", existing.name)
            existing.language = voice_spec.get("language", existing.language)
            existing.language_list = voice_spec.get("language_list", existing.language_list)
            existing.gender = voice_spec.get("gender", existing.gender)
            existing.accent = voice_spec.get("accent")
            existing.description = voice_spec.get("description")
            existing.sample_url = voice_spec.get("sample_url")
            existing.is_active = True
        else:
            new_voice = Voice(
                service_provider_id=provider_id,
                voice_id=voice_id,
                name=voice_spec.get("name", voice_id),
                language=voice_spec.get("language", ""),
                language_list=voice_spec.get("language_list"),
                gender=voice_spec.get("gender"),
                accent=voice_spec.get("accent"),
                description=voice_spec.get("description"),
                sample_url=voice_spec.get("sample_url"),
                is_active=True,
            )
            db.add(new_voice)
            print(f"  [voice] added: {voice_id}")

    db.flush()


def main():
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Load configs from dev-data.json
    dev_data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(dev_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build lookup: (name, provider_type) -> config
    config_lookup = {}
    for section in ("llm_providers", "stt_providers", "tts_providers"):
        for config in data.get(section, []):
            key = (config["name"], config["provider_type"])
            config_lookup[key] = config

    try:
        for provider_name, provider_type in GOOGLE_PROVIDERS:
            print(f"\n── Updating: {provider_name} ({provider_type}) ──")

            # Find provider in DB
            provider = (
                db.query(ServiceProvider)
                .filter(
                    ServiceProvider.name == provider_name,
                    ServiceProvider.provider_type == provider_type,
                )
                .first()
            )

            if not provider:
                print(f"  WARNING: Provider not found in DB. Skipping.")
                continue

            # Find config in dev-data.json
            config = config_lookup.get((provider_name, provider_type))
            if not config:
                print(f"  WARNING: Config not found in dev-data.json. Skipping.")
                continue

            # Count before
            model_count_before = (
                db.query(Model)
                .filter(Model.service_provider_id == provider.id, Model.status == "active")
                .count()
            )
            voice_count_before = (
                db.query(Voice)
                .filter(Voice.service_provider_id == provider.id, Voice.is_active == True)
                .count()
            )

            update_provider(db, provider, config)

            # Count after
            model_count_after = (
                db.query(Model)
                .filter(Model.service_provider_id == provider.id, Model.status == "active")
                .count()
            )
            voice_count_after = (
                db.query(Voice)
                .filter(Voice.service_provider_id == provider.id, Voice.is_active == True)
                .count()
            )

            print(f"  Models: {model_count_before} -> {model_count_after}")
            if provider_type == "tts":
                print(f"  Voices: {voice_count_before} -> {voice_count_after}")

        db.commit()
        print("\n✓ All Google providers updated successfully.")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
