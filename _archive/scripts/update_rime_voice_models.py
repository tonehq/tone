"""
Update Rime voice records with their correct model_id based on the
Rime voice-model-language mapping from the reference doc.

Each Rime voice belongs to a specific model (mist, mistv2, arcana).
This script looks up the Model.id for each model name under the Rime
provider, then updates Voice.model_id for every Rime voice accordingly.

Run from project root:
    python scripts/update_rime_voice_models.py
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

# ── Rime voice → model mapping ──────────────────────────────────────
# Source: docs/Rime_Voices_Model_Language_Reference.md

MIST_VOICES = {
    "abbie", "alexis", "allison", "ally", "alona", "alpine", "amber", "ana",
    "antoine", "armon", "bayou", "benjamin", "blaze", "blossom", "boulder",
    "breeze", "brenda", "brittany", "brook", "carol", "cedar", "colin",
    "courtney", "cove", "creek", "dew", "elena", "elliot", "ember", "eva",
    "falcon", "fjord", "flower", "frank", "gabriela", "geoff", "gerald",
    "glacier", "granite", "grove", "gulch", "gypsum", "hank", "hawk", "helen",
    "hera", "iris", "ironwood", "jen", "joe", "joy", "juan", "jungle",
    "kendra", "kendrick", "kenneth", "kevin", "kris", "lagoon", "linda",
    "loquat", "lotus", "madison", "marge", "marina", "marissa", "marsh",
    "marta", "maya", "mesa", "moon", "moraine", "nicholas", "nyles", "peak",
    "pearl", "petal", "phil", "rain", "rainforest", "reba", "rex", "rick",
    "ritu", "river", "rob", "rodney", "rohan", "rosco", "samantha", "sandy",
    "selena", "seth", "sharon", "spore", "stan", "steppe", "stone", "storm",
    "stream", "summit", "talon", "tamra", "tanya", "thunder", "tibur", "tj",
    "tundra", "tyler", "violet", "viv", "wildflower", "willow", "wolf",
    "yadira", "zest", "zion",
}

MISTV2_VOICES = {
    # English
    "abbie", "allison", "ally", "alona", "alpine", "amber", "ana", "antoine",
    "armon", "astra", "bayou", "blaze", "blossom", "boulder", "breeze",
    "brenda", "brittany", "brook", "carol", "cedar", "colin", "courtney",
    "cove", "cove_extra", "creek", "dew", "elena", "elliot", "ember",
    "eucalyptus", "eva", "falcon", "fjord", "flower", "geoff", "gerald",
    "glacier", "granite", "grove", "gulch", "gypsum", "hank", "hawk", "helen",
    "hera", "iris", "ironwood", "jen", "joe", "jose", "joy", "juan", "jungle",
    "karst", "kendra", "kendrick", "kenneth", "kevin", "kris", "lagoon",
    "linda", "loquat", "lotus", "madison", "marge", "mari", "marina",
    "marissa", "marlu", "marsh", "marta", "maya", "mesa", "mesa_extra",
    "moon", "moraine", "nicholas", "nyles", "pablo", "peak", "pearl", "petal",
    "phil", "rain", "rainforest", "reba", "rex", "rick", "ritu", "river",
    "rob", "rodney", "rohan", "rosco", "runton", "samantha", "sandy", "selena",
    "seth", "sharon", "spore", "stan", "steppe", "stone", "storm", "stream",
    "summit", "talon", "tamra", "tanya", "thunder", "tibur", "tj", "tundra",
    "tyler", "violet", "viv", "wildflower", "willow", "wolf", "yadira",
    "zest", "zion",
    # Spanish
    "diego", "dolores", "isa", "jose", "lucia", "mateo", "sofia",
    # French
    "alois", "juliette", "marguerite", "simone",
    # German
    "amalia", "frieda", "karolina", "klaus", "maximilian",
}

ARCANA_VOICES = {
    # English
    "ahmed_mohamed", "albion", "andersen_johan", "anderson_emily",
    "anderson_jake", "anderson_james", "anderson_kevin", "andromeda", "arcade",
    "astra", "atrium", "bauer_felix", "bennett_emily", "bennett_ryan",
    "biondi_paul", "bond", "brooks_jordan", "brown_alex", "brown_joshua",
    "brown_madison", "brown_matthew", "brown_steven", "bruno_katie",
    "carter_colin", "celeste", "chatterjee_rini", "chen_david", "chen_mei",
    "clark_tyler", "cohen_emily", "cohen_jared", "collins_emily",
    "cooper_logan", "cupola", "das_sourav", "davies_james", "dela_cristina",
    "diallo_amara", "dubois_emma", "duncan_colin", "duval_pierre", "eliphas",
    "estelle", "esther", "eucalyptus", "evans_jason", "fern",
    "fernandez_carlos", "goldberg_ryan", "gomez_daniela", "gomez_diego",
    "gomez_isabel", "gomez_isabella", "gomez_javon", "gonzalez_maya",
    "gonzalez_michael", "gonzalez_ryan", "grayson_avery", "hanson_ryan",
    "harris_luke", "harris_lynette", "harrison_brianna", "harrison_joey",
    "harrison_mary", "hassan_omar", "henderson_brittney", "hernandez_juanita",
    "holliday_jewel", "iyer_arun", "jensen_mikkel", "johnny_jackson",
    "johnson_angela", "johnson_asha", "johnson_avery", "johnson_brianna",
    "johnson_cynthia", "johnson_elijah", "johnson_james", "johnson_joshua",
    "johnson_latisha", "johnson_lisa", "johnson_madison", "johnson_malachi",
    "johnson_marcel", "johnson_mary", "johnson_matthew", "johnson_melissa",
    "johnson_monique", "johnson_nia", "johnson_tasha", "johnson_tia",
    "johnson_walter", "kelly_aoife", "kelly_jennifer", "kelly_john",
    "kelly_maureen", "khan_fatima", "khan_umar", "kim_ashley", "kim_daniel",
    "kim_sunny", "kima", "lee_sarah", "levi_david", "levine_emily",
    "levine_joshua", "levy_hannah", "li_xiao", "lintel", "luna", "lyra",
    "maguire_jason", "malik_ahmad", "marinelli_giulia", "marlu",
    "martinez_amber", "martinez_ana", "martinez_dylan", "martinez_jaime",
    "martinez_leticia", "martinez_rosa", "martinez_ryan", "masonry",
    "mbunda_james", "mccarthy_james", "mccarthy_teresa", "mcdowell_peter",
    "mckinley_robert", "mendoza_alonzo", "mendoza_jesus", "mendoza_luz",
    "merritt_jimmy", "miller_cameron", "miller_judy", "miller_kelsey",
    "miller_lisa", "miller_logan", "miyamoto_akari", "montgomery_elise",
    "montgomery_emily", "morgan_brianna", "morgan_charles", "morris_colin",
    "morris_james", "morris_leticia", "morris_melvin", "morton_daine", "moss",
    "moyo_david", "murphy_colin", "murphy_emily", "murphy_grace",
    "murphy_hannah", "murphy_liam", "murphy_nolan", "neal_colin",
    "novak_emily", "nowak_joanna", "nowak_michal", "oculus", "olsson_erik",
    "orion", "parapet", "park_minseo", "park_sumin", "patel_amit",
    "patel_asha", "pham_daniel", "pilaster", "pola", "ramirez_maya",
    "ramos_raul", "reddy_arjun", "reddy_sunil", "ricci_giulia",
    "ricci_lorenzo", "rodrigues_miguel", "rodriguez_carla", "rodriguez_carlos",
    "rodriguez_eduardo", "rodriguez_isabela", "rodriguez_miguel",
    "rossi_matteo", "santos_angelica", "schmidt_joshua", "schmidt_julia",
    "schmidt_sophie", "schneider_eric", "schneider_jack", "sharma_amit",
    "silva_ana", "singh_anjali", "sirius", "smith_heather", "smith_lisa",
    "smith_michael", "smith_mike", "stucco", "tauro", "thalassa",
    "thomas_sarah", "thompson_kevin", "torres_miguel", "tran_david",
    "tran_jessica", "tran_tu", "transom", "truss", "tupou_leilani", "ursa",
    "vashti", "vespera", "walnut", "wang_mei", "watson_emily", "williams_anna",
    "williams_brian", "williams_darnell", "williams_jennifer",
    "williams_jordan", "williams_ryan", "williams_terence",
    "williams_tiffany", "wilson_emma", "wong_kenny", "wright_cooper",
    "wright_jason", "wright_julianne", "wright_michael", "zhang_mei",
    # Spanish
    "aurelio", "celestino", "lark", "luz", "mar", "nova", "seraphina",
    # French
    "amarante", "aurelie", "destin", "morel_marianne", "solstice",
    # German
    "alfhild", "baldur", "kumara", "liesel", "lorelei", "runa",
    # Portuguese
    "alzira", "baltasar", "celso", "isadora", "lucia", "sol",
    # Arabic
    "batin", "layla", "qadir", "sakina",
    # Hindi
    "anaya", "anil", "arya",
    # Japanese
    "raiden", "ren", "yukiko",
    # Hebrew
    "aviva", "ori",
}

# Voices that exist in multiple models — map to the newest (arcana > mistv2 > mist).
# The seed script has a unique constraint on (service_provider_id, voice_id),
# so each voice_id appears only once in the DB. We assign the most capable model.
# Order of precedence: arcana first, then mistv2, then mist.


def get_voice_to_model_map():
    """Build voice_id → model_name mapping. Later models override earlier ones."""
    mapping = {}
    for voice_id in MIST_VOICES:
        mapping[voice_id] = "mist"
    for voice_id in MISTV2_VOICES:
        mapping[voice_id] = "mistv2"
    for voice_id in ARCANA_VOICES:
        mapping[voice_id] = "arcana"
    return mapping


def main():
    db = get_db_script()
    try:
        # Find the Rime service provider
        rime_provider = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.name == "rime")
            .first()
        )
        if not rime_provider:
            print("ERROR: Rime service provider not found in database.")
            print("       Run 'python dev/seed.py' first.")
            sys.exit(1)

        print(f"Found Rime provider: id={rime_provider.id}")

        # Load Rime models from DB and build name → id lookup
        rime_models = (
            db.query(Model)
            .filter(Model.service_provider_id == rime_provider.id)
            .all()
        )
        model_name_to_id = {m.name: m.id for m in rime_models}
        print(f"Found {len(rime_models)} Rime models: {model_name_to_id}")

        if not model_name_to_id:
            print("ERROR: No Rime models found. Run 'python dev/seed.py' first.")
            sys.exit(1)

        # Build voice → model mapping
        voice_to_model = get_voice_to_model_map()

        # Fetch all Rime voices
        rime_voices = (
            db.query(Voice)
            .filter(Voice.service_provider_id == rime_provider.id)
            .all()
        )
        print(f"Found {len(rime_voices)} Rime voices in database.\n")

        updated = 0
        skipped = 0
        not_mapped = 0

        for voice in rime_voices:
            model_name = voice_to_model.get(voice.voice_id)
            if not model_name:
                print(f"  WARNING: No model mapping for voice '{voice.voice_id}' — skipped")
                not_mapped += 1
                continue

            model_id = model_name_to_id.get(model_name)
            if not model_id:
                print(f"  WARNING: Model '{model_name}' not found in DB for voice '{voice.voice_id}' — skipped")
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
