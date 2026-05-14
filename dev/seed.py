"""
Seed script for initial Tone setup.
Run from project root: python dev/seed.py   or   python -m dev.seed

Prompts the installer for organization name, owner email, and password,
then seeds:
- User (owner)
- Organization
- Member (linking user to org as OWNER)
- ModelProviderMenu records (LLM, STT, TTS model creators)
- HostingProvider records (model hosts)
- HostingProviderModel records (which hosts serve which creators)
- ModelMenu records (available models)
- ModelInstance records (model deployed on a host)
- ApiKey records (from environment variables, linked to hosting providers)
- Service records (one per provider that has an API key, linked to model instances)
- Voice records (for TTS providers that have voices defined)
- ServiceProvider records (telephony only, if present in dev-data.json)
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
    from core.models.enums import UserStatus, AuthProvider
    from core.utils.security import hash_password

    username = email.split("@")[0]

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        auth_provider=AuthProvider.EMAIL,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def seed_organization(db, user, org_name):
    """Create the seed organization. Returns the organization record."""
    from core.models.organization import Organization
    from core.models.enums import OrganizationStatus

    slug = _slugify(org_name)

    org = Organization(
        name=org_name,
        slug=slug,
        status=OrganizationStatus.ACTIVE,
        created_by=user.id,
    )
    db.add(org)
    db.flush()
    return org


def seed_member(db, user, org):
    """Create the member linking user to organization. Returns the member record."""
    from core.models.member import Member
    from core.models.enums import Role
    import time

    member = Member(
        organization_id=org.id,
        user_id=user.id,
        role=Role.OWNER,
        status="active",
        created_by=user.id,
        joined_at=int(time.time()),
    )
    db.add(member)
    db.flush()
    return member


def seed_from_configs(db, org_name, email, password):
    """
    Seed user, org, member, providers, models, API keys, and voices.
    Inserts all records directly (assumes fresh database).
    """
    from core.models.voice import Voice
    from core.models.api_key import ApiKey
    from core.models.account import Account
    from core.models.tool import Tool
    from core.models.model_provider_menu import ModelProviderMenu
    from core.models.hosting_provider import HostingProvider
    from core.models.model_menu import ModelMenu
    from core.models.model_instance import ModelInstance
    from core.utils.encryption import encrypt

    # 0. Create seed user, organization, and member first
    user = seed_user(db, email, password)
    user_id = user.id

    org = seed_organization(db, user, org_name)
    org_id = org.id

    seed_member(db, user, org)

    stats = {
        "api_keys_created": 0,
        "api_keys_none": 0,
        "services_created": 0,
        "voices_created": 0,
        "tools_created": 0,
        "model_provider_menus_created": 0,
        "hosting_providers_created": 0,
        "model_menus_created": 0,
        "model_instances_created": 0,
    }

    # Load all provider configs from JSON
    data = load_seed_data()

    # Combine all providers (LLM, STT, TTS) into a single list for processing
    all_providers = []
    all_providers.extend(data.get("llm_providers", []))
    all_providers.extend(data.get("stt_providers", []))
    all_providers.extend(data.get("tts_providers", []))

    # --- Phase 1: Insert ModelProviderMenu (LLM/STT/TTS) ---
    model_provider_menu_map = {}  # config index -> ModelProviderMenu object
    for i, config in enumerate(all_providers):
        if config["provider_type"] == "telephony":
            continue
        mpm = ModelProviderMenu(
            name=config["name"],
            display_name=config["display_name"],
            provider_type=config["provider_type"],
            auth_type="api_key",
            description=config.get("description") or f"Model provider: {config['display_name']} ({config['provider_type']})",
            status=config.get("status", "active"),
            is_system=True,
            meta_data_schema=config.get("meta_data_schema"),
        )
        db.add(mpm)
        model_provider_menu_map[i] = mpm
        stats["model_provider_menus_created"] += 1

    db.flush()

    # --- Phase 2: Insert HostingProviders + join table ---
    # For initial seed, each model creator is also its own default host
    hosting_provider_map = {}  # config index -> HostingProvider object
    for i, config in enumerate(all_providers):
        if config["provider_type"] == "telephony" or i not in model_provider_menu_map:
            continue
        hp = HostingProvider(
            name=config["name"],
            display_name=config["display_name"],
            description=config.get("description") or f"Hosting provider: {config['display_name']}",
            status=config.get("status", "active"),
            is_system=True,
        )
        db.add(hp)
        hosting_provider_map[i] = hp
        stats["hosting_providers_created"] += 1

    db.flush()

    # --- Phase 3: Insert ModelMenu ---
    model_menu_name_to_obj = {}  # (mpm_id, model_name) -> ModelMenu object
    for i, config in enumerate(all_providers):
        if config["provider_type"] == "telephony" or i not in model_provider_menu_map:
            continue
        mpm = model_provider_menu_map[i]
        for model_spec in config.get("models") or []:
            model_name = model_spec.get("name") or "default"
            mm = ModelMenu(
                model_provider_menu_id=mpm.id,
                name=model_name,
                service_type=config["provider_type"],
                status="active",
                meta_data=model_spec.get("meta_data"),
            )
            db.add(mm)
            model_menu_name_to_obj[(mpm.id, model_name)] = mm
            stats["model_menus_created"] += 1

    db.flush()

    # --- Phase 4: Insert ModelInstance ---
    model_instance_map = {}  # (mpm_id, model_name) -> ModelInstance object
    for i, config in enumerate(all_providers):
        if config["provider_type"] == "telephony" or i not in model_provider_menu_map:
            continue
        mpm = model_provider_menu_map[i]
        for model_spec in config.get("models") or []:
            model_name = model_spec.get("name") or "default"
            mm = model_menu_name_to_obj.get((mpm.id, model_name))
            if not mm:
                continue
            mi = ModelInstance(
                model_menu_id=mm.id,
                status="active",
            )
            db.add(mi)
            model_instance_map[(mpm.id, model_name)] = mi
            stats["model_instances_created"] += 1

    db.flush()

    # --- Phase 5: Insert API keys ---
    api_key_obj_map = {}  # config index -> ApiKey object
    for i, config in enumerate(all_providers):
        api_key_env = config.get("api_key_env")
        api_key_value = _get_api_key_from_env(api_key_env)

        if not api_key_value:
            stats["api_keys_none"] += 1
            continue

        if i not in model_provider_menu_map:
            continue

        hint = api_key_value[:4] + "..." + api_key_value[-4:] if len(api_key_value) > 8 else "****"

        api_key = ApiKey(
            organization_id=org_id,
            name="seed",
            api_key_encrypted=encrypt(api_key_value),
            api_key_hint=hint,
            status="active",
            created_by=user_id,
        )
        db.add(api_key)
        api_key_obj_map[i] = api_key
        stats["api_keys_created"] += 1

    db.flush()

    # --- Phase 6: Insert Account records (linked to hosting provider + model provider menu) ---
    for i, config in enumerate(all_providers):
        if i not in api_key_obj_map:
            continue

        provider_type = config["provider_type"]
        api_key_obj = api_key_obj_map[i]
        mpm = model_provider_menu_map.get(i)

        hp = hosting_provider_map.get(i)
        account = Account(
            model_provider_menu_id=mpm.id if mpm else None,
            hosting_provider_id=hp.id if hp else None,
            organization_id=org_id,
            name=f"{config['display_name']} {provider_type.upper()}",
            description=config.get("description") or f"{config['display_name']} {provider_type} account",
            service_type=provider_type,
            config={},
            status=config.get("status", "active"),
            is_default=True,
            created_by=user_id,
        )

        db.add(account)
        db.flush()

        # Link the API key to this account (reverse FK direction)
        api_key_obj.account_id = account.id

        # Link existing model instances to this account
        if mpm:
            mpm_model_menu_ids = [
                mm.id for mm in db.query(ModelMenu).filter(
                    ModelMenu.model_provider_menu_id == mpm.id
                ).all()
            ]
            if mpm_model_menu_ids:
                db.query(ModelInstance).filter(
                    ModelInstance.model_menu_id.in_(mpm_model_menu_ids),
                    ModelInstance.account_id.is_(None),
                ).update({"account_id": account.id}, synchronize_session=False)

        stats["services_created"] += 1

    db.flush()

    # --- Phase 7: Insert voices ---
    # Use model_provider_menu_id + model_menu_id (new path)
    # service_provider_id and model_id are left NULL for LLM/STT/TTS
    for i, config in enumerate(all_providers):
        mpm = model_provider_menu_map.get(i)
        if not mpm:
            continue  # skip telephony — no voices for telephony
        voices_spec = config.get("voices") or []
        seen_voice_ids = set()
        for voice_spec in voices_spec:
            voice_id = voice_spec.get("voice_id")
            if not voice_id or voice_id in seen_voice_ids:
                continue
            seen_voice_ids.add(voice_id)

            voice_model_menu_id = None
            voice_model_name = voice_spec.get("model_name")
            if voice_model_name:
                mm_obj = model_menu_name_to_obj.get((mpm.id, voice_model_name))
                if mm_obj:
                    voice_model_menu_id = mm_obj.id

            voice = Voice(
                model_provider_menu_id=mpm.id,
                model_menu_id=voice_model_menu_id,
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

    # --- Phase 8: Insert built-in tools ---
    for tool_spec in data.get("built_in_tools", []):
        tool = Tool(
            organization_id=org_id,
            name=tool_spec["name"],
            description=tool_spec["description"],
            tool_type=tool_spec.get("tool_type", "built_in"),
            parameters=tool_spec.get("parameters"),
            is_active=True,
            is_template=True,
        )
        db.add(tool)
        stats["tools_created"] += 1

    db.commit()  # Single commit: everything becomes permanent
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
        print(f"   User:      created ({email})")
        print(f"   Org:       created ({org_name})")
        print(f"   Member:    created")
        print(f"   API keys:  {stats['api_keys_created']} created, {stats['api_keys_none']} no env key")
        print(f"   Services:  {stats['services_created']} created")
        print(f"   Voices:    {stats['voices_created']} created")
        print(f"   Tools:     {stats['tools_created']} created")
        print(f"   Model Provider Menus: {stats['model_provider_menus_created']} created")
        print(f"   Hosting Providers:    {stats['hosting_providers_created']} created")
        print(f"   Model Menus:          {stats['model_menus_created']} created")
        print(f"   Model Instances:      {stats['model_instances_created']} created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
