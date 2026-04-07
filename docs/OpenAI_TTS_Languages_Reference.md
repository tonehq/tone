# OpenAI TTS — Languages Reference

> **Last updated:** 2026-03-27
> **Source:** Official OpenAI documentation

---

## Key Rules

- **All 13 voices work across all supported languages** — no voice-language restriction
- **All 3 models support the same 57 languages** — no language-model dependency
- **No explicit `language` parameter** on the speech endpoint — model auto-detects from input text
- Voices are optimized for English; quality may vary for other languages
- `gpt-4o-mini-tts` supports `instructions` param to hint at accent/language behavior

---

## Voices by Model

| Model | Voices |
|-------|--------|
| `tts-1` | alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer (9) |
| `tts-1-hd` | alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer (9) |
| `gpt-4o-mini-tts` | all 9 above + ballad, verse, marin, cedar (13) |

---

## Complete Language List — 57 Languages

| # | Language | ISO 639-1 Code |
|---|----------|----------------|
| 1 | Afrikaans | `af` |
| 2 | Arabic | `ar` |
| 3 | Armenian | `hy` |
| 4 | Azerbaijani | `az` |
| 5 | Belarusian | `be` |
| 6 | Bosnian | `bs` |
| 7 | Bulgarian | `bg` |
| 8 | Catalan | `ca` |
| 9 | Chinese | `zh` |
| 10 | Croatian | `hr` |
| 11 | Czech | `cs` |
| 12 | Danish | `da` |
| 13 | Dutch | `nl` |
| 14 | English | `en` |
| 15 | Estonian | `et` |
| 16 | Finnish | `fi` |
| 17 | French | `fr` |
| 18 | Galician | `gl` |
| 19 | German | `de` |
| 20 | Greek | `el` |
| 21 | Hebrew | `he` |
| 22 | Hindi | `hi` |
| 23 | Hungarian | `hu` |
| 24 | Icelandic | `is` |
| 25 | Indonesian | `id` |
| 26 | Italian | `it` |
| 27 | Japanese | `ja` |
| 28 | Kannada | `kn` |
| 29 | Kazakh | `kk` |
| 30 | Korean | `ko` |
| 31 | Latvian | `lv` |
| 32 | Lithuanian | `lt` |
| 33 | Macedonian | `mk` |
| 34 | Malay | `ms` |
| 35 | Maori | `mi` |
| 36 | Marathi | `mr` |
| 37 | Nepali | `ne` |
| 38 | Norwegian | `no` |
| 39 | Persian | `fa` |
| 40 | Polish | `pl` |
| 41 | Portuguese | `pt` |
| 42 | Romanian | `ro` |
| 43 | Russian | `ru` |
| 44 | Serbian | `sr` |
| 45 | Slovak | `sk` |
| 46 | Slovenian | `sl` |
| 47 | Spanish | `es` |
| 48 | Swahili | `sw` |
| 49 | Swedish | `sv` |
| 50 | Tagalog | `tl` |
| 51 | Tamil | `ta` |
| 52 | Thai | `th` |
| 53 | Turkish | `tr` |
| 54 | Ukrainian | `uk` |
| 55 | Urdu | `ur` |
| 56 | Vietnamese | `vi` |
| 57 | Welsh | `cy` |

---

## Notes

- Language is auto-detected from input text — no need to pass a language code
- For `gpt-4o-mini-tts`, you can use `instructions` to guide accent (e.g., "Speak in French with a Parisian accent")
- Additional Whisper languages beyond these 57 may work but are not officially supported for TTS
