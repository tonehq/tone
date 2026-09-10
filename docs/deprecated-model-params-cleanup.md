# Deprecated Model Parameters — Cleanup Notes

**Branch:** `remove-deprecated-models`
**Date:** 2026-09-10
**Goal:** Remove/replace deprecated provider parameters exposed in the agent configuration so that
(a) no deprecation warnings/errors are raised at call time, (b) every schema field maps to a
parameter the provider still accepts, (c) existing agents keep working, (d) the provider validator
passes for all providers.

> This is a living log of everything changed (or intentionally left unchanged) during this effort.
> Source of truth for schemas is `dev/dev-data.json` (model-level `meta_data_schema`; provider-level
> is only the fallback). Full raw research + inventory is in `.context/` (git-ignored):
> `provider-param-inventory.md`, `research-findings-raw.md`.

---

## 1. Scope of the audit

Audited **every** provider and model parameter schema in `dev/dev-data.json`:

| Category | Providers | Notes |
|---|---|---|
| LLM | 17 | openai, groq, anthropic, google, openrouter, qwen, deepseek, grok, cohere, perplexity, azure, nvidia_nim, aws_bedrock, openai_realtime, gemini_live, cerebras, sarvam-ai |
| STT | 15 | deepgram, openai, groq, sarvam, assemblyai, cartesia, soniox, elevenlabs, gladia, nvidia, speechmatics, google, azure, mistral, kyutai |
| TTS | 22 | cartesia, deepgram, groq, minimax, rime, sarvam, fish, inworld, openai, resemble, nvidia, neuphonic, lmnt, elevenlabs, asyncai_http, aws_polly, google, azure, speechmatics, voxtral/chatterbox/qwen3 (hosted) |

Each model's `meta_data_schema` fields were checked against the provider's current API docs (Sept 2026)
and the Pipecat service contract. Research was run via the `deep-research` workflow (LLM + TTS) plus
direct web searches (STT). **Note:** the LLM/TTS research verify+synthesize phases were cut short by an
account credit limit — items below are sourced from primary provider docs; ⭐ = re-confirm before merge.

---

## 2. KEYS REMOVED from `dev/dev-data.json` (this change)

11 field removals, all pure deletions (228 lines). No providers or models were added or deleted here.

### LLM

| Provider | Model(s) | Key(s) removed | Why | Resulting schema |
|---|---|---|---|---|
| `openai_realtime` | provider fallback + `gpt-4o-realtime-preview`, `gpt-4o-mini-realtime-preview`, `gpt-realtime` | `temperature` | `temperature` was **removed as a model parameter in the Realtime GA API** (beta clamped it to 0.6–1.2). OpenAI recommends prompting instead. | `[voice_id]` (provider), `[max_completion_tokens]` (models) |
| `anthropic` | `claude-opus-4-6`, `claude-opus-4-7` | `thinking_budget_tokens` | Manual extended thinking is **deprecated on Claude 4.6** and **unsupported on Claude 4.7+ (hard 400)**. Also the real API field is nested `thinking.budget_tokens`, not a flat key. | `[temperature, top_p, top_k, max_tokens]` |
| `azure` (LLM) | `microsoft/MAI-DS-R1` | `temperature`, `top_p`, `frequency_penalty`, `presence_penalty` | MAI-DS-R1 is a **reasoning model**; Azure reasoning models do **not support** these params (unsupported → 400). | `[seed, max_completion_tokens]` |

### TTS

| Provider | Model(s) | Key(s) removed | Why | Resulting schema |
|---|---|---|---|---|
| `azure` (TTS) | `DragonHDLatestNeural`, `DragonHDOmniLatestNeural`, `DragonHD Flash`, `MultiTalker DragonHDLatestNeural` | `rate`, `volume`, `style` | Azure **HD (Dragon) voices do not support `<prosody>` (rate/volume/pitch) or `<mstts:express-as>` (style/role)** — the values are silently ignored. HD voices steer expressiveness via `temperature` (see §5 follow-up). | `[region]` |

### STT
No key removals — the STT schemas were already correct (see §3).

---

## 2b. MODELS removed / replaced (this change)

Removed the **already-retired** models (past their vendor shutdown date, verified 3-0) and pointed each
to its current replacement. Where the replacement already existed in the seed, the retired model was
simply deleted; otherwise the entry was renamed in place (preserving `base_url`, schema, etc.).

| Category | Provider | Removed | Replacement | How |
|---|---|---|---|---|
| LLM | anthropic | `claude-opus-4-1` (retired 2026-08-05) | `claude-opus-4-8` | Renamed entry → 4-8; also dropped `thinking_budget_tokens` (schema + `meta_data`) since extended thinking is unsupported on Claude 4.7+ |
| STT | soniox | `stt-rt-v3`, `stt-async-v3` (removed 2026-02-28) | `stt-rt-v5` / `stt-async-v5` | Deleted (v3 entries) |
| STT | soniox | `stt-rt-v4`, `stt-async-v4` (removed 2026-06-30) | `stt-rt-v5` / `stt-async-v5` | Renamed v4 → v5 |
| TTS | rime | `arcana` (cloud retired 2026-08-15) | `coda` | Renamed model → coda **and repointed all 273 arcana voices' `model_name` → coda** |
| TTS | fish | `speech-1.5`, `speech-1.6` (deprecated 2026-02-28) | `s1` / `s2-pro` (already in seed) | Deleted |

Net model-list results: anthropic `…, claude-opus-4-8, …`; soniox `[stt-rt-v5, stt-async-v5]`;
rime `[coda, mistv2, mist]`; fish `[s1, s2-pro]`.

> Deprecated-but-still-working models (§4b: OpenAI `o3`/`o3-pro`, Google `gemini-2.5-*`, Cartesia
> `sonic-2`/`sonic-turbo`, Inworld `tts-1.5-*`, the OpenRouter legacy list, …) were **left in place** —
> they have future shutdown dates and their replacements (`gpt-5.6`, `sonic-3.6`, etc.) are not yet in
> the seed. Handle in a follow-up.

---

## 3. Checked and left UNCHANGED (already correct)

The seed was already ~90% correct; the team had previously moved schemas to model level and
pre-excluded most deprecated params. Verified still-correct:

- **Groq / DeepSeek / Grok** — `frequency_penalty` / `presence_penalty` already excluded (deprecated / silently-ignored / hard-error on reasoning). ✔
- **OpenAI reasoning (gpt-5 / o3 / o4)** — already limited to `max_completion_tokens`. ✔
- **Sarvam-AI (LLM)** — `temperature/top_p/seed/penalties/max_tokens/reasoning_effort/wiki_grounding` all current; `top_k` correctly not exposed. ✔
- **AWS Bedrock Nova** — only `temperature/top_p/max_tokens` (Converse API base params). ✔
- **Gemini Live** — all exposed params valid (`maxOutputTokens/temperature/topP/topK/penalties`). ✔
- **AssemblyAI** — uses `keyterms_prompt`; `word_boost` (retired 2026-09-11) is not exposed anywhere. ✔
- **Deepgram** — `keywords` correctly only on nova-2/1 models; nova-3 doesn't expose it. ✔
- **Google STT v2** — all `enable_*` RecognitionFeatures still current in the v2 API. ✔
- **Sarvam TTS `bulbul:v3`** — `loudness`/`pitch` (v2-only) already excluded; `temperature` present. ✔
- **AWS Polly** — `pitch` correctly only on `standard`, not neural/generative/long-form. ✔
- **OpenAI TTS** — `instructions` correctly only on `gpt-4o-mini-tts`. ✔
- **ElevenLabs / MiniMax / Cartesia** — `stability/style`, `volume/pitch/emotion`, `speed` all current. ✔

---

## 4. Deprecated MODELS (from deep-research run `wf_d86950eb-638`, all rows verified 3-0)

These are retired/superseded **models** (not keys), mapped to our actual seed model ids. **Not removed yet**
— pending your go-ahead, since they change what agents can select and may need a migration for agents
already on them. `⭐` = re-confirm before acting.

### 4a. RETIRED (vendor already removed — past shutdown date) — ✅ DONE (see §2b)

| Category | Provider | Seed model id | Status | Replacement |
|---|---|---|---|---|
| LLM | anthropic | `claude-opus-4-1` | Retired 2026-08-05 | ✅ → `claude-opus-4-8` |
| STT | soniox | `stt-rt-v3`, `stt-async-v3` | Removed 2026-02-28 | ✅ → `stt-rt-v5` / `stt-async-v5` |
| STT | soniox | `stt-rt-v4`, `stt-async-v4` | Removed 2026-06-30 | ✅ → `stt-rt-v5` / `stt-async-v5` |
| TTS | rime | `arcana` | Cloud retired 2026-08-15 → Coda | ✅ → `coda` (+273 voices) |
| TTS | fish | `speech-1.5`, `speech-1.6` | Deprecated 2026-02-28 | ✅ → `s1` / `s2-pro` |

### 4b. DEPRECATED — still works, shutdown scheduled

| Category | Provider | Seed model id(s) | Shutdown | Replacement |
|---|---|---|---|---|
| LLM | openai | `o3`, `o3-pro` | 2026-12-11 | `gpt-5.6-sol` |
| STT | openai | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`(+snapshots) | 2027-02-26 | `gpt-transcribe` / `gpt-live-transcribe` |
| LLM | google | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` | 2026-10-16 | `gemini-3.x` |
| STT | google | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` | 2026-10-16 | `gemini-3.x` |
| TTS | google | `gemini-2.5-pro-preview-tts`, `gemini-2.5-flash-preview-tts` | 2026-10-16 ⭐ | `gemini-3.x` tts |
| LLM | openrouter | `google/gemini-2.5-pro`, `google/gemini-2.5-flash`, `google/gemini-2.5-flash-lite` | 2026-10-16 | `google/gemini-3.x` |
| TTS | cartesia | `sonic-2`, `sonic-turbo` | after 2026-10-20 | `sonic-3.6` |
| TTS | cartesia | `sonic-3.5` | superseded | `sonic-3.6` |
| TTS | inworld | `inworld-tts-1.5-max`, `inworld-tts-1.5-mini` | deprecated | `inworld-tts-2` / `-2-flash` |
| LLM | openrouter | `openai/gpt-4`, `gpt-4-turbo`, `gpt-4-1106-preview`, `gpt-3.5-turbo`, `gpt-3.5-turbo-0613`, `gpt-3.5-turbo-16k`, `gpt-3.5-turbo-instruct`, `o1`, `o1-pro`, `o3-mini`, `o3-mini-high` | 2026-10-23 | `openai/gpt-5.6` |
| LLM | openrouter | `openai/o3`, `openai/o3-pro` | 2026-12-11 | `openai/gpt-5.6` |
| LLM | openrouter | `deepseek/deepseek-r1`, `deepseek-r1-0528`, `deepseek-chat-v3-0324` ⭐ | Azure Foundry retired; may still route via DeepSeek-direct | `deepseek/deepseek-v4-*` |

### 4c. Confirmed ACTIVE — keep (do not remove)
OpenAI-direct `gpt-4o` / `gpt-4o-mini` / `gpt-4.1-mini` / `gpt-4.1-nano` (⭐ nano had one conflicting retire claim),
OpenAI TTS `tts-1` / `tts-1-hd` / `gpt-4o-mini-tts`, Cohere `command-a-03-2025` / `command-r*-08-2024`,
Deepgram `nova-3` / `nova-2*` / `flux`, ElevenLabs `scribe_v2` + `eleven_*`, AssemblyAI `Universal-2`.

### 4d. UNRESOLVED this pass (no evidence gathered → verify before touching)
Perplexity `sonar*`; Azure `Phi-3*` / `Phi-3.5*`; NVIDIA NIM `nemotron*`; AWS Bedrock `amazon.nova-*-v1:0`
(nova-2 exists); Google `gemma-4*`; Deepgram `aura` vs `aura-2`; Sarvam `bulbul:v2` (earlier TTS pass:
deprecated, v3 default); Resemble `tts-v4`; Google STT `chirp` / `chirp_2` / `chirp_3`.

---

## 5. Follow-ups / open items

1. **Azure HD voices — add `temperature`.** After removing `rate/volume/style`, DragonHD models expose
   only `[region]`. HD voices control expressiveness via `temperature` (0–1; +`top_p`/`top_k`/`cfg_scale`
   for Omni). Adding it requires confirming Pipecat's `AzureTTSService` accepts a `temperature` param in
   the pinned `tone-pipecat==0.0.76.dev8`; deferred until verified (otherwise it'd be dropped by
   `build_input_params`).
2. **Deepgram nova-3 — optionally add `keyterm`** (the nova-3 replacement for `keywords`, which nova-3
   rejects). Not a deprecation, just a missing capability.
3. **OpenRouter reasoning** — ensure `reasoning_effort` and the `reasoning` object are never sent together
   (→ 400 "Only one of reasoning and reasoning_effort"). Adapter maps to `extra_body.reasoning`, so likely
   fine; confirm in `core/services/pipeline/service_factory.py`.
4. **Framework-level deprecation** — upstream Pipecat deprecates `params=`/`InputParams` → `settings=`
   (and Inworld `voice_id`→`voice`) **as of v0.0.105**. Our pin `tone-pipecat==0.0.76.dev8` predates this,
   so it likely does **not** fire. Confirm against the installed fork; a real call log with the warning
   text would pinpoint any runtime warning precisely.
5. **`google-generativeai==0.8.6`** is EOL (support ended 2025-11-30) in favor of `google-genai` (already
   pinned at 1.68.0, which Pipecat uses). Verify it's a dead transitive dep and drop if unused.
6. **DB sync** — two purpose-built scripts push these changes into the running environment's rows.
   Set `DATABASE_URL` at the top of each, then run from project root **in this order**:
   1. `dev/remove_deprecated_schema_keys.py` — strips the deprecated keys from
      `models.meta_data_schema` + `model_providers.meta_data_schema` (targeted, idempotent; matches §2).
   2. `dev/sync_deprecated_model_changes.py` — applies the model removals/replacements (§2b):
      renames retired rows in place (`claude-opus-4-1`→`4-8`, soniox `v4`→`v5`, `arcana`→`coda`) so the
      row UUID and its **273 Rime voices** are preserved, and deletes the pure removals (soniox `v3`,
      fish `speech-1.5`/`1.6`).
   Both are idempotent and touch no agent settings — the runtime `_filter_by_model_schema()` strips any
   now-removed keys, so no agent-settings migration is required. (The generic
   `dev/update_model_meta_data_schema.py` / `update_meta_data_schema.py` also re-sync all schemas from the
   seed, but do NOT delete/rename model rows — hence the dedicated scripts.)
7. **Validate** — run the provider validator / `dev/validate_models.py` and confirm no agent config write
   fails `_validate_meta_data_schema`.

---

## 6. Change log

- **2026-09-10** — Audited all LLM/STT/TTS provider param schemas. Removed 11 deprecated keys from
  `dev/dev-data.json` (Realtime `temperature`; Anthropic `thinking_budget_tokens` on opus-4-6/4-7;
  MAI-DS-R1 `temperature/top_p/frequency_penalty/presence_penalty`; Azure HD `rate/volume/style`).
  Documented already-correct schemas, deprecated models pending removal, and follow-ups above.
- **2026-09-10** — Ran deep-research on model lifecycle (§4). Removed the 5 already-retired model groups
  and pointed each to its current replacement (§2b): anthropic `claude-opus-4-1`→`claude-opus-4-8`
  (dropped extended thinking); soniox v3 deleted + v4→v5; rime `arcana`→`coda` (+repointed 273 voices);
  fish `speech-1.5`/`speech-1.6` deleted. Deprecated-but-live models (§4b) left for a follow-up.
