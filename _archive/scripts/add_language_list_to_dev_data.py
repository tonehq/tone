"""
One-time script to add `language_list` to every voice entry in dev-data.json.

- ElevenLabs, MiniMax, OpenAI: full multi-language list
- All other TTS providers: [voice["language"]] (single-element list)

Keeps the existing `language` key unchanged.

Run from project root:
    python scripts/add_language_list_to_dev_data.py
"""

import json
import os

DEV_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "dev", "dev-data.json")

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
    with open(DEV_DATA_PATH, "r") as f:
        data = json.load(f)

    total_updated = 0

    for provider in data.get("tts_providers", []):
        provider_name = provider.get("name", "")
        voices = provider.get("voices", [])

        if not voices:
            continue

        full_lang_list = PROVIDER_LANGUAGES.get(provider_name)

        for voice in voices:
            if full_lang_list:
                voice["language_list"] = full_lang_list
            else:
                lang = voice.get("language", "")
                voice["language_list"] = [lang] if lang else []
            total_updated += 1

        print(f"{provider_name}: {len(voices)} voices updated")

    with open(DEV_DATA_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nTotal voices updated: {total_updated}")
    print("dev-data.json saved.")


if __name__ == "__main__":
    main()
