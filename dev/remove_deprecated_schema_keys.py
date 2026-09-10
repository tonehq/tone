"""
Remove deprecated parameter keys from meta_data_schema in the running DB.

Run from project root:  python dev/remove_deprecated_schema_keys.py

This mirrors the key removals already applied to dev/dev-data.json (see
docs/deprecated-model-params-cleanup.md §2). It strips the named fields from:
  - models.meta_data_schema            (per-model schema)
  - model_providers.meta_data_schema   (per-kind provider fallback schema)

The operation is TARGETED and IDEMPOTENT: it only removes the named keys from
the named targets, and re-running it is a no-op. It does NOT touch any other
column, model, or agent settings. (Existing agent settings are filtered against
the model schema at call time, so removed keys are simply ignored — no data
migration is required.)
"""
import os
import sys

if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

# ── Hardcode the target database URL here (leave "" and pass via env if preferred) ──
DATABASE_URL = ""  # e.g. "postgresql+psycopg2://user:pass@host:5432/dbname"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ── What was removed (must match dev/dev-data.json) ─────────────────────────────
# Per-model removals: (provider_slug, model_name, {keys_to_remove})
MODEL_KEY_REMOVALS = [
    ("openai_realtime", "gpt-4o-realtime-preview", {"temperature"}),
    ("openai_realtime", "gpt-4o-mini-realtime-preview", {"temperature"}),
    ("openai_realtime", "gpt-realtime", {"temperature"}),
    ("anthropic", "claude-opus-4-6", {"thinking_budget_tokens"}),
    ("anthropic", "claude-opus-4-7", {"thinking_budget_tokens"}),
    ("anthropic", "claude-opus-4-8", {"thinking_budget_tokens"}),  # renamed from 4-1; keep clean
    ("azure", "microsoft/MAI-DS-R1", {"temperature", "top_p", "frequency_penalty", "presence_penalty"}),
    ("azure", "DragonHDLatestNeural", {"rate", "volume", "style"}),
    ("azure", "DragonHDOmniLatestNeural", {"rate", "volume", "style"}),
    ("azure", "DragonHD Flash", {"rate", "volume", "style"}),
    ("azure", "MultiTalker DragonHDLatestNeural", {"rate", "volume", "style"}),
]

# Per-provider (fallback) removals: (provider_slug, kind, {keys_to_remove})
PROVIDER_KEY_REMOVALS = [
    ("openai_realtime", "llm", {"temperature"}),
]


def _strip(schema, keys):
    """Return (new_schema, removed_names). schema is a list of field dicts."""
    if not isinstance(schema, list):
        return schema, []
    removed = [f.get("name") for f in schema if isinstance(f, dict) and f.get("name") in keys]
    new = [f for f in schema if not (isinstance(f, dict) and f.get("name") in keys)]
    return new, removed


def run(db):
    from core.models.model import Model
    from core.models.model_provider import ModelProvider

    # provider slug -> UUID
    provider_map = {mp.provider_id: mp.id for mp in db.query(ModelProvider).all()}
    # (provider_uuid, model_name) -> Model row
    model_map = {(m.provider_id, m.name): m for m in db.query(Model).all()}

    model_updates = 0
    provider_updates = 0
    not_found = 0

    print("== Model-level key removals ==")
    for slug, model_name, keys in MODEL_KEY_REMOVALS:
        puid = provider_map.get(slug)
        row = model_map.get((puid, model_name)) if puid else None
        if not row:
            print(f"  NOT FOUND: {slug}/{model_name} (skipped)")
            not_found += 1
            continue
        new_schema, removed = _strip(row.meta_data_schema, keys)
        if removed:
            row.meta_data_schema = new_schema
            model_updates += 1
            print(f"  UPDATED: {slug}/{model_name} removed {removed} -> {[f['name'] for f in new_schema]}")
        else:
            print(f"  OK (already clean): {slug}/{model_name}")

    print("\n== Provider-level (fallback) key removals ==")
    for slug, kind, keys in PROVIDER_KEY_REMOVALS:
        mp = db.query(ModelProvider).filter(ModelProvider.provider_id == slug).first()
        if not mp:
            print(f"  NOT FOUND: {slug} (skipped)")
            not_found += 1
            continue
        schema_dict = mp.meta_data_schema or {}
        if not isinstance(schema_dict, dict) or kind not in schema_dict:
            print(f"  OK (no {kind} schema): {slug}")
            continue
        new_schema, removed = _strip(schema_dict.get(kind), keys)
        if removed:
            # reassign a fresh dict so SQLAlchemy detects the JSONB change
            updated = dict(schema_dict)
            updated[kind] = new_schema
            mp.meta_data_schema = updated
            provider_updates += 1
            print(f"  UPDATED: {slug} [{kind}] removed {removed} -> {[f['name'] for f in new_schema]}")
        else:
            print(f"  OK (already clean): {slug} [{kind}]")

    db.commit()
    return model_updates, provider_updates, not_found


def main():
    if not DATABASE_URL:
        print("ERROR: Set DATABASE_URL at the top of this script before running.")
        sys.exit(1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        host = DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "local"
        print(f"Connecting to: {host}...\n")
        m, p, nf = run(db)
        print(f"\nDone: {m} model rows updated, {p} provider rows updated, {nf} targets not found.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
