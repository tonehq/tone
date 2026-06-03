# LLM Issues — Voice Pipeline

Issues discovered during load testing with multiple concurrent calls on agent `f8e20d72` (Hotel Assistant Agent).

---

## Issue 1: Reasoning Models (GPT-5) Cause Silent Bot Due to High TTFB + Interruption Loop

**Model:** `openai/gpt-5` (reasoning model)

**Symptom:** Bot says greeting, user speaks, then bot goes silent. User says "Hello?" repeatedly.

**Root Cause:** GPT-5 is a reasoning model that spends 85-90% of completion tokens on internal reasoning before producing visible output. This causes TTFB of 4-12 seconds. During this silence:
1. User thinks bot didn't hear them and speaks again
2. New speech triggers `UserStartedSpeakingFrame` -> `InterruptionTaskFrame`
3. Since `allow_interruptions=True` (line 1251 in `agent_factory_service.py`), the pending LLM response gets cancelled
4. A new LLM call starts -> again takes 4-12s -> user interrupts again -> deadlock loop

**Evidence from logs:**
- `d9fc85fe`: LLM TTFB 0.83s (interrupted), retry: 12.5s TTFB
- `aea97cdf`: LLM TTFB 0.54s (interrupted), retry: 7.18s TTFB
- `0fc7cd8c`: LLM TTFB 4.64s
- Token breakdown: 256/299 reasoning tokens, 320/360 reasoning tokens — almost all tokens are reasoning

**Key Code Locations:**
- `core/services/agent_factory_service.py:1251` — `allow_interruptions=True`
- `core/services/agent_factory_service.py:1112-1116` — UserTurnStrategies with TranscriptionUserTurnStopStrategy + TranscriptionTimeoutUserTurnStopStrategy
- `core/processors/transcription_timeout_turn_stop.py` — 1.5s timeout fallback

**Possible Fixes:**
- Option A: Detect reasoning models and disable interruptions while LLM is processing (not while TTS is playing)
- Option B: Add a configurable "LLM thinking grace period" — don't allow interruptions for N seconds after LLM call starts
- Option C: Warn/block reasoning models in the agent config UI since they're unsuitable for real-time voice
- Option D: For reasoning models, send a filler phrase via TTS ("Let me check on that...") while waiting for LLM response

---

## Issue 2: Groq `compound` Model Fails on Tool Calling — Every LLM Call Errors Out

**Model:** `groq/compound` (via GroqLLMService)

**Symptom:** Bot says greeting, then never responds to anything. Completely silent after first message.

**Root Cause:** The agent has a `read_document` tool registered (for knowledge base PDF). The pipeline always includes tools in the LLM request. Groq's `compound` model does NOT support tool calling, so every request returns:
```
Error code: 400 - {'error': {'message': '`tool calling` is not supported with this model', 'type': 'invalid_request_error', 'param': 'tool calling'}}
```

The error is non-fatal (`fatal: False`), so the pipeline stays alive but the bot can never generate a response.

**Evidence from logs:**
- Every single GroqLLMService call across all traces (`c0c76148`, `0dd52d29`, `217d1a20`, `fbcc9eb1`, `c788e05c`) fails with the same tool calling error
- Error repeats on every user turn — bot is effectively dead

**Key Code Locations:**
- `core/services/agent_factory_service.py:1110-1111` — `tools = combined_tools` always passed to LLMContext
- `core/services/agent_factory_service.py:1045` — Tool inventory log shows `1 total (doc=1, custom=0, mcp=0) -> ['read_document']`
- `core/services/document_tool_service.py:217` — Tool registration happens unconditionally

**Possible Fixes:**
- Option A (Runtime fallback): If the LLM returns a tool-calling error, retry the request WITHOUT tools. Strip tools from context and retry.
- Option B (Validation at config time): Check model metadata to see if it supports tool calling. If the agent has tools (doc/custom/MCP) and the selected LLM model doesn't support tools, show a warning in the UI or block the configuration.
- Option C (Both): Validate upfront in UI + graceful runtime fallback. This is the safest approach.
- Option D: Store a `supports_tool_calling` flag in the Model metadata (dev-data.json / DB) and check it before including tools in the LLM request.

---

## Issue 3: GPT-5 Rejects Unsupported LLM Parameters (`top_p`, `seed`, `presence_penalty`, `frequency_penalty`)

**Status: FIXED**

**Model:** `openai/gpt-5` (reasoning model)

**Symptom:** Bot says greeting, user speaks, then bot goes silent. LLM call fails on every turn with a 400 error.

**Root Cause:** GPT-5 does not support several parameters that work fine on older models (GPT-4o, etc.). The agent's `llm_settings` stored in DB contained all of these, and the pipeline builder passes them through to the OpenAI API without filtering by model compatibility. The API rejects the entire request.

**Unsupported parameters for GPT-5:**
- `top_p` — `Unsupported parameter: 'top_p' is not supported with this model.`
- `seed` — unsupported
- `presence_penalty` — `Unsupported parameter: 'presence_penalty' is not supported with this model.`
- `frequency_penalty` — `Unsupported parameter: 'frequency_penalty' is not supported with this model.`

**Evidence from logs:**
- First call (`39c5e88b`): `build_input_params` applied `top_p=0.0, seed=1, presence_penalty=-2.0, frequency_penalty=-2.0` → OpenAI returned 400 for `top_p`
- After removing `top_p` and `seed` from DB, second call (`e7c44e35`): `build_input_params` applied `presence_penalty=-2.0, frequency_penalty=-2.0` → OpenAI returned 400 for `presence_penalty`
- Error is non-fatal (`fatal: False`), so pipeline stays alive but bot never responds

### Fix Applied

Moved `meta_data_schema` from provider level to model level. Each LLM model now defines exactly which params it supports. Three layers of protection:

**Layer 1 — Per-model schema in dev-data.json (160 LLM models updated)**
- Each model has its own `meta_data_schema` based on official API docs
- GPT-5/o3/o4 reasoning models: only `max_completion_tokens`
- GPT-4o/4.1 standard models: full param set (temperature, top_p, frequency_penalty, etc.)
- All other providers (Groq, Anthropic, Google, DeepSeek, Grok, Perplexity, Qwen, OpenRouter) mapped correctly
- Script: `dev/add_model_schemas.py` — can be rerun when models are added

**Layer 2 — Frontend shows only supported params per model**
- `AiStep.tsx`: reads `meta_data_schema` from the selected model (falls back to provider schema)
- When user switches models, a `useEffect` clears stale form values not in the new schema
- Example: switching GPT-4o → GPT-5 removes temperature/top_p from form state
- `VoiceStep.tsx`: same pattern for TTS and STT schemas

**Layer 3 — Backend runtime filtering (safety net for stale DB data)**
- `agent_runtime_resolver.py`: `_filter_by_model_schema()` strips settings keys not in the model's `meta_data_schema` before passing to the pipeline builder
- Catches cases where old settings are saved in DB from a previous model selection
- If model has no schema, all settings pass through unchanged (backward compatible)

**Layer 4 — Backend validation uses model schema**
- `agent_service.py`: `_validate_meta_data_schema()` now prefers model-level schema over provider-level
- Falls back to provider schema if model has no schema (backward compatible)

**Files changed:**
| File | Change |
|------|--------|
| `dev/dev-data.json` | 160 LLM models with per-model `meta_data_schema` |
| `dev/add_model_schemas.py` | Script to generate model schemas |
| `core/models/model.py` | Added `meta_data_schema` JSONB column |
| `core/services/model_provider_service.py` | Returns `meta_data_schema` in model API response |
| `core/services/agent_service.py` | Validation uses model schema first, provider fallback |
| `core/services/agent_runtime_resolver.py` | Runtime filtering of stale params |
| `dev/seed.py` | Stores model-level schema from dev-data.json |
| `frontend/src/types/service.ts` | Added `meta_data_schema` to `ProviderModel` type |
| `frontend/src/components/agents/agent-form/steps/AiStep.tsx` | Schema from model + stale field cleanup |
| `frontend/src/components/agents/agent-form/steps/VoiceStep.tsx` | Schema from model for TTS/STT |

**DB migration needed:** Add `meta_data_schema` JSONB column to `models` table (not auto-created — run `alembic revision --autogenerate`).

---

## General Observations

- All three issues produce the same user-visible symptom: bot says hello then goes silent
- The pipeline's error handling for non-fatal LLM errors is too silent — the user/caller gets no feedback
- Consider adding an audible error response ("I'm sorry, I'm having trouble processing your request") when the LLM fails, so the caller knows something went wrong instead of hearing silence
- The `allow_interruptions=True` setting is correct for normal conversational models but creates problems with slow models — this may need to be model-aware
- Issue 1 (reasoning model TTFB) and Issue 2 (tool calling) are still open — to be fixed separately
