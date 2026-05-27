# Agent Configs — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

An **Agent Config** is the versioned bundle of runtime settings attached to an [[agents|Agent]] — the LLM provider/model + tuning, STT provider/model, TTS provider/model/voice, system prompt, first message, end-call message, and conversation parameters. The voice pipeline (see [[voice-pipeline]]) reads the latest non-deleted config at call-start to build the Pipecat pipeline.

Surface area is intentionally minimal: a single upsert endpoint (`POST /agent_config/upsert_agent_config`). There is no GET, no LIST, no DELETE, no versioning UI — agent CRUD ([[agents]]) reads and mutates configs inline through the agent payload.

- **Target users**: agent owners (set the prompt and pick the providers), backend code that runs the pipeline.
- **Problem solved**: separates the "config payload" from the agent record so that pipeline boot has one clear contract to read from.

## 2. User stories & use cases

- As an agent owner, I want to set the system prompt + LLM model + voice + STT model for my agent in one save.
- As an agent owner, I want each save to bump a `version` so I can audit changes over time (⚠ unimplemented today — version is always 1).
- As a pipeline builder, I want a stable schema I can read at call-start to instantiate Pipecat services.

Typical flow: The agent CRUD form sends the entire payload to `POST /agent/create_agent` or `PUT /agent/update_agent`; the agents controller delegates to `AgentService._upsert_new_config`. The standalone `POST /agent_config/upsert_agent_config` endpoint is exercised primarily by Postman and EE callers.

## 3. Functional requirements

- **`POST /agent_config/upsert_agent_config`** accepts a loose `Dict[str, Any]` body (no Pydantic schema) and writes/updates an `agent_configs` row for the given `agent_id`.
- **Provider resolution**: per LLM/STT/TTS, the service resolves `model_provider_menu_id`, `model_menu_id` (or `voice_menu_id`), and `account_id` (the org's API-key row). Returns `None` on miss.
- **Provider tuning is opaque**: `temperature`, `max_tokens`, voice settings, etc., are stored inside `{stype}_metadata` JSONB columns — not as scalar columns.
- **Read at runtime**: `core/services/agent_factory_service.py:serialize_agent_bot_data()` bulk-loads agent + config + provider/keys/voices in 3 queries, decrypts API keys via `core.utils.encryption`, and caches the materialized payload in Redis (`agent_bot_data:{agent_id}:{transport}`, 30 min TTL).
- **Cache invalidation**: upsert calls `cache_delete_pattern("agent_bot_data:{agent_id}:*")`.

### Edge cases & failure modes

- **⚠ Schema divergence**: `core/models/agent_config.py` declares a **v2 schema** (UUID PK, JSONB `llm_settings`/`voice_settings`/`stt_settings`, `version`, `is_default`, `published_at`, `system_prompt_template`), but `core/services/agent_config_service.py` writes the **legacy schema** (BIGINT PK, `system_prompt`, `llm_account_id`/`tts_account_id`/`stt_account_id`, `llm_metadata`/`tts_metadata`/`stt_metadata`, `status`, `first_message`, `end_call_message`, epoch-int `created_at`/`updated_at`). The factory (`agent_factory_service.py`) reads the legacy columns at runtime — that is authoritative until migrations reconcile.
- **⚠ Silent provider-resolution failures**: `_resolve_account_and_instance` returns `None` on miss and the service writes a partial row that fails only at pipeline build time.
- **⚠ Postman example is misaligned with service code**: uses bare `llm_model_id` / `temperature` / `max_tokens` top-level keys; service only resolves `{stype}_model_menu_id` + `{stype}_model_provider_menu_id` and stores tuning inside `{stype}_metadata`.
- **⚠ Frontend never calls this endpoint**: `frontend/src/services/agentsService.ts` only talks to `/agent/*`. `AgentFormPage.tsx` saves via `createAgentAtom`/`updateAgentAtom` with a v2-shaped `config` blob (see `frontend/src/utils/agentFormUtils.ts`). The `/agent_config/upsert_agent_config` endpoint is exercised only by Postman and EE callers.
- **⚠ `UPSERT_DEBUG` INFO logs leak system_prompt** — sensitive prompt data ends up in logs at INFO level.
- **⚠ RBAC**: only `require_org_member` — no admin/owner check.
- **⚠ Request body is loose `Dict[str, Any]`** — no Pydantic schema, no validation, no type errors.
- **⚠ No version semantics** despite the v2 model declaring `version`/`published_at`. Always written as `version=1`.
- **No dedicated tests** for `AgentConfigService` or this endpoint exist in the repo.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `organization_id` on the `agent_configs` row. The service constructs queries scoped by `self.org_id`.
- **AuthN**: `require_org_member` on the controller.
- **RBAC**: ⚠ none.
- **Performance**: 3 SQL queries to load agent_bot_data (joins providers/keys/voices). 30-min Redis cache.
- **Secrets**: provider API keys are decrypted at pipeline boot, never stored in the cache plaintext.
- **Observability**: INFO-level `UPSERT_DEBUG` logs — ⚠ leak prompt content.

## 5. Test cases (as-built)

⚠ **No dedicated tests** for `AgentConfigService` or this endpoint. The 9 scenarios below derived from controller/service code + Postman.

```
TEST: upsert_creates_new_config
  GIVEN agent X in org A, no agent_config row
  WHEN  POST /api/v1/agent_config/upsert_agent_config
        {"agent_id": "X", "system_prompt": "...", "first_message": "Hi"}
  THEN  200; new agent_configs row inserted with version=1, status='active'

TEST: upsert_updates_existing_config
  GIVEN agent X already has an agent_config row
  WHEN  POST /api/v1/agent_config/upsert_agent_config with new prompt
  THEN  200; existing row updated (no version bump) ⚠

TEST: upsert_resolves_llm_provider
  GIVEN agent X, body includes llm_model_provider_menu_id + llm_model_menu_id
  WHEN  POST /api/v1/agent_config/upsert_agent_config
  THEN  llm_account_id resolved to org's stored API key for that provider

TEST: upsert_missing_account_silent
  GIVEN llm_model_provider_menu_id but no API key configured for that provider
  WHEN  POST /api/v1/agent_config/upsert_agent_config
  THEN  200; row written with llm_account_id=NULL ⚠ — fails at pipeline boot

TEST: upsert_cross_agent_org
  GIVEN agent X in org A; caller in org B
  WHEN  POST /api/v1/agent_config/upsert_agent_config {"agent_id": "X", ...}
  THEN  ⚠ Verify org-scope check — current code may allow leak

TEST: upsert_invalidates_cache
  GIVEN agent X with cached agent_bot_data:X:twilio in Redis
  WHEN  POST /api/v1/agent_config/upsert_agent_config
  THEN  cache key deleted; next bot launch re-fetches

TEST: factory_serializes_agent
  GIVEN agent X with full config
  WHEN  AgentFactoryService(...).serialize_agent_bot_data("X", "twilio")
  THEN  returns dict with decrypted API keys + provider metadata + voice settings

TEST: factory_cache_hit
  GIVEN previous call to serialize_agent_bot_data warmed the cache
  WHEN  AgentFactoryService(...).serialize_agent_bot_data("X", "twilio")
  THEN  returns from Redis without hitting the DB

TEST: upsert_body_validation_loose
  WHEN  POST /api/v1/agent_config/upsert_agent_config {} (no agent_id)
  THEN  ⚠ Likely 500 — no Pydantic validation, error surfaces from SQLAlchemy
```

## 6. Data model / DB schema

**Table: `agent_configs`** (live schema written by `AgentConfigService`)

| Column                  | Type        | Null | Default     | Notes                                                  |
|-------------------------|-------------|------|-------------|--------------------------------------------------------|
| id                      | BIGINT      | NO   | sequence    | PK ⚠ (model declares UUID — drift)                     |
| agent_id                | UUID        | NO   | —           | FK → `agents.id`                                       |
| organization_id         | UUID        | NO   | —           | Multi-tenancy boundary                                 |
| system_prompt           | TEXT        | YES  | —           | Live column name (model declares `system_prompt_template`) |
| first_message           | TEXT        | YES  | —           | Greeting                                               |
| end_call_message        | TEXT        | YES  | —           | Wrap-up message                                        |
| llm_model_provider_menu_id  | INT     | YES  | —           |                                                        |
| llm_model_menu_id       | INT         | YES  | —           |                                                        |
| llm_account_id          | UUID        | YES  | —           | FK → `accounts.id` (API key row)                       |
| llm_metadata            | JSONB       | YES  | `{}`        | `{temperature, max_tokens, ...}`                       |
| stt_model_provider_menu_id  | INT     | YES  | —           |                                                        |
| stt_model_menu_id       | INT         | YES  | —           |                                                        |
| stt_account_id          | UUID        | YES  | —           |                                                        |
| stt_metadata            | JSONB       | YES  | `{}`        |                                                        |
| tts_model_provider_menu_id  | INT     | YES  | —           |                                                        |
| tts_model_menu_id       | INT         | YES  | —           |                                                        |
| tts_voice_menu_id       | INT         | YES  | —           |                                                        |
| tts_account_id          | UUID        | YES  | —           |                                                        |
| tts_metadata            | JSONB       | YES  | `{}`        |                                                        |
| status                  | VARCHAR(20) | NO   | `'active'`  |                                                        |
| version                 | INT         | NO   | `1`         | ⚠ Always 1                                              |
| created_at              | BIGINT      | NO   | epoch       | Epoch seconds                                          |
| updated_at              | BIGINT      | NO   | epoch       | Epoch seconds                                          |

**⚠ Schema drift**: `core/models/agent_config.py` declares the v2 schema (UUID PK, `llm_settings`/`voice_settings`/`stt_settings` JSONB, `version` + `published_at`). The service writes the legacy schema. The factory reads the legacy columns.

**Indexes**: `(agent_id, version)` for fast latest-version lookup.

**Relationships**:
- `agent_configs.agent_id → agents.id` (`ON DELETE CASCADE`)
- `agents.published_config_id → agent_configs.id` (`ON DELETE SET NULL`)

## 7. API design

All endpoints under prefix `/api/v1/agent_config`. Auth: JWT bearer (`require_org_member`). RBAC: ⚠ none.

| Method | Path                                  | Purpose                                          |
|--------|---------------------------------------|--------------------------------------------------|
| POST   | `/agent_config/upsert_agent_config`   | Upsert config for an agent (200 on success)      |

### Request shape (loose, no Pydantic)

```json
{
  "agent_id": "uuid",
  "system_prompt": "You are a helpful support agent...",
  "first_message": "Hi! How can I help?",
  "end_call_message": "Thanks for calling. Goodbye!",
  "llm_model_provider_menu_id": 1,
  "llm_model_menu_id": 7,
  "llm_metadata": {"temperature": 0.7, "max_tokens": 4000},
  "stt_model_provider_menu_id": 3,
  "stt_model_menu_id": 12,
  "stt_metadata": {},
  "tts_model_provider_menu_id": 5,
  "tts_model_menu_id": 18,
  "tts_voice_menu_id": 33,
  "tts_metadata": {"speed": 1.0}
}
```

### Response shape

```json
{
  "id": 42, "agent_id": "uuid", "version": 1, "status": "active",
  "system_prompt": "...", "first_message": "...", "end_call_message": "...",
  "llm_account_id": "uuid", "llm_metadata": {...},
  "stt_account_id": "uuid", "stt_metadata": {...},
  "tts_account_id": "uuid", "tts_metadata": {...},
  "created_at": 1716800000, "updated_at": 1716800500
}
```

### Referenced but not present

- ⚠ No `GET /agent_config/{id}` — must fetch through `GET /agent/get_agent` which embeds the config.
- ⚠ No `DELETE /agent_config/{id}` — deletion cascades from agent delete.
- ⚠ No `POST /agent_config/{id}/publish` — there's no draft/publish flow.

## 8. Backend implementation

- **Controller**: `core/api/v1/agent_configs.py` — single `upsert_agent_config` route.
- **EE Controller**: `ee/api/v1/agent_configs.py` (if present) — mirrors.
- **Service**: `core/services/agent_config_service.py`
  - `upsert_agent_config(data)` — main entry.
  - `_resolve_account_and_instance(stype, provider_menu_id)` — resolves API key + model_instance for a service type.
  - `_invalidate_agent_bot_cache(agent_id)` — calls `cache_delete_pattern("agent_bot_data:{agent_id}:*")`.
- **Model**: `core/models/agent_config.py` (⚠ v2 schema declared, legacy written).
- **Pipeline consumer**: `core/services/agent_factory_service.py:serialize_agent_bot_data()` — bulk-loads + decrypts + caches.
- **Supported provider counts** from `agent_factory_service.py` switch statements:
  - LLM: ~20 (openai, anthropic, groq, google, deepseek, etc.)
  - STT: ~15 (deepgram, speechmatics, openai, etc.)
  - TTS: ~23 (elevenlabs, cartesia, openai, deepgram, etc.)
- **No audit logging**, no Celery tasks, no Pydantic validation.

## 9. Frontend implementation

- ⚠ **No direct caller**: the frontend's agent form (`AgentFormPage.tsx`) does not call this endpoint. It bundles the config payload into the agent create/update body and lets the agent controller upsert the config inline.
- The agent form lives at `/agents/create/{type}` and `/agents/edit/{type}/{id}` — see [[agents]] §9.
- Form state shape in `frontend/src/utils/agentFormUtils.ts`. v2-shaped (`config.llm_settings`, etc.). ⚠ Backend silently maps to legacy columns.

## 10. Postman collection & examples

`postman_collection/agent_configs.postman_collection.json`.

### POST /api/v1/agent_config/upsert_agent_config

⚠ Postman example uses bare `llm_model_id` / `temperature` / `max_tokens` top-level keys; the service expects `llm_model_menu_id` + `llm_metadata.temperature`. Update.

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "system_prompt": "You are a helpful agent...",
    "first_message": "Hi! How can I help?",
    "llm_model_provider_menu_id": 1,
    "llm_model_menu_id": 7,
    "llm_metadata": {"temperature": 0.7}
  }' \
  "$BASE_URL/api/v1/agent_config/upsert_agent_config"
```

## 11. Next steps

- [ ] ⚠ **Reconcile schema drift**: pick v2 (`llm_settings`/`voice_settings`/`stt_settings` JSONB) or legacy (`*_account_id` + `*_metadata` scalar columns). Migrate one to the other. Today the model declares v2 but service + factory operate on legacy.
- [ ] ⚠ **Stop leaking `system_prompt` in INFO logs**: gate `UPSERT_DEBUG` behind a DEBUG-level flag.
- [ ] ⚠ **Add Pydantic schema** for the request body so missing `agent_id` / unknown fields fail with 422, not 500.
- [ ] ⚠ **Add RBAC**: agent config is admin-level (provider keys + prompt are sensitive).
- [ ] ⚠ **Implement versioning**: bump `version` on each upsert; allow rollback to a prior version.
- [ ] ⚠ **Fail loudly on provider-resolution miss**: return 400 with the specific missing API key, don't silently write NULL.
- [ ] ⚠ **Fix Postman example** to use `*_model_menu_id` + `*_metadata` shapes.
- [ ] **Add `GET /agent_config/{id}`** for explicit fetch.
- [ ] **Add tests** under `tests/test_agent_configs.py`.
- [ ] **Add audit logging** for prompt/provider changes.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) Schema drift between v2 model declaration and legacy write/read paths; (2) Provider-resolution failures are silent — partial rows fail only at pipeline boot; (3) Postman example uses incompatible keys; (4) Frontend never calls this endpoint — it goes through [[agents]] instead; (5) `UPSERT_DEBUG` INFO logs leak `system_prompt`; (6) No RBAC; (7) No Pydantic schema; (8) No version semantics despite model declaring `version`/`published_at`; (9) No dedicated tests.
