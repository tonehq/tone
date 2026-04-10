# TTS Provider — Voice, Model & Language Dependency Matrix

> **Last updated:** 2026-03-27
> **Source:** Official provider documentation and API references

---

## Quick Summary

### Category 1: Model does NOT matter — All voices & languages work with any model

| Provider       | Why model doesn't matter                                                    |
|----------------|-----------------------------------------------------------------------------|
| **LMNT**       | Single model (Blizzard). All voices work with all 21 languages.             |
| **Camb AI**    | All voices work with all models (Flash/Pro/Instruct/Nano). 140+ languages shared across models. |
| **Speechmatics** | No model selection — single TTS service. 4 English-only voices.          |

### Category 2: Model matters ONLY for language support — Voices are universal

| Provider        | Voice-Model dependency? | Language-Model dependency?                                   |
|-----------------|------------------------|--------------------------------------------------------------|
| **Cartesia**    | No — any voice, any model | Yes — sonic-3: 42 langs, sonic-2/turbo: ~15, sonic-english: English only |
| **ElevenLabs**  | No — any voice, any model | Yes — eleven_v3: 70+ langs, flash/turbo_v2_5: 32, flash/turbo_v2: English only |

| **MiniMax**     | No — any voice, any model | Yes — speech-2.6+: 40+ langs, speech-02: 32, speech-01: fewer |
| **Inworld**     | Not confirmed, likely shared across same-gen models | Yes — TTS 1.5: 15 langs, TTS 1.0: 13 langs |

### Category 3: Model matters — Voices AND/OR languages are model-specific

| Provider       | What's tied to model                                                        |
|----------------|-----------------------------------------------------------------------------|
| **Groq**       | Each model = 1 language + its own voice set. English model: 6 voices. Arabic model: 4 voices. |
| **Rime**       | Different voice catalogs per model. Mist: English only (~134 voices). Mist v2: 4 langs (~169 voices). Arcana: 9 langs (262+ voices). Almost no voice overlap. |
| **Sarvam**     | Completely separate speaker sets per model. bulbul:v2: 7 speakers. bulbul:v3: 39 speakers. No overlap. Languages (11) are shared across all speakers within a model. |
| **Hume**       | Octave 2 voices don't work on Octave 1. Octave 1: 2 langs. Octave 2: 11 langs. |
| **Neuphonic**  | Voices are tied to specific models. Languages may vary per model. Docs say: "Ensure voice ID is available for the selected model." |
| **Async AI**   | Only 1 model currently (Flash 1.0). Voices may have language properties. 16 languages supported. |

---

## Detailed Provider Breakdown

### 1. Cartesia

| Aspect    | Details |
|-----------|---------|
| **Models** | `sonic-3`, `sonic-2`, `sonic-turbo`, `sonic` (legacy), `sonic-english` (English only) |
| **Voices** | Universal — any voice works with any model |
| **Languages** | Model-dependent: sonic-3 = 42 langs, sonic-2/turbo = ~15, sonic-english = English only |
| **Mapping rule** | Pick model based on required language. If language needs >15 langs → use `sonic-3`. Voice is independent. |

### 2. ElevenLabs

| Aspect    | Details |
|-----------|---------|
| **Models** | `eleven_v3` (70+ langs), `eleven_multilingual_v2` (29 langs), `eleven_flash_v2_5` (32 langs), `eleven_turbo_v2_5` (32 langs), `eleven_flash_v2` (English only), `eleven_turbo_v2` (English only) |
| **Voices** | Universal — any voice works with any model |
| **Languages** | Model-dependent. English-only models won't accept other languages (server error). |
| **Mapping rule** | Pick model based on required language + latency needs. If non-English → use v3, flash_v2_5, turbo_v2_5, or multilingual_v2. Voice is independent. |
| **Note** | `eleven_multilingual_v2` auto-detects language (no `language_code` param). `eleven_flash_v2_5`/`eleven_turbo_v2_5` accept explicit `language_code`. |

### 3. OpenAI

| Aspect    | Details |
|-----------|---------|
| **Models** | `tts-1`, `tts-1-hd`, `gpt-4o-mini-tts` |
| **Voices** | 9 shared voices (alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer) work on ALL models. 4 extra voices (ballad, verse, marin, cedar) are **gpt-4o-mini-tts only**. |
| **Languages** | All models support 50+ languages equally. No language-model dependency. |
| **Mapping rule** | If voice is ballad/verse/marin/cedar → must use `gpt-4o-mini-tts`. Otherwise any model works. `instructions` param only works on `gpt-4o-mini-tts`. |

### 4. Groq

| Aspect    | Details |
|-----------|---------|
| **Models** | `canopylabs/orpheus-v1-english` (English), `canopylabs/orpheus-arabic-saudi` (Arabic) |
| **Voices** | **Model-specific.** English: autumn, diana, hannah, austin, daniel, troy. Arabic: fahad, sultan, lulwa, noura. |
| **Languages** | **Model-specific.** Each model = exactly 1 language. |
| **Mapping rule** | Model is determined by language. Arabic → arabic model + arabic voices. English → english model + english voices. **Strict 1:1:1 mapping.** |

### 5. Neuphonic

| Aspect    | Details |
|-----------|---------|
| **Models** | `neu_hq`, plus others (NeuTTS Air, NeuTTS Nano, NeuCodec, Longform Inference) |
| **Voices** | **Model-specific.** Docs: "Ensure this voice ID is available for the selected model." |
| **Languages** | Likely model-specific. 15 languages supported total (en, ar, ca, zh, nl, fr, de, hi, ja, kn, es, te, ta, pt, ru). |
| **Mapping rule** | Must validate voice+model+language combo. Use their List Voices API to get valid combinations. No public compatibility matrix available. |

### 6. LMNT

| Aspect    | Details |
|-----------|---------|
| **Models** | `blizzard` (only model — `aurora` is now an alias for blizzard) |
| **Voices** | Universal — all voices work with the single model. Supports cross-lingual transfer. |
| **Languages** | 21 languages: en, ar, de, es, fr, hi, id, it, ja, ko, nl, pl, pt, ru, sv, th, tr, uk, ur, vi, zh. Plus `auto` detection. |
| **Mapping rule** | No mapping needed. Single model. Any voice + any language. |

### 7. Rime

| Aspect    | Details |
|-----------|---------|
| **Models** | `mist` (English only), `mistv2` (4 langs), `arcana` (9 langs) |
| **Voices** | **Model-specific.** Mist: ~134 voices. Mist v2: ~169 voices. Arcana: 262+ voices. Almost no overlap between catalogs. |
| **Languages** | **Model-specific.** Mist: English. Mist v2: English, Spanish, French, German. Arcana: + Portuguese, Arabic, Hebrew, Hindi, Japanese. |
| **Mapping rule** | Voice determines the model (since voice catalogs barely overlap). If you need Arabic/Hindi/Japanese → must use `arcana`. Language must match voice's language tag. **Three-way dependency.** |
| **Reference** | Voice catalog available at `https://users.rime.ai/data/voices/all-v2.json` |

### 8. Inworld

| Aspect    | Details |
|-----------|---------|
| **Models** | `inworld-tts-1.5-max`, `inworld-tts-1.5-mini` (current). `inworld-tts-1-max`, `inworld-tts-1` (deprecated). |
| **Voices** | Likely shared across same-generation models (not explicitly confirmed in docs). |
| **Languages** | Model-dependent. TTS 1.5: 15 langs (en, zh, ja, ko, ru, it, es, pt, fr, de, pl, nl, hi, he, ar). TTS 1.0: 13 langs (no Hebrew, Arabic). |
| **Mapping rule** | Use TTS 1.5 models. If Hebrew/Arabic needed → must be 1.5. Voice cloning and voice design supported. |

### 9. Hume

| Aspect    | Details |
|-----------|---------|
| **Models** | Octave 1 (version `"1"`), Octave 2 (version `"2"`, preview) |
| **Voices** | **Asymmetric.** Octave 1 voices work on both versions. Octave 2 voices work on Octave 2 ONLY. |
| **Languages** | **Model-specific.** Octave 1: English, Spanish. Octave 2: 11 langs (en, ja, ko, es, fr, pt, it, de, ru, hi, ar). |
| **Mapping rule** | If non-English/Spanish language needed → must use Octave 2. Octave 2 voices can't be used with Octave 1. Check voice compatibility before assigning version. |

### 10. Camb AI

| Aspect    | Details |
|-----------|---------|
| **Models** | `MARS-Flash` (real-time), `MARS-Pro` (high-fidelity), `MARS-Instruct` (promptable), `MARS-Nano` (on-device) |
| **Voices** | Universal — any voice works with any model. |
| **Languages** | 140+ languages. Shared across all models. |
| **Mapping rule** | No mapping needed. Pick model based on latency/quality needs. Voice and language are independent. Only `MARS-Instruct` supports `user_instructions` param. |

### 11. Async AI

| Aspect    | Details |
|-----------|---------|
| **Models** | `async_flash_v1.0` (only GA model). `async_pro_v1.0` coming soon. |
| **Voices** | 500+ voices (UUID-based). Voices have language properties. |
| **Languages** | 16 langs: en, fr, es, de, it, pt, nl, ar, ru, ro, ja, he, hy, tr, hi, zh. |
| **Mapping rule** | Single model currently. Voice language property exists — may need to match. Use List Voices API to filter by language. |

### 12. Speechmatics

| Aspect    | Details |
|-----------|---------|
| **Models** | No model selection — single TTS service. |
| **Voices** | 4 voices: sarah (en-GB), theo (en-GB), megan (en-US), jack (en-US). |
| **Languages** | English only (UK and US accents). |
| **Mapping rule** | No mapping needed. Pick voice = pick accent. No model or language selection. |

### 13. Sarvam

| Aspect    | Details |
|-----------|---------|
| **Models** | `bulbul:v2` (7 speakers), `bulbul:v3` (39 speakers) |
| **Voices** | **Model-specific.** Completely separate speaker sets. v2: Anushka, Manisha, Vidya, Arya, Abhilash, Karun, Hitesh. v3: Shubh, Aditya, Rahul, + 36 more. Zero overlap. |
| **Languages** | All 11 Indic languages shared across ALL speakers within a model: hi-IN, bn-IN, ta-IN, te-IN, gu-IN, kn-IN, ml-IN, mr-IN, pa-IN, od-IN, en-IN. |
| **Mapping rule** | Voice determines model (no overlap). Language is independent within a model. |

### 14. MiniMax

| Aspect    | Details |
|-----------|---------|
| **Models** | `speech-2.8-hd/turbo`, `speech-2.6-hd/turbo`, `speech-02-hd/turbo`, `speech-01-hd/turbo` |
| **Voices** | Universal — 300+ voices work across all models. |
| **Languages** | Model-dependent. speech-2.6+: 40+ langs. speech-02: 32 langs. speech-01: fewer. |
| **Mapping rule** | Pick model based on required language + latency (hd vs turbo). Voice is independent. |

---

## Backend Mapping Logic Cheat Sheet

When user selects a **voice** and **language**, here's how to resolve the model:

```
PROVIDER                  → HOW TO PICK MODEL
─────────────────────────────────────────────────────────────────
LMNT                      → Always "blizzard" (only model)
Speechmatics              → No model needed (single service)
Async AI                  → Always "async_flash_v1.0" (only GA model)
Camb AI                   → Default to "MARS-Flash" (all voices/langs work)
Cartesia                  → Default to "sonic-3" (supports most languages)
ElevenLabs                → Default to "eleven_flash_v2_5" (32 langs, low latency)
                            If language not in flash_v2_5 → use "eleven_v3" (70+ langs)
OpenAI                    → If voice in [ballad,verse,marin,cedar] → "gpt-4o-mini-tts"
                            Else → default "gpt-4o-mini-tts" (best quality, all voices)
MiniMax                   → Default to latest "speech-2.8-turbo" (40+ langs)
Inworld                   → Default to "inworld-tts-1.5-max" (15 langs)
Groq                      → If language == "ar" → "canopylabs/orpheus-arabic-saudi"
                            Else → "canopylabs/orpheus-v1-english"
Rime                      → Voice determines model (lookup voice catalog)
                            Fallback: if lang in [pt,ar,he,hi,ja] → "arcana"
                            if lang in [es,fr,de] → "mistv2" or "arcana"
                            if lang == "en" → any model
Sarvam                    → Voice determines model (lookup speaker list)
                            v2 speakers: anushka,manisha,vidya,arya,abhilash,karun,hitesh
                            v3 speakers: all others → "bulbul:v3"
Hume                      → If language not in [en,es] → version "2" (Octave 2)
                            Else → check if voice is Octave-2-only
Neuphonic                 → Must validate via API. No simple rule.
Deepgram                  -> Configured correctly need to test. Default model is aura-2
```

---

## Not Configured

The following TTS providers are supported in code but not yet documented in this matrix:

- PlayHT
- AWS Polly
- Google Base
- NVIDIA
- Azure
- Fish
- Hathora
- Resemble
