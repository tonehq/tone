"""
Reseed script: Update meta_data_schema on model providers, delete and
repopulate models, voices, and languages from dev-data.json.

Does NOT delete or recreate model providers or API keys.

Steps:
  1. Accumulate meta_data_schema per kind for each provider
  2. Update meta_data_schema on existing ModelProvider records
  3. Per provider config:
     a. Delete voices (model_voices → models FK)
     b. Delete languages (model_languages → models FK)
     c. Delete models
     d. Recreate models
     e. Recreate voices
     f. Recreate languages

Usage:
    python dev/reseed_models_voices.py
"""

import os
import sys

# Ensure project root is on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()


def load_seed_data():
    import json
    data_path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Reuse the language display map from the seed script
from dev.seed import LANGUAGE_DISPLAY_MAP


def _resolve_display_name(code: str) -> str:
    return LANGUAGE_DISPLAY_MAP.get(code, code)


def main():
    from core.database.session import get_db_script
    from core.models.model_provider import ModelProvider
    from core.models.model import Model
    from core.models.model_voice import ModelVoice
    from core.models.model_language import ModelLanguage

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
            "languages_deleted": 0,
            "languages_created": 0,
        }

        print(f"Loaded {len(all_providers)} provider configs from dev-data.json\n")

        # --- Step 1: Accumulate meta_data_schema per kind for each provider ---
        provider_schemas = {}  # provider_id_str -> {kind: [...schema...]}
        for config in all_providers:
            name = config["name"]
            kind = config["provider_type"]
            schema = config.get("meta_data_schema")
            if schema is not None:
                provider_schemas.setdefault(name, {})[kind] = schema

        # --- Step 2: Update meta_data_schema on existing ModelProvider records ---
        all_provider_names = list({c["name"] for c in all_providers})
        existing_providers = (
            db.query(ModelProvider)
            .filter(ModelProvider.provider_id.in_(all_provider_names))
            .all()
        )
        provider_by_name = {p.provider_id: p for p in existing_providers}

        for provider_id_str, schema_dict in provider_schemas.items():
            mp = provider_by_name.get(provider_id_str)
            if mp:
                mp.meta_data_schema = schema_dict
                stats["providers_updated"] += 1
            else:
                print(f"  SKIP schema  {provider_id_str} — not found in DB")

        db.flush()

        # --- Step 3: Per provider config — reseed models, voices, languages ---
        for config in all_providers:
            name = config["name"]
            kind = config["provider_type"]
            display_name = config.get("display_name", name)
            models_spec = config.get("models") or []
            voices_spec = config.get("voices") or []

            mp = provider_by_name.get(name)
            if not mp:
                print(f"  SKIP  {display_name} ({kind}) — not found in DB")
                stats["providers_not_found"] += 1
                continue

            print(f"  Processing {display_name} ({kind}, id={mp.id})")

            # Find existing models for this provider + kind
            existing_models = (
                db.query(Model)
                .filter(Model.provider_id == mp.id, Model.kind == kind)
                .all()
            )
            existing_model_ids = [m.id for m in existing_models]

            # 3a. Delete voices linked to these models
            if existing_model_ids:
                voice_count = (
                    db.query(ModelVoice)
                    .filter(ModelVoice.model_id.in_(existing_model_ids))
                    .delete(synchronize_session=False)
                )
                stats["voices_deleted"] += voice_count

                # 3b. Delete languages linked to these models
                lang_count = (
                    db.query(ModelLanguage)
                    .filter(ModelLanguage.model_id.in_(existing_model_ids))
                    .delete(synchronize_session=False)
                )
                stats["languages_deleted"] += lang_count

            # 3c. Delete models
            if existing_model_ids:
                db.query(Model).filter(Model.id.in_(existing_model_ids)).delete(
                    synchronize_session=False
                )
                stats["models_deleted"] += len(existing_model_ids)

            db.flush()

            # 3d. Recreate models
            model_name_to_obj = {}
            for model_spec in models_spec:
                model_name = model_spec.get("name") or "default"
                m = Model(
                    provider_id=mp.id,
                    kind=kind,
                    name=model_name,
                    display_name=model_name,
                    is_active=True,
                )
                db.add(m)
                model_name_to_obj[model_name] = m

            db.flush()
            stats["models_created"] += len(models_spec)

            # 3e. Recreate voices
            seen_voice_ids = set()
            for voice_spec in voices_spec:
                voice_id = voice_spec.get("voice_id")
                if not voice_id or voice_id in seen_voice_ids:
                    continue
                seen_voice_ids.add(voice_id)

                # Resolve model for this voice
                model_obj = None
                voice_model_name = voice_spec.get("model_name")
                if voice_model_name:
                    model_obj = model_name_to_obj.get(voice_model_name)
                if not model_obj and model_name_to_obj:
                    model_obj = next(iter(model_name_to_obj.values()))
                if not model_obj:
                    continue

                mv = ModelVoice(
                    model_id=model_obj.id,
                    voice_id=voice_id,
                    accent=voice_spec.get("accent"),
                    name=voice_spec.get("name"),
                    gender=voice_spec.get("gender"),
                    description=(voice_spec.get("description") or "")[:200] or None,
                    language_list=voice_spec.get("language_list"),
                    sample_url=voice_spec.get("sample_url"),
                    is_active=True,
                )
                db.add(mv)
                stats["voices_created"] += 1

            # 3f. Recreate languages (from voice language_list)
            seen_model_languages = set()
            for voice_spec in voices_spec:
                lang_list = voice_spec.get("language_list") or []
                voice_model_name = voice_spec.get("model_name")
                model_obj = None
                if voice_model_name:
                    model_obj = model_name_to_obj.get(voice_model_name)
                if not model_obj and model_name_to_obj:
                    model_obj = next(iter(model_name_to_obj.values()))
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
                        display_name=_resolve_display_name(lang),
                        is_active=True,
                    )
                    db.add(ml)
                    stats["languages_created"] += 1

        db.commit()

        print(f"\n{'='*50}")
        print("DONE")
        print(f"{'='*50}")
        print(f"  Providers updated:    {stats['providers_updated']}")
        print(f"  Providers not found:  {stats['providers_not_found']}")
        print(f"  Models deleted:       {stats['models_deleted']}")
        print(f"  Models created:       {stats['models_created']}")
        print(f"  Voices deleted:       {stats['voices_deleted']}")
        print(f"  Voices created:       {stats['voices_created']}")
        print(f"  Languages deleted:    {stats['languages_deleted']}")
        print(f"  Languages created:    {stats['languages_created']}")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
