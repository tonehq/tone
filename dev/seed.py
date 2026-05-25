"""
Seed script for initial Tone v2 setup.
Run from project root: python dev/seed.py   or   python -m dev.seed

Prompts the installer for organization name, owner email, and password,
then seeds:
- User (owner)
- Organization
- Member (linking user to org as owner)
- ModelProvider records (LLM, STT, TTS)
- Model records (per provider)
- ModelVoice records (for TTS providers that have voices)
- ModelLanguage records (for STT providers that have languages)
- ApiKey records (from environment variables, linked to providers)
- Tool records (built-in tools)
"""
import os
import sys
import json
import re
import getpass

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


def _slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def _validate_email(email):
    """Basic email format validation."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def _validate_password(password):
    """Validate password: min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit, 1 special char."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        return False, "Password must contain at least one special character."
    return True, ""


def prompt_setup_inputs():
    """Prompt the installer for organization name, owner email, and password."""
    print("\n── Tone Setup ──\n")

    # Organization name
    while True:
        org_name = input("Organization name: ").strip()
        if org_name:
            break
        print("  Organization name cannot be empty.")

    # Owner email
    while True:
        email = input("Owner email: ").strip()
        if _validate_email(email):
            break
        print("  Please enter a valid email address.")

    # Password
    while True:
        password = getpass.getpass("Password: ")
        valid, msg = _validate_password(password)
        if not valid:
            print(f"  {msg}")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("  Passwords do not match.")
            continue
        break

    return org_name, email, password


def seed_user(db, email, password):
    """Create the seed user. Returns the user record."""
    from core.models.user import User
    from core.utils.security import hash_password

    user = User(
        email=email,
        first_name=email.split("@")[0],
        password_hash=hash_password(password),
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def seed_organization(db, org_name):
    """Create the seed organization. Returns the organization record."""
    from core.models.organization import Organization

    slug = _slugify(org_name)

    org = Organization(
        name=org_name,
        slug=slug,
    )
    db.add(org)
    db.flush()
    return org


def seed_member(db, user, org):
    """Create the member linking user to organization as owner."""
    from core.models.member import Member

    member = Member(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(member)
    db.flush()
    return member


def seed_from_configs(db, org_name, email, password):
    """
    Seed user, org, member, providers, models, API keys, voices, and tools.
    Inserts all records directly (assumes fresh database).
    """
    from core.models.model_provider import ModelProvider
    from core.models.model import Model
    from core.models.model_voice import ModelVoice
    from core.models.model_language import ModelLanguage
    from core.models.api_key import ApiKey
    from core.models.tool import Tool
    from core.utils.encryption import encrypt

    # 0. Create seed user, organization, and member
    user = seed_user(db, email, password)
    org = seed_organization(db, org_name)
    seed_member(db, user, org)

    # Link user to organization
    user.organization_id = org.id

    org_id = org.id

    stats = {
        "model_providers_created": 0,
        "models_created": 0,
        "model_voices_created": 0,
        "model_languages_created": 0,
        "api_keys_created": 0,
        "api_keys_none": 0,
        "tools_created": 0,
    }

    # Load all provider configs from JSON
    data = load_seed_data()

    # Combine all providers (LLM, STT, TTS) into a single list
    all_providers = []
    all_providers.extend(data.get("llm_providers", []))
    all_providers.extend(data.get("stt_providers", []))
    all_providers.extend(data.get("tts_providers", []))

    # --- Phase 1: Insert ModelProvider records ---
    provider_map = {}  # config index -> ModelProvider object
    seen_providers = {}  # provider_id_str -> ModelProvider object
    for i, config in enumerate(all_providers):
        provider_id_str = config["name"]  # e.g. "openai", "deepgram"

        if provider_id_str in seen_providers:
            provider_map[i] = seen_providers[provider_id_str]
            continue

        slug = _slugify(config["display_name"])

        mp = ModelProvider(
            provider_id=provider_id_str,
            slug=slug,
            display_name=config["display_name"],
            description=config.get("description"),
            is_active=config.get("status", "active") == "active",
        )
        db.add(mp)
        provider_map[i] = mp
        seen_providers[provider_id_str] = mp
        stats["model_providers_created"] += 1

    db.flush()

    # --- Phase 2: Insert Model records ---
    model_name_to_obj = {}  # (provider_uuid, model_name) -> Model object
    for i, config in enumerate(all_providers):
        if i not in provider_map:
            continue
        mp = provider_map[i]
        kind = config["provider_type"]  # llm | stt | tts

        for model_spec in config.get("models") or []:
            model_name = model_spec.get("name") or "default"

            if (mp.id, model_name) in model_name_to_obj:
                continue

            m = Model(
                provider_id=mp.id,
                kind=kind,
                name=model_name,
                display_name=model_name,
                is_active=True,
            )
            db.add(m)
            model_name_to_obj[(mp.id, model_name)] = m
            stats["models_created"] += 1

    db.flush()

    # --- Phase 3: Insert ModelVoice records (TTS providers) ---
    for i, config in enumerate(all_providers):
        if i not in provider_map:
            continue
        mp = provider_map[i]
        voices_spec = config.get("voices") or []
        seen_voice_ids = set()

        for voice_spec in voices_spec:
            voice_id = voice_spec.get("voice_id")
            if not voice_id or voice_id in seen_voice_ids:
                continue
            seen_voice_ids.add(voice_id)

            # Find the model this voice belongs to
            voice_model_name = voice_spec.get("model_name")
            model_obj = None
            if voice_model_name:
                model_obj = model_name_to_obj.get((mp.id, voice_model_name))

            # If no specific model, try first model of this provider
            if not model_obj:
                for key, obj in model_name_to_obj.items():
                    if key[0] == mp.id:
                        model_obj = obj
                        break

            if not model_obj:
                continue  # skip voice if no model found

            mv = ModelVoice(
                model_id=model_obj.id,
                accent=voice_spec.get("accent"),
                name=voice_spec.get("name"),
                gender=voice_spec.get("gender"),
                description=(voice_spec.get("description") or "")[:200] or None,
                language_list=voice_spec.get("language_list"),
                sample_url=voice_spec.get("sample_url"),
                is_active=True,
            )
            db.add(mv)
            stats["model_voices_created"] += 1

    db.flush()

    # --- Phase 4: Insert ModelLanguage records (STT providers with language_list) ---
    seen_model_languages = set()
    for i, config in enumerate(all_providers):
        if i not in provider_map:
            continue
        mp = provider_map[i]

        # Extract languages from voices or from model meta_data
        for voice_spec in config.get("voices") or []:
            lang_list = voice_spec.get("language_list") or []
            voice_model_name = voice_spec.get("model_name")
            model_obj = None
            if voice_model_name:
                model_obj = model_name_to_obj.get((mp.id, voice_model_name))
            if not model_obj:
                for key, obj in model_name_to_obj.items():
                    if key[0] == mp.id:
                        model_obj = obj
                        break
            if not model_obj:
                continue

            for lang in lang_list:
                key = (model_obj.id, lang)
                if key in seen_model_languages:
                    continue
                seen_model_languages.add(key)

                ml = ModelLanguage(
                    model_id=model_obj.id,
                    name=lang,
                    is_active=True,
                )
                db.add(ml)
                stats["model_languages_created"] += 1

    db.flush()

    # --- Phase 5: Insert ApiKey records (from env vars) ---
    seen_api_keys = set()  # track provider IDs already keyed
    for i, config in enumerate(all_providers):
        api_key_env = config.get("api_key_env")
        api_key_value = _get_api_key_from_env(api_key_env)

        if not api_key_value:
            stats["api_keys_none"] += 1
            continue

        if i not in provider_map:
            continue

        mp = provider_map[i]

        if mp.id in seen_api_keys:
            continue
        seen_api_keys.add(mp.id)

        api_key = ApiKey(
            organization_id=org_id,
            provider_id=mp.id,
            label="seed",
            encrypted_key=encrypt(api_key_value),
            is_active=True,
        )
        db.add(api_key)
        stats["api_keys_created"] += 1

    db.flush()

    # --- Phase 6: Insert built-in Tool records ---
    # for tool_spec in data.get("built_in_tools", []):
    #     tool = Tool(
    #         organization_id=org_id,
    #         name=tool_spec["name"],
    #         description=tool_spec.get("description"),
    #         tool_type=tool_spec.get("tool_type", "built_in"),
    #         action_params_schema=tool_spec.get("parameters"),
    #     )
    #     db.add(tool)
    #     stats["tools_created"] += 1

    db.commit()
    return stats


def main():
    from core.database.session import get_db_script

    # Prompt for setup inputs before touching the DB
    org_name, email, password = prompt_setup_inputs()

    db = get_db_script()
    try:
        print("\nLoading seed data from dev-data.json...")
        data = load_seed_data()
        print(f"   Found {len(data.get('llm_providers', []))} LLM providers")
        print(f"   Found {len(data.get('stt_providers', []))} STT providers")
        print(f"   Found {len(data.get('tts_providers', []))} TTS providers")

        print("\nSeeding...")
        stats = seed_from_configs(db, org_name, email, password)

        print(f"\n✓ Setup complete:")
        print(f"   User:             created ({email})")
        print(f"   Org:              created ({org_name})")
        print(f"   Member:           created")
        print(f"   Model Providers:  {stats['model_providers_created']} created")
        print(f"   Models:           {stats['models_created']} created")
        print(f"   Model Voices:     {stats['model_voices_created']} created")
        print(f"   Model Languages:  {stats['model_languages_created']} created")
        print(f"   API keys:         {stats['api_keys_created']} created, {stats['api_keys_none']} no env key")
        print(f"   Tools:            {stats['tools_created']} created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
