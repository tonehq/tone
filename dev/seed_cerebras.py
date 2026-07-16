"""Idempotent upsert of the Cerebras LLM provider + its models.

Standalone, org-agnostic seeder. Unlike ``dev/seed.py`` (which creates a fresh
user/org and assumes an empty DB), this only touches the global
``model_providers`` / ``models`` catalog tables and is safe to re-run against an
already-populated database (local, staging, prod). It reads the ``cerebras``
entry from ``dev/dev-data.json`` so the source of truth stays in one place.

    PYTHONPATH=. python dev/seed_cerebras.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from core.database.session import get_db_script
    from core.models.model import Model
    from core.models.model_provider import ModelProvider

    # Reuse the single slug implementation from dev/seed.py (imported lazily so this
    # standalone seeder stays light and the slug logic lives in one place).
    from dev.seed import _slugify

    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev-data.json")
    with open(data_path) as f:
        data = json.load(f)

    config = next(
        (p for p in data.get("llm_providers", []) if p["name"] == "cerebras"), None
    )
    if config is None:
        print("✗ No 'cerebras' entry found in dev-data.json"); sys.exit(1)

    provider_id_str = config["name"]
    kind = config["provider_type"]

    db = get_db_script()
    stats = {"provider_created": 0, "provider_skipped": 0, "models_created": 0, "models_skipped": 0}
    try:
        mp = (
            db.query(ModelProvider)
            .filter(ModelProvider.provider_id == provider_id_str)
            .one_or_none()
        )
        if mp is None:
            mp = ModelProvider(
                provider_id=provider_id_str,
                slug=_slugify(config["display_name"]),
                display_name=config["display_name"],
                description=config.get("description"),
                is_active=config.get("status", "active") == "active",
                meta_data_schema={kind: config.get("meta_data_schema")}
                if config.get("meta_data_schema")
                else None,
            )
            db.add(mp)
            db.flush()
            stats["provider_created"] = 1
        else:
            stats["provider_skipped"] = 1

        for model_spec in config.get("models") or []:
            model_name = model_spec.get("name") or "default"
            existing = (
                db.query(Model)
                .filter(Model.provider_id == mp.id, Model.name == model_name)
                .one_or_none()
            )
            if existing is not None:
                stats["models_skipped"] += 1
                continue
            db.add(
                Model(
                    provider_id=mp.id,
                    kind=kind,
                    name=model_name,
                    display_name=model_name,
                    is_active=True,
                    meta_data=model_spec.get("meta_data"),
                    meta_data_schema=model_spec.get("meta_data_schema"),
                )
            )
            stats["models_created"] += 1

        db.commit()
        print(
            f"✓ Cerebras: provider "
            f"{'created' if stats['provider_created'] else 'already existed'}; "
            f"models {stats['models_created']} created, {stats['models_skipped']} already existed"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
