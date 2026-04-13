"""
One-time script to add `model_name` to Rime and Sarvam voice entries
in dev-data.json, so that seed.py can set model_id during seeding.

- Rime: maps voice_id to model (arcana > mistv2 > mist precedence)
- Sarvam: maps voice name (lowercase) to model (bulbul:v2 or bulbul:v3)

Run from project root:
    python scripts/add_model_name_to_dev_data.py
"""

import json
import os

DEV_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "dev", "dev-data.json")

# ── Rime voice_id → model mapping (arcana > mistv2 > mist) ──────────

RIME_MIST_VOICES = {
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

RIME_MISTV2_VOICES = {
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
    "diego", "dolores", "isa", "jose", "lucia", "mateo", "sofia",
    "alois", "juliette", "marguerite", "simone",
    "amalia", "frieda", "karolina", "klaus", "maximilian",
}

RIME_ARCANA_VOICES = {
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
    "aurelio", "celestino", "lark", "luz", "mar", "nova", "seraphina",
    "amarante", "aurelie", "destin", "morel_marianne", "solstice",
    "alfhild", "baldur", "kumara", "liesel", "lorelei", "runa",
    "alzira", "baltasar", "celso", "isadora", "lucia", "sol",
    "batin", "layla", "qadir", "sakina",
    "anaya", "anil", "arya",
    "raiden", "ren", "yukiko",
    "aviva", "ori",
}

# ── Sarvam voice name (lowercase) → model mapping ───────────────────

SARVAM_BULBUL_V2_VOICES = {
    "anushka", "manisha", "vidya", "arya", "abhilash", "karun", "hitesh",
}

SARVAM_BULBUL_V3_VOICES = {
    "shubh", "aditya", "rahul", "rohan", "amit", "dev", "ratan", "varun",
    "manan", "sumit", "kabir", "aayan", "ashutosh", "advait", "anand",
    "tarun", "sunny", "mani", "gokul", "vijay", "mohit", "rehan", "soham",
    "ritu", "priya", "neha", "pooja", "simran", "kavya", "ishita", "shreya",
    "roopa", "amelia", "sophia", "tanya", "shruti", "suhani", "kavitha",
    "rupali",
}


def get_rime_voice_to_model():
    """Build voice_id → model_name. arcana > mistv2 > mist precedence."""
    mapping = {}
    for vid in RIME_MIST_VOICES:
        mapping[vid] = "mist"
    for vid in RIME_MISTV2_VOICES:
        mapping[vid] = "mistv2"
    for vid in RIME_ARCANA_VOICES:
        mapping[vid] = "arcana"
    return mapping


def get_sarvam_voice_to_model():
    """Build voice name (lowercase) → model_name."""
    mapping = {}
    for name in SARVAM_BULBUL_V2_VOICES:
        mapping[name] = "bulbul:v2"
    for name in SARVAM_BULBUL_V3_VOICES:
        mapping[name] = "bulbul:v3"
    return mapping


def main():
    with open(DEV_DATA_PATH, "r") as f:
        data = json.load(f)

    rime_map = get_rime_voice_to_model()
    sarvam_map = get_sarvam_voice_to_model()

    rime_updated = 0
    rime_not_mapped = 0
    sarvam_updated = 0
    sarvam_not_mapped = 0

    for provider in data.get("tts_providers", []):
        provider_name = provider.get("name", "")
        voices = provider.get("voices", [])

        if provider_name == "rime":
            for voice in voices:
                voice_id = voice.get("voice_id", "")
                model_name = rime_map.get(voice_id)
                if model_name:
                    voice["model_name"] = model_name
                    rime_updated += 1
                else:
                    rime_not_mapped += 1
                    print(f"  WARNING: Rime voice '{voice_id}' not in mapping")

        elif provider_name == "sarvam":
            for voice in voices:
                name_key = voice.get("name", "").lower()
                model_name = sarvam_map.get(name_key)
                if model_name:
                    voice["model_name"] = model_name
                    sarvam_updated += 1
                else:
                    sarvam_not_mapped += 1
                    print(f"  WARNING: Sarvam voice '{voice.get('name')}' not in mapping")

    with open(DEV_DATA_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nRime:   {rime_updated} updated, {rime_not_mapped} not mapped")
    print(f"Sarvam: {sarvam_updated} updated, {sarvam_not_mapped} not mapped")
    print("dev-data.json saved.")


if __name__ == "__main__":
    main()
