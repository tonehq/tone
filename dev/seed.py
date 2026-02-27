"""
Seed service providers with their models, API keys, and voices (from .env).
Run from project root: python dev/seed.py   or   python -m dev.seed

Reads service provider data from dev/dev-data.json and creates:
- ServiceProvider records (LLM, STT, TTS providers)
- Model records (all models for each provider)
- ApiKey records (from environment variables)
- Voice records (for TTS providers that have voices defined)
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
    """Load service provider configurations from dev-data.json."""
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_api_key_from_env(env_var_name):
    """Return API key value from env, or None if var missing/empty."""
    if not env_var_name:
        return None
    value = os.environ.get(env_var_name) or ""
    return value.strip() or None


def seed_user(db):
    """Create or get the seed user. Returns the user record."""
    from core.models.user import User
    from core.models.enums import UserStatus, AuthProvider
    from core.utils.security import hash_password

    email = "thilak.gunasekaran@productfusion.co"
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing, False

    user = User(
        email=email,
        username="thilak.gunasekaran",
        password_hash=hash_password("Pass@123"),
        first_name="Thilak",
        last_name="Gunasekaran",
        auth_provider=AuthProvider.EMAIL,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    return user, True


def seed_from_configs(db):
    """
    Seed providers, models, and API keys from the loaded JSON data.
    For each config: create or get ServiceProvider -> create or get all Models
    -> if api_key_env set in env, create or get ApiKey and link to all models of that provider.
    """
    from core.models.voice import Voice
    from core.models.service_provider import ServiceProvider
    from core.models.models import Model
    from core.models.api_key import ApiKey
    from core.utils.encryption import encrypt

    # 0. Create seed user first
    user, user_created = seed_user(db)
    user_id = user.id

    stats = {
        "user_created": "",
        "providers_created": 0,
        "providers_skipped": 0,
        "models_created": 0,
        "models_skipped": 0,
        "api_keys_created": 0,
        "api_keys_skipped": 0,
        "api_keys_none": 0,
        "voices_created": 0,
        "voices_skipped": 0,
    }

    # Load all provider configs from JSON
    data = load_seed_data()

    # Combine all providers (LLM, STT, TTS) into a single list for processing
    all_providers = []
    all_providers.extend(data.get("llm_providers", []))
    all_providers.extend(data.get("stt_providers", []))
    all_providers.extend(data.get("tts_providers", []))

    stats["user_created"] = "created" if user_created else "already existed"

    for config in all_providers:
        name = config["name"]
        provider_type = config["provider_type"]
        display_name = config["display_name"]
        description = config.get("description") or f"Service provider: {display_name} ({provider_type})"
        api_key_env = config.get("api_key_env")
        models_spec = config.get("models") or []
        meta_data_schema = config.get("meta_data_schema")

        # 1. Get or create ServiceProvider
        provider = (
            db.query(ServiceProvider)
            .filter(
                ServiceProvider.name == name,
                ServiceProvider.provider_type == provider_type,
            )
            .first()
        )
        if not provider:
            provider = ServiceProvider(
                name=name,
                display_name=display_name,
                provider_type=provider_type,
                auth_type="api_key",
                description=description,
                status="active",
                is_system=True,
                meta_data_schema=meta_data_schema,
            )
            db.add(provider)
            db.flush()
            stats["providers_created"] += 1
        else:
            if meta_data_schema and provider.meta_data_schema != meta_data_schema:
                provider.meta_data_schema = meta_data_schema
            stats["providers_skipped"] += 1

        # 2. Get or create each Model for this provider
        for model_spec in models_spec:
            model_name = model_spec.get("name") or "default"
            meta_data = model_spec.get("meta_data")
            existing = (
                db.query(Model)
                .filter(
                    Model.service_provider_id == provider.id,
                    Model.name == model_name,
                )
                .first()
            )
            if not existing:
                model = Model(
                    service_provider_id=provider.id,
                    name=model_name,
                    service_type=provider_type,
                    status="active",
                    meta_data=meta_data,
                    api_key_id=None,
                )
                db.add(model)
                db.flush()
                stats["models_created"] += 1
            else:
                stats["models_skipped"] += 1

        # 3. API key: if env var set, get or create ApiKey and link to all models of this provider
        api_key_value = _get_api_key_from_env(api_key_env)
        if not api_key_value:
            stats["api_keys_none"] += 1
        else:
            existing_key = (
                db.query(ApiKey)
                .filter(
                    ApiKey.service_provider_id == provider.id,
                    ApiKey.status == "active",
                )
                .first()
            )
            if existing_key:
                stats["api_keys_skipped"] += 1
                api_key_id = existing_key.id
            else:
                hint = api_key_value[:4] + "..." + api_key_value[-4:] if len(api_key_value) > 8 else "****"
                api_key = ApiKey(
                    service_provider_id=provider.id,
                    name="seed",
                    api_key_encrypted=encrypt(api_key_value),
                    api_key_hint=hint,
                    status="active",
                    created_by=user_id,
                )
                db.add(api_key)
                db.flush()
                api_key_id = api_key.id
                stats["api_keys_created"] += 1

            # Link all models of this provider to this API key
            db.query(Model).filter(
                Model.service_provider_id == provider.id,
                Model.status == "active",
            ).update({Model.api_key_id: api_key_id}, synchronize_session=False)

        # 4. Voices: if voices defined for this provider, get or create Voice records
        voices_spec = config.get("voices") or []
        seen_voice_ids = set()
        for voice_spec in voices_spec:
            voice_id = voice_spec.get("voice_id")
            if not voice_id or voice_id in seen_voice_ids:
                stats["voices_skipped"] += 1
                continue
            seen_voice_ids.add(voice_id)
            existing_voice = (
                db.query(Voice)
                .filter(
                    Voice.service_provider_id == provider.id,
                    Voice.voice_id == voice_id,
                )
                .first()
            )
            if not existing_voice:
                voice = Voice(
                    service_provider_id=provider.id,
                    # model_id=None,
                    voice_id=voice_id,
                    name=voice_spec.get("name"),
                    language=voice_spec.get("language") or "",
                    gender=voice_spec.get("gender"),
                    accent=voice_spec.get("accent"),
                    description=voice_spec.get("description"),
                    sample_url=voice_spec.get("sample_url"),
                    is_active=True,
                )
                db.add(voice)
                stats["voices_created"] += 1
            else:
                stats["voices_skipped"] += 1

    db.commit()
    return stats


def main():
    from core.database.session import get_db_script

    db = get_db_script()
    try:
        print("Loading seed data from dev-data.json...")
        data = load_seed_data()
        print(f"   Found {len(data.get('llm_providers', []))} LLM providers")
        print(f"   Found {len(data.get('stt_providers', []))} STT providers")
        print(f"   Found {len(data.get('tts_providers', []))} TTS providers")
        
        print("\nSeeding user, service providers, models, API keys, and voices...")
        stats = seed_from_configs(db)

        print(f"\n✓ Seeding complete:")
        print(f"   User:      {stats['user_created']}")
        print(f"   Providers: {stats['providers_created']} created, {stats['providers_skipped']} already existed.")
        print(f"   Models:    {stats['models_created']} created, {stats['models_skipped']} already existed.")
        print(f"   API keys:  {stats['api_keys_created']} created, {stats['api_keys_skipped']} already existed, {stats['api_keys_none']} no env key.")
        print(f"   Voices:    {stats['voices_created']} created, {stats['voices_skipped']} already existed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
