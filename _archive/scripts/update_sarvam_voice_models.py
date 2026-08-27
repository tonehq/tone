"""
Update Sarvam voice records with their correct model_id based on the
Sarvam voice-model mapping from the reference doc.

Each Sarvam voice belongs to a specific model (bulbul:v2 or bulbul:v3).
This script looks up the Model.id for each model name under the Sarvam
provider, then updates Voice.model_id for every Sarvam voice accordingly.

Run from project root:
    python scripts/update_sarvam_voice_models.py
"""

import os
import sys

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()

from core.database.session import get_db_script
from core.models.voice import Voice
from core.models.models import Model
from core.models.service_provider import ServiceProvider

# ── Sarvam voice → model mapping ────────────────────────────────────
# Source: docs/Sarvam_Voices_Model_Reference.md

BULBUL_V2_VOICES = {
    "anushka", "manisha", "vidya", "arya", "abhilash", "karun", "hitesh",
}

BULBUL_V3_VOICES = {
    # Male
    "shubh", "aditya", "rahul", "rohan", "amit", "dev", "ratan", "varun",
    "manan", "sumit", "kabir", "aayan", "ashutosh", "advait", "anand",
    "tarun", "sunny", "mani", "gokul", "vijay", "mohit", "rehan", "soham",
    # Female
    "ritu", "priya", "neha", "pooja", "simran", "kavya", "ishita", "shreya",
    "roopa", "amelia", "sophia", "tanya", "shruti", "suhani", "kavitha",
    "rupali",
}


def get_voice_to_model_map():
    """Build voice name (lowercase) → model_name mapping."""
    mapping = {}
    for voice_id in BULBUL_V2_VOICES:
        mapping[voice_id] = "bulbul:v2"
    for voice_id in BULBUL_V3_VOICES:
        mapping[voice_id] = "bulbul:v3"
    return mapping


def main():
    db = get_db_script()
    try:
        # Find the Sarvam service provider
        sarvam_provider = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.name == "sarvam", ServiceProvider.provider_type == "tts")
            .first()
        )
        if not sarvam_provider:
            print("ERROR: Sarvam service provider not found in database.")
            print("       Run 'python dev/seed.py' first.")
            sys.exit(1)

        print(f"Found Sarvam provider: id={sarvam_provider.id}")

        # Load Sarvam models from DB and build name → id lookup
        sarvam_models = (
            db.query(Model)
            .filter(Model.service_provider_id == sarvam_provider.id)
            .all()
        )
        model_name_to_id = {m.name: m.id for m in sarvam_models}
        print(f"Found {len(sarvam_models)} Sarvam models: {model_name_to_id}")

        if not model_name_to_id:
            print("ERROR: No Sarvam models found. Run 'python dev/seed.py' first.")
            sys.exit(1)

        # Build voice → model mapping
        voice_to_model = get_voice_to_model_map()

        # Fetch all Sarvam voices
        sarvam_voices = (
            db.query(Voice)
            .filter(Voice.service_provider_id == sarvam_provider.id)
            .all()
        )
        print(f"Found {len(sarvam_voices)} Sarvam voices in database.\n")

        updated = 0
        skipped = 0
        not_mapped = 0

        for voice in sarvam_voices:
            # Match by voice name (lowercased) since voice_id is like
            # "sarvam-ashutosh-bn-IN" but the mapping uses names like "ashutosh"
            voice_name_key = voice.name.lower() if voice.name else ""
            model_name = voice_to_model.get(voice_name_key)
            if not model_name:
                print(f"  WARNING: No model mapping for voice '{voice.name}' (voice_id: {voice.voice_id}) — skipped")
                not_mapped += 1
                continue

            model_id = model_name_to_id.get(model_name)
            if not model_id:
                print(f"  WARNING: Model '{model_name}' not found in DB for voice '{voice.name}' — skipped")
                skipped += 1
                continue

            if voice.model_id == model_id:
                skipped += 1
                continue

            voice.model_id = model_id
            updated += 1

        db.commit()
        print(f"Done!")
        print(f"  Updated:    {updated}")
        print(f"  Skipped:    {skipped} (already correct)")
        print(f"  Not mapped: {not_mapped}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
