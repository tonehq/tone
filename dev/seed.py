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
import time
from datetime import datetime

# Trailing " LLM" / " STT" / " TTS" on a provider description is redundant
# (the kind is conveyed by the service-type badge on the card) and misleading
# for providers that serve multiple kinds — seed dedupes by name and only the
# first bucket's description survives, so OpenAI would get "OpenAI LLM" even
# on its STT/TTS cards. Strip the suffix at seed time so all envs stay clean.
_PROVIDER_DESC_SUFFIX_RE = re.compile(r"\s+(LLM|STT|TTS)\s*$", re.IGNORECASE)


def _clean_provider_description(description):
    if not description:
        return description
    return _PROVIDER_DESC_SUFFIX_RE.sub("", description).rstrip() or None

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


# Maps provider-specific language codes/names to canonical display names.
# Used during seeding to populate ModelLanguage.display_name so the UI
# can show a single deduplicated dropdown while keeping the provider code
# in ModelLanguage.name for runtime API calls.
LANGUAGE_DISPLAY_MAP = {
    # ── Full names ────────────────────────────────────────────────────
    "Afrikaans": "Afrikaans", "Albanian": "Albanian", "Amharic": "Amharic",
    "Arabic": "Arabic", "Armenian": "Armenian", "Assamese": "Assamese",
    "Azerbaijani": "Azerbaijani", "Basque": "Basque", "Belarusian": "Belarusian",
    "Bengali": "Bengali", "Bosnian": "Bosnian", "Bulgarian": "Bulgarian",
    "Burmese": "Burmese", "Catalan": "Catalan", "Cebuano": "Cebuano",
    "Chichewa": "Chichewa", "Chinese": "Chinese", "Chinese (Cantonese)": "Chinese (Cantonese)",
    "Chinese (Mandarin)": "Chinese", "Croatian": "Croatian", "Czech": "Czech",
    "Danish": "Danish", "Dutch": "Dutch", "English": "English",
    "English (GB)": "English", "English (US)": "English", "Estonian": "Estonian",
    "Filipino": "Filipino", "Finnish": "Finnish", "French": "French",
    "Galician": "Galician", "Georgian": "Georgian", "German": "German",
    "Greek": "Greek", "Gujarati": "Gujarati", "Haitian Creole": "Haitian Creole",
    "Hausa": "Hausa", "Hebrew": "Hebrew", "Hindi": "Hindi",
    "Hungarian": "Hungarian", "Icelandic": "Icelandic", "Indonesian": "Indonesian",
    "Irish": "Irish", "Italian": "Italian", "Japanese": "Japanese",
    "Javanese": "Javanese", "Kannada": "Kannada", "Kazakh": "Kazakh",
    "Kirghiz": "Kirghiz", "Konkani": "Konkani", "Korean": "Korean",
    "Lao": "Lao", "Latin": "Latin", "Latvian": "Latvian",
    "Lingala": "Lingala", "Lithuanian": "Lithuanian", "Luxembourgish": "Luxembourgish",
    "Macedonian": "Macedonian", "Malagasy": "Malagasy", "Malay": "Malay",
    "Malayalam": "Malayalam", "Mandarin Chinese": "Chinese", "Maori": "Maori",
    "Marathi": "Marathi", "Mongolian": "Mongolian", "Nepali": "Nepali",
    "Norwegian": "Norwegian", "Norwegian (Bokmal)": "Norwegian", "Nynorsk": "Norwegian",
    "Odia": "Odia", "Pashto": "Pashto", "Persian": "Persian",
    "Polish": "Polish", "Portugese": "Portuguese", "Portuguese": "Portuguese",
    "Punjabi": "Punjabi", "Romanian": "Romanian", "Russian": "Russian",
    "Serbian": "Serbian", "Sindhi": "Sindhi", "Sinhala": "Sinhala",
    "Slovak": "Slovak", "Slovenian": "Slovenian", "Somali": "Somali",
    "Spanish": "Spanish", "Swahili": "Swahili", "Swedish": "Swedish",
    "Tagalog": "Tagalog", "Tamil": "Tamil", "Telugu": "Telugu",
    "Thai": "Thai", "Turkish": "Turkish", "Ukrainian": "Ukrainian",
    "Urdu": "Urdu", "Vietnamese": "Vietnamese", "Welsh": "Welsh",
    # ── ISO / BCP-47 codes ────────────────────────────────────────────
    "af-ZA": "Afrikaans", "am-ET": "Amharic",
    "ar": "Arabic", "ar-001": "Arabic", "ar-EG": "Arabic",
    "az-AZ": "Azerbaijani", "be-BY": "Belarusian", "bg-BG": "Bulgarian",
    "bn": "Bengali", "bn-BD": "Bengali", "bn-IN": "Bengali",
    "ca": "Catalan", "ca-ES": "Catalan", "ceb-PH": "Cebuano",
    "cmn-CN": "Chinese", "cmn-TW": "Chinese",
    "cs-CZ": "Czech", "da-DK": "Danish",
    "de": "German", "de-DE": "German",
    "el-GR": "Greek",
    "en": "English", "en-AU": "English", "en-GB": "English",
    "en-IN": "English", "en-US": "English",
    "es": "Spanish", "es-ES": "Spanish", "es-MX": "Spanish", "es-US": "Spanish",
    "et-EE": "Estonian", "eu-ES": "Basque",
    "fa-IR": "Persian", "fi-FI": "Finnish", "fil-PH": "Filipino",
    "fr": "French", "fr-CA": "French", "fr-FR": "French",
    "gl-ES": "Galician", "gu-IN": "Gujarati",
    "he": "Hebrew", "he-IL": "Hebrew",
    "hi": "Hindi", "hi-IN": "Hindi",
    "hr-HR": "Croatian", "ht-HT": "Haitian Creole",
    "hu-HU": "Hungarian", "hy": "Armenian", "hy-AM": "Armenian",
    "id-ID": "Indonesian", "is-IS": "Icelandic",
    "it": "Italian", "it-IT": "Italian",
    "ja": "Japanese", "ja-JP": "Japanese",
    "jv-JV": "Javanese", "ka-GE": "Georgian",
    "kn-IN": "Kannada", "ko": "Korean", "ko-KR": "Korean",
    "kok-IN": "Konkani", "la-VA": "Latin",
    "lb-LU": "Luxembourgish", "lo-LA": "Lao",
    "lt-LT": "Lithuanian", "lv-LV": "Latvian",
    "mai-IN": "Maithili", "mg-MG": "Malagasy",
    "mk-MK": "Macedonian", "ml-IN": "Malayalam",
    "mn-MN": "Mongolian", "mr-IN": "Marathi",
    "ms-MY": "Malay", "my-MM": "Burmese",
    "nb-NO": "Norwegian", "ne-NP": "Nepali",
    "nl": "Dutch", "nl-NL": "Dutch",
    "nn-NO": "Norwegian",
    "od-IN": "Odia", "or-IN": "Odia",
    "pa-IN": "Punjabi",
    "pl": "Polish", "pl-PL": "Polish",
    "ps-AF": "Pashto",
    "pt": "Portuguese", "pt-BR": "Portuguese", "pt-PT": "Portuguese",
    "ro": "Romanian", "ro-RO": "Romanian",
    "ru": "Russian", "ru-RU": "Russian",
    "sd-PK": "Sindhi", "si-LK": "Sinhala",
    "sk-SK": "Slovak", "sl-SI": "Slovenian",
    "sq-AL": "Albanian", "sr-RS": "Serbian",
    "sv-SE": "Swedish", "sw-KE": "Swahili",
    "ta": "Tamil", "ta-IN": "Tamil",
    "te": "Telugu", "te-IN": "Telugu",
    "th-TH": "Thai", "tr-TR": "Turkish",
    "uk-UA": "Ukrainian", "ur-PK": "Urdu",
    "vi-VN": "Vietnamese",
    "zh": "Chinese", "zh-CN": "Chinese",
}


def _resolve_display_name(code: str) -> str:
    """Return the canonical display name for a language code/name."""
    return LANGUAGE_DISPLAY_MAP.get(code, code)


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
        "model_providers_skipped": 0,
        "models_created": 0,
        "models_skipped": 0,
        "model_voices_created": 0,
        "model_voices_skipped": 0,
        "model_languages_created": 0,
        "model_languages_skipped": 0,
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

    # --- Phase 1: Load or create ModelProvider records ---
    # Check which providers already exist in DB
    existing_providers = {
        mp.provider_id: mp
        for mp in db.query(ModelProvider).all()
    }

    provider_map = {}  # config index -> ModelProvider object
    seen_providers = {}  # provider_id_str -> ModelProvider object
    provider_schemas = {}  # provider_id_str -> {kind: [...schema...]}
    for i, config in enumerate(all_providers):
        provider_id_str = config["name"]  # e.g. "openai", "deepgram"
        kind = config["provider_type"]  # llm | stt | tts

        # Accumulate meta_data_schema per kind for each provider
        schema = config.get("meta_data_schema")
        if schema is not None:
            provider_schemas.setdefault(provider_id_str, {})[kind] = schema

        if provider_id_str in seen_providers:
            provider_map[i] = seen_providers[provider_id_str]
            continue

        # Reuse existing provider from DB if it exists
        if provider_id_str in existing_providers:
            mp = existing_providers[provider_id_str]
            provider_map[i] = mp
            seen_providers[provider_id_str] = mp
            stats["model_providers_skipped"] += 1
            continue

        slug = _slugify(config["display_name"])

        mp = ModelProvider(
            provider_id=provider_id_str,
            slug=slug,
            display_name=config["display_name"],
            description=_clean_provider_description(config.get("description")),
            is_active=config.get("status", "active") == "active",
        )
        db.add(mp)
        provider_map[i] = mp
        seen_providers[provider_id_str] = mp
        stats["model_providers_created"] += 1

    # Assign merged meta_data_schema (keyed by kind) to each provider
    for provider_id_str, mp in seen_providers.items():
        if provider_id_str in provider_schemas:
            mp.meta_data_schema = provider_schemas[provider_id_str]

    db.flush()

    # --- Phase 2: Load or create Model records ---
    # Check which models already exist in DB
    existing_models = {
        (m.provider_id, m.name): m
        for m in db.query(Model).all()
    }

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

            # Reuse existing model from DB if it exists
            if (mp.id, model_name) in existing_models:
                existing_model = existing_models[(mp.id, model_name)]
                # Update meta_data_schema if present in seed data
                new_schema = model_spec.get("meta_data_schema")
                if new_schema and existing_model.meta_data_schema != new_schema:
                    existing_model.meta_data_schema = new_schema
                model_name_to_obj[(mp.id, model_name)] = existing_model
                stats["models_skipped"] += 1
                continue

            m = Model(
                provider_id=mp.id,
                kind=kind,
                name=model_name,
                display_name=model_name,
                is_active=True,
                meta_data=model_spec.get("meta_data"),
                meta_data_schema=model_spec.get("meta_data_schema"),
            )
            db.add(m)
            model_name_to_obj[(mp.id, model_name)] = m
            stats["models_created"] += 1

    db.flush()

    # --- Phase 3: Load or create ModelVoice records (TTS providers) ---
    # Check which voices already exist in DB
    existing_voices = {
        (mv.model_id, mv.voice_id)
        for mv in db.query(ModelVoice).all()
    }

    for i, config in enumerate(all_providers):
        if i not in provider_map:
            continue
        mp = provider_map[i]
        kind = config["provider_type"]
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

            # If no specific model, try first model of this provider with matching kind
            if not model_obj:
                for key, obj in model_name_to_obj.items():
                    if key[0] == mp.id and obj.kind == kind:
                        model_obj = obj
                        break

            if not model_obj:
                continue  # skip voice if no model found

            # Skip if voice already exists in DB
            if (model_obj.id, voice_id) in existing_voices:
                stats["model_voices_skipped"] += 1
                continue

            mv = ModelVoice(
                model_id=model_obj.id,
                voice_id=voice_spec.get("voice_id"),
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

    # --- Phase 4: Load or create ModelLanguage records (from voice language_list) ---
    # Check which languages already exist in DB
    existing_languages = {
        (ml.model_id, ml.name)
        for ml in db.query(ModelLanguage).all()
    }
    seen_model_languages = set()

    for i, config in enumerate(all_providers):
        if i not in provider_map:
            continue
        mp = provider_map[i]
        kind = config["provider_type"]

        # Extract languages from voices
        for voice_spec in config.get("voices") or []:
            lang_list = voice_spec.get("language_list") or []
            voice_model_name = voice_spec.get("model_name")
            model_obj = None
            if voice_model_name:
                model_obj = model_name_to_obj.get((mp.id, voice_model_name))
            if not model_obj:
                for key, obj in model_name_to_obj.items():
                    if key[0] == mp.id and obj.kind == kind:
                        model_obj = obj
                        break
            if not model_obj:
                continue

            for lang in lang_list:
                key = (model_obj.id, lang)
                if key in seen_model_languages:
                    continue
                seen_model_languages.add(key)

                # Skip if language already exists in DB
                if key in existing_languages:
                    stats["model_languages_skipped"] += 1
                    continue

                ml = ModelLanguage(
                    model_id=model_obj.id,
                    name=lang,
                    display_name=_resolve_display_name(lang),
                    is_active=True,
                )
                db.add(ml)
                stats["model_languages_created"] += 1

    db.flush()

    # --- Phase 5: Insert ApiKey records (from env vars) ---
    # One row per (provider, service_type). A provider that appears in multiple
    # buckets (e.g. OpenAI in llm/stt/tts) gets one ApiKey per kind, all
    # sharing the same encrypted secret. service_type must be populated so the
    # Model Providers UI can render each card and per-kind defaults work via
    # the partial unique index on (org_id, service_type, is_default).
    seen_api_keys = set()  # tracks (provider_id, service_type) tuples
    for i, config in enumerate(all_providers):
        api_key_env = config.get("api_key_env")
        api_key_value = _get_api_key_from_env(api_key_env)

        if not api_key_value:
            stats["api_keys_none"] += 1
            continue

        if i not in provider_map:
            continue

        mp = provider_map[i]
        kind = config["provider_type"]  # llm | stt | tts

        key = (mp.id, kind)
        if key in seen_api_keys:
            continue
        seen_api_keys.add(key)

        api_key = ApiKey(
            organization_id=org_id,
            provider_id=mp.id,
            service_type=kind,
            label=f"seed ({kind})",
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


def _run_chained_seeder(label: str, module_path: str) -> None:
    """Run a standalone seeder script (e.g. ``dev.seed_app_integrations``) as
    part of the main seed flow.

    The chained scripts call ``sys.exit(1)`` on internal errors — we catch
    ``SystemExit`` so a failure there only skips that step instead of aborting
    the whole seed. Each chained seeder opens its own DB session, so the
    in-flight ``main()`` session above is not affected.
    """
    print(f"\nSeeding {label}...")
    try:
        import importlib

        module = importlib.import_module(module_path)
        module.main()
    except SystemExit as exc:
        print(f"   ⚠ {label} seeder exited (code={exc.code}); continuing.")
    except Exception as exc:
        print(f"   ⚠ {label} seeder failed: {exc}; continuing.")


def main():
    from core.database.session import get_db_script

    # Prompt for setup inputs before touching the DB
    org_name, email, password = prompt_setup_inputs()

    db = get_db_script()
    started_at = datetime.now()
    start = time.perf_counter()
    print(f"\nSeed started at: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
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
        print(f"   Model Providers:  {stats['model_providers_created']} created, {stats['model_providers_skipped']} already existed")
        print(f"   Models:           {stats['models_created']} created, {stats['models_skipped']} already existed")
        print(f"   Model Voices:     {stats['model_voices_created']} created, {stats['model_voices_skipped']} already existed")
        print(f"   Model Languages:  {stats['model_languages_created']} created, {stats['model_languages_skipped']} already existed")
        print(f"   API keys:         {stats['api_keys_created']} created, {stats['api_keys_none']} no env key")
        print(f"   Tools:            {stats['tools_created']} created")

        # Chain the standalone seeders so a single ``python dev/seed.py`` run
        # leaves the deployment fully seeded. They open their own DB sessions
        # and are safe to re-run — any failure is logged but doesn't abort the
        # main setup (each seeder is isolated in its own try block).
        _run_chained_seeder("app_integrations", "dev.seed_app_integrations")
        _run_chained_seeder("built-in tools", "dev.seed_built_in_tools")
    finally:
        db.close()
        ended_at = datetime.now()
        elapsed = time.perf_counter() - start
        print(f"\nSeed started:  {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Seed ended:    {ended_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total time:    {elapsed:.2f}s ({elapsed / 60:.2f} min)")


if __name__ == "__main__":
    main()
