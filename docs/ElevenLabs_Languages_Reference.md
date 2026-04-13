# ElevenLabs TTS — Languages & Voice Reference

> **Last updated:** 2026-03-27
> **Source:** Official ElevenLabs documentation

---

## Key Rules

- **All voices work with all models** — no voice-model restriction
- **All voices can speak all languages** the selected model supports — no voice-language restriction
- **Language support depends on the model** — pick model based on language needed
- For best quality, choose a voice whose accent matches your target language

---

## Language Support by Model

### eleven_v3 — 70+ languages (ISO 639-3 codes)

> Newest model. Most expressive. Uses **3-letter** language codes.

| Language | Code | Language | Code |
|----------|------|----------|------|
| Afrikaans | `afr` | Latvian | `lav` |
| Arabic | `ara` | Lingala | `lin` |
| Armenian | `hye` | Lithuanian | `lit` |
| Assamese | `asm` | Luxembourgish | `ltz` |
| Azerbaijani | `aze` | Macedonian | `mkd` |
| Belarusian | `bel` | Malay | `msa` |
| Bengali | `ben` | Malayalam | `mal` |
| Bosnian | `bos` | Mandarin Chinese | `cmn` |
| Bulgarian | `bul` | Marathi | `mar` |
| Catalan | `cat` | Nepali | `nep` |
| Cebuano | `ceb` | Norwegian | `nor` |
| Chichewa | `nya` | Pashto | `pus` |
| Croatian | `hrv` | Persian | `fas` |
| Czech | `ces` | Polish | `pol` |
| Danish | `dan` | Portuguese | `por` |
| Dutch | `nld` | Punjabi | `pan` |
| English | `eng` | Romanian | `ron` |
| Estonian | `est` | Russian | `rus` |
| Filipino | `fil` | Serbian | `srp` |
| Finnish | `fin` | Sindhi | `snd` |
| French | `fra` | Slovak | `slk` |
| Galician | `glg` | Slovenian | `slv` |
| Georgian | `kat` | Somali | `som` |
| German | `deu` | Spanish | `spa` |
| Greek | `ell` | Swahili | `swa` |
| Gujarati | `guj` | Swedish | `swe` |
| Hausa | `hau` | Tamil | `tam` |
| Hebrew | `heb` | Telugu | `tel` |
| Hindi | `hin` | Thai | `tha` |
| Hungarian | `hun` | Turkish | `tur` |
| Icelandic | `isl` | Ukrainian | `ukr` |
| Indonesian | `ind` | Urdu | `urd` |
| Irish | `gle` | Vietnamese | `vie` |
| Italian | `ita` | Welsh | `cym` |
| Japanese | `jpn` | Javanese | `jav` |
| Kannada | `kan` | Kazakh | `kaz` |
| Kirghiz | `kir` | Korean | `kor` |

---

### eleven_flash_v2_5 / eleven_turbo_v2_5 — 32 languages (ISO 639-1 codes)

> Low latency. Uses **2-letter** language codes. Accepts explicit `language_code` param.

| Language | Code | Language | Code |
|----------|------|----------|------|
| Arabic | `ar` | Indonesian | `id` |
| Bulgarian | `bg` | Italian | `it` |
| Chinese | `zh` | Japanese | `ja` |
| Croatian | `hr` | Korean | `ko` |
| Czech | `cs` | Malay | `ms` |
| Danish | `da` | Norwegian | `no` |
| Dutch | `nl` | Polish | `pl` |
| English | `en` | Portuguese | `pt` |
| Filipino | `fil` | Romanian | `ro` |
| Finnish | `fi` | Russian | `ru` |
| French | `fr` | Slovak | `sk` |
| German | `de` | Spanish | `es` |
| Greek | `el` | Swedish | `sv` |
| Hindi | `hi` | Tamil | `ta` |
| Hungarian | `hu` | Turkish | `tr` |
| Ukrainian | `uk` | Vietnamese | `vi` |

---

### eleven_multilingual_v2 — 29 languages (auto-detected)

> Does **NOT** accept `language_code` param. Auto-detects language from input text.

Same as flash_v2_5 list **minus** Hungarian (`hu`), Norwegian (`no`), Vietnamese (`vi`).

---

## Important: Language Code Format Differs by Model

| Model | Code format | Example for French | Accepts `language_code` param? |
|-------|-------------|-------------------|-------------------------------|
| `eleven_v3` | ISO 639-3 (3-letter) | `fra` | Yes |
| `eleven_flash_v2_5` | ISO 639-1 (2-letter) | `fr` | Yes |
| `eleven_turbo_v2_5` | ISO 639-1 (2-letter) | `fr` | Yes |
| `eleven_multilingual_v2` | N/A | N/A | No (auto-detects) |

---

## Voice + Language Behavior

- Any voice can speak any language the model supports
- Voices are **not** locked to a language
- For best quality, pick a voice whose native accent matches the target language
- ElevenLabs has 10,000+ voices in their library — many are optimized for specific languages
- Cloned voices preserve speaker characteristics across languages
