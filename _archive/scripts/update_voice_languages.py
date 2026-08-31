"""
Update the language_list JSON column on Voice records.

- ElevenLabs, MiniMax, OpenAI: ALL voices get the full language list
  (every voice supports every language for these providers).
- All other providers: language_list is set to [voice.language]
  (single-element list from the existing language column).

Language lists sourced from:
  - docs/ElevenLabs_Languages_Reference.md (76 languages — eleven_v3 superset)
  - docs/MiniMax_Languages_Reference.md (40 languages)
  - docs/OpenAI_TTS_Languages_Reference.md (57 languages)

Run from project root:
    python scripts/update_voice_languages.py
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
from core.models.service_provider import ServiceProvider

# ── Language lists per provider ──────────────────────────────────────

ELEVENLABS_LANGUAGES = [
    "Afrikaans", "Arabic", "Armenian", "Assamese", "Azerbaijani",
    "Belarusian", "Bengali", "Bosnian", "Bulgarian", "Catalan",
    "Cebuano", "Chichewa", "Croatian", "Czech", "Danish",
    "Dutch", "English", "Estonian", "Filipino", "Finnish",
    "French", "Galician", "Georgian", "German", "Greek",
    "Gujarati", "Hausa", "Hebrew", "Hindi", "Hungarian",
    "Icelandic", "Indonesian", "Irish", "Italian", "Japanese",
    "Javanese", "Kannada", "Kazakh", "Kirghiz", "Korean",
    "Latvian", "Lingala", "Lithuanian", "Luxembourgish", "Macedonian",
    "Malay", "Malayalam", "Mandarin Chinese", "Marathi", "Nepali",
    "Norwegian", "Pashto", "Persian", "Polish", "Portuguese",
    "Punjabi", "Romanian", "Russian", "Serbian", "Sindhi",
    "Slovak", "Slovenian", "Somali", "Spanish", "Swahili",
    "Swedish", "Tamil", "Telugu", "Thai", "Turkish",
    "Ukrainian", "Urdu", "Vietnamese", "Welsh",
]

MINIMAX_LANGUAGES = [
    "Afrikaans", "Arabic", "Bulgarian", "Catalan",
    "Chinese (Mandarin)", "Chinese (Cantonese)", "Croatian", "Czech",
    "Danish", "Dutch", "English", "Filipino",
    "Finnish", "French", "German", "Greek",
    "Hebrew", "Hindi", "Hungarian", "Indonesian",
    "Italian", "Japanese", "Korean", "Malay",
    "Norwegian (Bokmal)", "Nynorsk", "Persian", "Polish",
    "Portuguese", "Romanian", "Russian", "Slovak",
    "Slovenian", "Spanish", "Swedish", "Tamil",
    "Thai", "Turkish", "Ukrainian", "Vietnamese",
]

OPENAI_LANGUAGES = [
    "Afrikaans", "Arabic", "Armenian", "Azerbaijani", "Belarusian",
    "Bosnian", "Bulgarian", "Catalan", "Chinese", "Croatian",
    "Czech", "Danish", "Dutch", "English", "Estonian",
    "Finnish", "French", "Galician", "German", "Greek",
    "Hebrew", "Hindi", "Hungarian", "Icelandic", "Indonesian",
    "Italian", "Japanese", "Kannada", "Kazakh", "Korean",
    "Latvian", "Lithuanian", "Macedonian", "Malay", "Maori",
    "Marathi", "Nepali", "Norwegian", "Persian", "Polish",
    "Portuguese", "Romanian", "Russian", "Serbian", "Slovak",
    "Slovenian", "Spanish", "Swahili", "Swedish", "Tagalog",
    "Tamil", "Thai", "Turkish", "Ukrainian", "Urdu",
    "Vietnamese", "Welsh",
]

PROVIDER_LANGUAGES = {
    "elevenlabs": ELEVENLABS_LANGUAGES,
    "minimax": MINIMAX_LANGUAGES,
    "openai": OPENAI_LANGUAGES,
}


def main():
    db = get_db_script()
    try:
        for provider_name, languages in PROVIDER_LANGUAGES.items():
            provider = (
                db.query(ServiceProvider)
                .filter(
                    ServiceProvider.name == provider_name,
                    ServiceProvider.provider_type == "tts",
                )
                .first()
            )
            if not provider:
                print(f"WARNING: Provider '{provider_name}' not found — skipped")
                continue

            voices = (
                db.query(Voice)
                .filter(Voice.service_provider_id == provider.id)
                .all()
            )
            print(f"{provider_name}: {len(voices)} voices, {len(languages)} languages")

            updated = 0
            skipped = 0
            for voice in voices:
                if voice.language_list == languages:
                    skipped += 1
                    continue
                voice.language_list = languages
                updated += 1

            print(f"  Updated: {updated}, Skipped: {skipped} (already correct)")

        db.commit()
        print("\n--- Multi-language providers done ---\n")

        # ── All other providers: use existing language column ────────
        multi_lang_names = set(PROVIDER_LANGUAGES.keys())
        other_providers = (
            db.query(ServiceProvider)
            .filter(
                ServiceProvider.provider_type == "tts",
                ~ServiceProvider.name.in_(multi_lang_names),
            )
            .all()
        )

        for provider in other_providers:
            voices = (
                db.query(Voice)
                .filter(Voice.service_provider_id == provider.id)
                .all()
            )
            if not voices:
                continue

            updated = 0
            skipped = 0
            for voice in voices:
                target = [voice.language] if voice.language else []
                if voice.language_list == target:
                    skipped += 1
                    continue
                voice.language_list = target
                updated += 1

            print(f"{provider.name}: {len(voices)} voices")
            print(f"  Updated: {updated}, Skipped: {skipped} (already correct)")

        db.commit()
        print("\nDone!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
