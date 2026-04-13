# MiniMax TTS — Languages Reference

> **Last updated:** 2026-03-27
> **Source:** Official MiniMax documentation

---

## Key Rules

- **All 332 voices work with all models** — no voice-model restriction
- **All voices can speak all languages** the selected model supports
- **Language support depends on model** — speech-2.6+ has full 40 language coverage

---

## Language Support by Model

| Languages | speech-2.8 (hd/turbo) | speech-2.6 (hd/turbo) | speech-02 (hd/turbo) |
|-----------|-----------------------|-----------------------|----------------------|
| 40 languages | Yes | Yes | No (37 — missing Filipino, Persian, Tamil) |

---

## Complete Language List — 40 Languages

> API uses English-language strings (not ISO codes) via the `language_boost` parameter.

| # | Language | API Value |
|---|----------|-----------|
| 1 | Afrikaans | `Afrikaans` |
| 2 | Arabic | `Arabic` |
| 3 | Bulgarian | `Bulgarian` |
| 4 | Catalan | `Catalan` |
| 5 | Chinese (Mandarin) | `Chinese` |
| 6 | Chinese (Cantonese) | `Chinese,Yue` |
| 7 | Croatian | `Croatian` |
| 8 | Czech | `Czech` |
| 9 | Danish | `Danish` |
| 10 | Dutch | `Dutch` |
| 11 | English | `English` |
| 12 | Filipino | `Filipino` |
| 13 | Finnish | `Finnish` |
| 14 | French | `French` |
| 15 | German | `German` |
| 16 | Greek | `Greek` |
| 17 | Hebrew | `Hebrew` |
| 18 | Hindi | `Hindi` |
| 19 | Hungarian | `Hungarian` |
| 20 | Indonesian | `Indonesian` |
| 21 | Italian | `Italian` |
| 22 | Japanese | `Japanese` |
| 23 | Korean | `Korean` |
| 24 | Malay | `Malay` |
| 25 | Norwegian (Bokmal) | `Norwegian` |

| 26 | Nynorsk | `Nynorsk` |
| 27 | Persian | `Persian` |
| 28 | Polish | `Polish` |
| 29 | Portuguese | `Portuguese` |
| 30 | Romanian | `Romanian` |
| 31 | Russian | `Russian` |
| 32 | Slovak | `Slovak` |
| 33 | Slovenian | `Slovenian` |
| 34 | Spanish | `Spanish` |
| 35 | Swedish | `Swedish` |
| 36 | Tamil | `Tamil` |
| 37 | Thai | `Thai` |
| 38 | Turkish | `Turkish` |
| 39 | Ukrainian | `Ukrainian` |
| 40 | Vietnamese | `Vietnamese` |

Plus `auto` for auto-detection and `null` (default) for no language boost.

---

## Notes

- API values are **English strings**, not ISO codes (e.g., `"Japanese"` not `"ja"`)
- Cantonese is a special case: `"Chinese,Yue"` (comma, no space)
- Filipino, Persian, Tamil are only available on speech-2.6+ models
