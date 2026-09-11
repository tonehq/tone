"""
Sync retired-model removals / replacements from dev-data.json into the running DB.

Run from project root:  python dev/sync_deprecated_model_changes.py

Mirrors the model changes already applied to dev/dev-data.json (see
docs/deprecated-model-params-cleanup.md §2b). Two kinds of change:

  RENAMES  — the retired model was replaced by a new id. We UPDATE the existing
             row IN PLACE (name + meta_data + meta_data_schema + base_url +
             display_name pulled from dev-data.json). Doing it in place keeps the
             row's UUID, so all attached model_voices / model_languages follow
             automatically — critical for Rime (arcana -> coda) which has 273
             voices linked by model_id. (A delete+insert would cascade-drop them.)

  DELETES  — the retired model has no replacement id of its own (its replacement
             already exists as another row). We DELETE the row; ON DELETE CASCADE
             removes its voices/languages.

IDEMPOTENT: if a rename's old row is gone but the new row already exists, it is
treated as already-applied and skipped. Re-running is safe. No agent settings are
touched (removed model rows just become unselectable; the runtime already filters).
"""
import os
import sys
import json

if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

# ── Hardcode the target database URL here (leave "" and pass via env if preferred) ──
DATABASE_URL = ""  # e.g. "postgresql+psycopg2://user:pass@host:5432/dbname"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ── What changed (must match dev/dev-data.json) ────────────────────────────────
# Renames: (provider_slug, old_name, new_name) — new spec is read from dev-data.json
RENAMES = [
    ("anthropic", "claude-opus-4-1", "claude-opus-4-8"),
    ("soniox", "stt-rt-v4", "stt-rt-v5"),
    ("soniox", "stt-async-v4", "stt-async-v5"),
    ("rime", "arcana", "coda"),
]

# Deletes: (provider_slug, model_name)
DELETES = [
    ("soniox", "stt-rt-v3"),
    ("soniox", "stt-async-v3"),
    ("fish", "speech-1.5"),
    ("fish", "speech-1.6"),
]


def load_seed_specs():
    """Return {(provider_slug, model_name): model_spec} from dev-data.json."""
    path = os.path.join(os.path.dirname(__file__), "dev-data.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    specs = {}
    for cat in ("llm_providers", "stt_providers", "tts_providers"):
        for p in data.get(cat, []):
            for m in p.get("models", []):
                specs[(p["name"], m["name"])] = m
    return specs


def run(db):
    from core.models.model import Model
    from core.models.model_provider import ModelProvider

    provider_map = {mp.provider_id: mp.id for mp in db.query(ModelProvider).all()}
    model_map = {(m.provider_id, m.name): m for m in db.query(Model).all()}
    seed_specs = load_seed_specs()

    renamed = 0
    deleted = 0
    skipped = 0

    print("== Renames (in place; voices/languages preserved) ==")
    for slug, old_name, new_name in RENAMES:
        puid = provider_map.get(slug)
        if not puid:
            print(f"  PROVIDER NOT FOUND: {slug} (skipped)")
            skipped += 1
            continue
        old_row = model_map.get((puid, old_name))
        new_row = model_map.get((puid, new_name))
        if not old_row:
            if new_row:
                print(f"  OK (already renamed): {slug}/{old_name} -> {new_name}")
            else:
                print(f"  NOT FOUND: {slug}/{old_name} (skipped)")
                skipped += 1
            continue
        if new_row:
            print(f"  CONFLICT: {slug}/{new_name} already exists; deleting stale {old_name} instead")
            db.delete(old_row)
            deleted += 1
            continue
        spec = seed_specs.get((slug, new_name), {})
        old_row.name = new_name
        old_row.display_name = new_name
        if spec.get("meta_data") is not None:
            old_row.meta_data = spec["meta_data"]
        if spec.get("meta_data_schema") is not None:
            old_row.meta_data_schema = spec["meta_data_schema"]
        if "base_url" in spec:
            old_row.base_url = spec["base_url"]
        renamed += 1
        print(f"  RENAMED: {slug}/{old_name} -> {new_name} (voices kept via model_id {old_row.id})")

    print("\n== Deletes (cascade voices/languages) ==")
    for slug, name in DELETES:
        puid = provider_map.get(slug)
        row = model_map.get((puid, name)) if puid else None
        if not row:
            print(f"  OK (already gone / not found): {slug}/{name}")
            continue
        db.delete(row)
        deleted += 1
        print(f"  DELETED: {slug}/{name}")

    db.commit()
    return renamed, deleted, skipped


def main():
    if not DATABASE_URL:
        print("ERROR: Set DATABASE_URL at the top of this script before running.")
        sys.exit(1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        host = DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "local"
        print(f"Connecting to: {host}...\n")
        r, d, s = run(db)
        print(f"\nDone: {r} renamed, {d} deleted, {s} skipped.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
