# Model Providers — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

The **Model Providers** feature is the catalog + per-org-credential layer for LLM, STT, and TTS providers. Tone supports 55+ provider integrations via Pipecat — OpenAI, Anthropic, Groq, Google, Deepgram, ElevenLabs, Cartesia, Speechmatics, MiniMax, Rime, Sarvam, etc. — across three categories:

- **LLM**: text generation (the agent's "brain").
- **STT**: speech-to-text (caller audio → text).
- **TTS**: text-to-speech (agent text → audio).

Tenants store their own API keys (AES-encrypted via Fernet/PBKDF2) on per-service `api_keys` rows; the catalog itself (providers, models, voices, languages) is globally shared and seeded by `dev/seed.py` from `dev/dev-data.json`. The voice pipeline ([[voice-pipeline]]) joins agent config → provider → model → API key at call-start to instantiate the right Pipecat service.

- **Target users**: org admins/owners (paste API keys), agent owners (pick models in [[agents]] / [[agent-configs]]).
- **Problem solved**: a single multi-tenant place to store per-provider credentials with encryption-at-rest, plus a shared model/voice/language catalog so the agent form has rich pickers.

Cross-links: [[agents]], [[agent-configs]], [[voice-pipeline]], [[oauth-integrations]].

## 2. User stories & use cases

- As an org owner, I want to paste my OpenAI API key and have it stored encrypted so my org's agents can use GPT-4o.
- As an agent owner, I want a dropdown of available LLM/STT/TTS providers + their models in the agent form.
- As an org admin, I want to toggle the "default" provider per service type so new agents pick a sensible default.
- As an org admin, I want to copy a connection (`source_key_id`) for a different service type without re-pasting the key — e.g., OpenAI key shared between LLM and embeddings.
- As an agent owner, I want to filter TTS by language to find voices that support my caller's language.
- As an org admin, I want to bulk delete all keys for a provider when revoking access.

Typical flow: Admin → Settings → Model Providers → "Add OpenAI" → drawer with API key + service type — submits → encrypted key stored → key appears in [[agents]] form as an LLM option.

## 3. Functional requirements

- **Per-org API keys** (`/api/v1/services/list`, `POST /services`, `GET /services/{id}`, `PATCH /services/{id}`, `DELETE /services/{id}`): stores encrypted credentials per (org, provider, service_type).
- **Source-key copy** via `source_key_id`: re-use an existing org's API-key row for the same provider but different `service_type` (e.g., copy OpenAI LLM key into OpenAI Embeddings).
- **Default flag**: `is_default=true` per `service_type` — partial unique index `uq_api_keys_one_default_per_org_type`. Setting a key default unsets the previous default in a single transaction.
- **Bulk delete**: `DELETE /services/providers/{provider_id}` removes all keys for that provider in the org; `DELETE /services/{service_id}` removes one.
- **Provider catalogue**: `GET /services/providers/catalog` returns the global list of supported providers (across LLM/STT/TTS).
- **Provider drill-down**:
  - `POST /services/providers/{provider_id}/keys` → list keys for a provider.
  - `POST /services/providers/{provider_id}/models` → list models for a provider (globally shared catalog).
  - `POST /services/providers/{provider_id}/models` (create) / `PATCH .../{model_id}` (update) / `DELETE .../{model_id}` (admin-only model catalog edits).
- **TTS catalog**:
  - `GET /services/tts/providers` → list TTS providers in catalog.
  - `GET /services/tts/voices?provider_id=...&language_id=...` → list voices filtered by provider + language.
  - `GET /services/tts/languages?provider_id=...` → list languages supported by a TTS provider.
- **Encryption**: API keys stored via Fernet symmetric encryption with PBKDF2-derived key. Master key is `settings.JWT_SECRET` (⚠ same as auth signing key — single point of failure).

### Edge cases & failure modes

- **Interlocked `is_default` invariant**: partial unique index `uq_api_keys_one_default_per_org_type` enforces "at most one default per service_type per org". When a new key is set `is_default=true`, the previous default is `is_default=false` in the same UPDATE.
- **`source_key_id` same-provider rule**: when copying from a source key, the new row must share `provider_id` (different `service_type` is the typical use). The service rejects cross-provider copies.
- **NULL-`service_type` exclusion**: rows with `service_type IS NULL` are excluded from the partial unique index (legacy rows tolerated).
- **⚠ Missing FK from `agent_configs` to `models`**: `agent_configs.llm_model_menu_id` / `stt_model_menu_id` / `tts_model_menu_id` are bare INT columns, not FKs. Orphan possible if a model is deleted.
- **⚠ JWT-secret-as-master-key**: rotating `JWT_SECRET` invalidates ALL encrypted API keys. Encryption key rotation needs a separate setting.
- **⚠ Static salt** in PBKDF2 — same salt across all installations. Cracking one DB makes others trivial.
- **⚠ Legacy parallel API**: `/model-providers-menu`, `/model-menu`, `/model-instances` endpoints (older surface). Some Postman collections + a few FE files still reference them.
- **`api_keys` is org-scoped; `model_providers`/`models`/`model_voices`/`model_languages` are global** (shared catalog).
- **`last_used` is not actually tracked**: column exists on `api_keys` but no code path writes to it.
- **⚠ No audit logging** on key creation/update/delete (high-impact security events).
- **⚠ RBAC**: `require_org_member` only — member can write/delete keys. Should be admin/owner.
- **⚠ No tests** for `/services/*` endpoints.
- **Label uniqueness pre-check**: service checks `(org_id, label)` uniqueness in Python before insert. Race condition under concurrent inserts (no DB-level unique constraint on label).
- **Postman drift**: no Postman folder for the new UUID-based `/services/*` surface — only the legacy parallel API.

## 4. Non-functional requirements

- **Multi-tenancy**: `api_keys` org-scoped via `organization_id` FK + `BaseService.query()`. Catalog tables (`model_providers`, `models`, `model_voices`, `model_languages`) are global.
- **AuthN**: `require_org_member` for org-scoped endpoints; admin/owner is expected on catalog mutations but ⚠ not enforced.
- **RBAC**: ⚠ weak — member can write/delete keys.
- **Encryption**: Fernet + PBKDF2 from `JWT_SECRET`. Static salt. ⚠ Hardening needed.
- **Performance**: batched lookup helpers in `model_provider_service.py` to avoid N+1.
- **Audit logging**: ⚠ none.
- **EE parity**: `ee/api/v1/services.py` mirrors with `require_ee_org_member`. Same service.

## 5. Test cases (as-built)

⚠ **No tests** for `/services/*` endpoints.

```
TEST: create_api_key
  GIVEN authenticated owner in org A
  WHEN  POST /services
        {"provider_id":1,"service_type":"llm","api_key":"sk-...","label":"OpenAI Prod"}
  THEN  201; api_keys row; encrypted_api_key set; last4 stored

TEST: create_api_key_default_unsets_previous
  GIVEN existing default LLM key in org A
  WHEN  POST /services with is_default=true for another LLM key
  THEN  previous default flipped to is_default=false in same transaction

TEST: create_with_source_key
  GIVEN existing OpenAI LLM key (id=K)
  WHEN  POST /services {"source_key_id":K,"service_type":"embeddings"}
  THEN  new row created sharing provider; encrypted_api_key copied; same label suffix

TEST: source_key_cross_provider_rejected
  GIVEN OpenAI key K; payload provider_id=Anthropic
  WHEN  POST /services {"source_key_id":K,"provider_id":Anthropic}
  THEN  400 "source key provider mismatch"

TEST: label_uniqueness_409
  GIVEN existing label "OpenAI Prod" in org A
  WHEN  POST /services {"label":"OpenAI Prod"}
  THEN  409 "Label already in use"

TEST: list_services_filter_by_type
  WHEN  POST /services/list {"service_type":"llm"}
  THEN  only LLM keys returned

TEST: catalog_listing
  WHEN  GET /services/providers/catalog
  THEN  array of {id, name, slug, supported_service_types, logo_url, ...}

TEST: tts_voices_filtered_by_language
  WHEN  GET /services/tts/voices?provider_id=elevenlabs&language_id=en
  THEN  voices marked supporting en

TEST: bulk_delete_provider
  GIVEN org A has 3 OpenAI keys (LLM, STT, embeddings)
  WHEN  DELETE /services/providers/{openai_id}
  THEN  all 3 rows deleted

TEST: delete_single
  WHEN  DELETE /services/{service_id}
  THEN  row deleted

TEST: cross_org
  GIVEN key K in org A; caller in org B
  WHEN  GET /services/{K.id}
  THEN  404
```

## 6. Data model / DB schema

**Table: `model_providers`** (catalog — global)

| Column                  | Type         | Null | Default     | Notes                                                  |
|-------------------------|--------------|------|-------------|--------------------------------------------------------|
| id                      | UUID         | NO   | `uuid4()`   | PK                                                     |
| name                    | VARCHAR(100) | NO   | —           | Display ("OpenAI")                                     |
| slug                    | VARCHAR(50)  | NO   | —           | Unique (`openai`)                                      |
| supported_service_types | ARRAY(TEXT)  | NO   | `{}`        | `["llm","stt","tts","embeddings"]`                     |
| logo_url                | VARCHAR(512) | YES  | —           |                                                        |
| documentation_url       | VARCHAR(512) | YES  | —           |                                                        |
| required_config         | JSONB        | YES  | `{}`        | Schema for required keys (`api_key`, etc.)             |
| is_active               | BOOL         | NO   | `true`      |                                                        |

**Table: `models`** (catalog — global)

| Column                | Type         | Null | Notes                                                |
|-----------------------|--------------|------|------------------------------------------------------|
| id                    | UUID         | NO   | PK                                                   |
| provider_id           | UUID         | NO   | FK → model_providers.id                              |
| name                  | VARCHAR(100) | NO   | Display ("GPT-4o")                                   |
| model_id              | VARCHAR(100) | NO   | API identifier ("gpt-4o-2024-08-06")                 |
| service_type          | VARCHAR(20)  | NO   | `llm` / `stt` / `tts` / `embeddings`                 |
| capabilities          | JSONB        | YES  | `{streaming, function_calling, ...}`                 |
| context_window        | INT          | YES  | LLM context size                                     |
| is_active             | BOOL         | NO   | true                                                 |

**Table: `model_voices`** (TTS voices — global)

| Column                | Type         | Null | Notes                                                |
|-----------------------|--------------|------|------------------------------------------------------|
| id                    | UUID         | NO   | PK                                                   |
| model_id              | UUID         | NO   | FK → models.id                                       |
| name                  | VARCHAR(100) | NO   | "Rachel"                                             |
| voice_id              | VARCHAR(100) | NO   | API identifier                                       |
| gender                | VARCHAR(20)  | YES  |                                                      |
| accent                | VARCHAR(50)  | YES  |                                                      |
| sample_url            | VARCHAR(512) | YES  | Preview audio                                        |

**Table: `model_languages`** (TTS/STT language catalog — global)

| Column                | Type         | Null | Notes                                                |
|-----------------------|--------------|------|------------------------------------------------------|
| id                    | UUID         | NO   | PK                                                   |
| model_id              | UUID         | NO   | FK → models.id                                       |
| language_code         | VARCHAR(10)  | NO   | "en", "es-MX"                                        |
| language_name         | VARCHAR(50)  | NO   | "English"                                            |

**Table: `api_keys`** (org-scoped credentials)

| Column                | Type         | Null | Notes                                                |
|-----------------------|--------------|------|------------------------------------------------------|
| id                    | UUID         | NO   | PK                                                   |
| organization_id       | UUID         | NO   | Multi-tenancy boundary                               |
| provider_id           | UUID         | NO   | FK → model_providers.id                              |
| service_type          | VARCHAR(20)  | YES  | `llm` / `stt` / `tts` / `embeddings` (NULL legacy)   |
| label                 | VARCHAR(100) | NO   | Per-org unique (app-level check) ⚠                   |
| encrypted_api_key     | TEXT         | NO   | Fernet-encrypted                                     |
| last4                 | VARCHAR(4)   | YES  | Last 4 chars for display                             |
| is_default            | BOOL         | NO   | Partial unique: at most one true per (org, service_type) |
| source_key_id         | UUID         | YES  | FK → api_keys.id (copied-from key)                   |
| last_used             | TIMESTAMPTZ  | YES  | ⚠ Never written                                      |
| created_at            | TIMESTAMPTZ  | NO   |                                                      |
| updated_at            | TIMESTAMPTZ  | NO   |                                                      |

**Indexes**:
- Partial unique `uq_api_keys_one_default_per_org_type` on `(organization_id, service_type) WHERE is_default = true AND service_type IS NOT NULL`.

**Migration**: seeded by `dev/seed.py` from `dev/dev-data.json` for provider/model catalog rows.

## 7. API design

All endpoints under prefix `/api/v1/services`. Auth: JWT bearer (`require_org_member`). RBAC: ⚠ none enforced.

### Org-scoped API keys

| Method | Path                                          | Purpose                                            |
|--------|-----------------------------------------------|----------------------------------------------------|
| POST   | `/services/list`                              | Paginated list of org's API keys                   |
| POST   | `/services`                                   | Create API key (201)                               |
| GET    | `/services/{service_id}`                      | Fetch one                                          |
| PATCH  | `/services/{service_id}`                      | Update label / is_default / metadata               |
| DELETE | `/services/{service_id}`                      | Delete one                                         |
| DELETE | `/services/providers/{provider_id}`           | Bulk delete all org's keys for a provider          |

### Catalog

| Method | Path                                                            | Purpose                                       |
|--------|-----------------------------------------------------------------|-----------------------------------------------|
| GET    | `/services/providers/catalog`                                   | List all supported providers                  |
| POST   | `/services/providers/{provider_id}/keys`                        | List API keys for a provider in this org      |
| POST   | `/services/providers/{provider_id}/models`                      | List models for a provider                    |
| POST   | `/services/providers/{provider_id}/models` (with body)          | Create a model (catalog admin)                |
| PATCH  | `/services/providers/{provider_id}/models/{model_id}`           | Update a model                                |
| DELETE | `/services/providers/{provider_id}/models/{model_id}`           | Delete a model                                |

### TTS catalog

| Method | Path                                              | Purpose                                       |
|--------|---------------------------------------------------|-----------------------------------------------|
| GET    | `/services/tts/providers`                         | List TTS providers                            |
| GET    | `/services/tts/languages?provider_id=...`         | List languages for a TTS provider             |
| GET    | `/services/tts/voices?provider_id=...&language_id=...` | List voices filtered                     |

### POST /services

```json
{
  "provider_id": "uuid-openai",
  "service_type": "llm",
  "api_key": "sk-...",
  "label": "OpenAI Prod",
  "is_default": true,
  "source_key_id": null
}
```

### Response

```json
{
  "id": "uuid", "organization_id": "uuid", "provider_id": "uuid-openai",
  "service_type": "llm", "label": "OpenAI Prod", "last4": "abcd",
  "is_default": true, "source_key_id": null,
  "created_at": "...", "updated_at": "..."
}
```

(API key is **never** returned in the response — only `last4`.)

### Referenced but not present

- ⚠ Legacy parallel API: `/model-providers-menu`, `/model-menu`, `/model-instances`. Some Postman collections + FE files reference. Drift risk.
- ⚠ No `POST /services/{id}/test_connection` health check.
- ⚠ No way to rotate the encryption key without invalidating every row.

## 8. Backend implementation

- **Controller**: `core/api/v1/services.py` — ~15 routes covering org keys + catalog + TTS catalog.
- **EE Controller**: `ee/api/v1/services.py` — mirrors.
- **Service**: `core/services/model_provider_service.py` (898 lines)
  - Encryption helpers (Fernet/PBKDF2 derived from `settings.JWT_SECRET`).
  - Batched lookup helpers to avoid N+1 in agent reads.
  - Default-flag invariant maintained in a single transaction.
- **Models**: `core/models/{model_provider,model,model_voice,model_language,api_key}.py`.
- **Seed**: `dev/seed.py` reads `dev/dev-data.json` (catalog rows).
- **Encryption**: `core/utils/encryption.py` (or co-located in service).
- **No audit logging.**

## 9. Frontend implementation

- **Route**: `/model-providers` — `frontend/src/app/(dashboard)/model-providers/` (3 page.tsx files: list + per-provider drill-down + admin edit).
- **API services**:
  - `frontend/src/services/servicesService.ts` — main `/services/*` wrappers.
  - `frontend/src/services/ttsService.ts` — TTS catalog.
  - `frontend/src/services/providerService.ts` ⚠ legacy.
  - `frontend/src/services/voiceService.ts` ⚠ legacy.
- **Layout**: drawer (chosen by field count — provider picker + api_key field + label + is_default toggle is small).
- **State**: Jotai atoms.
- **Components**: provider catalog grid, "Add credential" drawer, per-provider key list, per-provider model catalog (admin), TTS voice browser with filters.

## 10. Postman collection & examples

Multiple collections cover overlapping surfaces. ⚠ No clear Postman folder for the new UUID `/services/*` surface — the existing collections are mostly legacy:
- `service_providers.postman_collection.json` ⚠ legacy
- `model_providers_menu.postman_collection.json` ⚠ legacy
- `models.postman_collection.json` ⚠ legacy
- `voices.postman_collection.json` ⚠ legacy
- `model_menu.postman_collection.json` ⚠ legacy
- `model_instances.postman_collection.json` ⚠ legacy
- `hosting_providers.postman_collection.json` ⚠ legacy

### POST /api/v1/services

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"provider_id":"uuid-openai","service_type":"llm","api_key":"sk-...","label":"OpenAI Prod","is_default":true}' \
  "$BASE_URL/api/v1/services"
```

### POST /api/v1/services/list

```json
{"page": 1, "page_size": 20, "service_type": "llm"}
```

### GET /api/v1/services/providers/catalog

```json
[
  {"id":"uuid","name":"OpenAI","slug":"openai","supported_service_types":["llm","embeddings"],"logo_url":"..."},
  {"id":"uuid","name":"ElevenLabs","slug":"elevenlabs","supported_service_types":["tts"],"logo_url":"..."},
  ...
]
```

### GET /api/v1/services/tts/voices?provider_id=...&language_id=...

```json
[
  {"id":"uuid","name":"Rachel","voice_id":"21m00Tcm4TlvDq8ikWAM","gender":"female","accent":"American","sample_url":"..."}
]
```

### DELETE /api/v1/services/providers/{provider_id} — bulk

```json
{"message": "Deleted 3 API keys for provider"}
```

## 11. Next steps

- [ ] ⚠ **Tighten RBAC**: only owner/admin should create/delete API keys.
- [ ] ⚠ **Add audit log** entries for create/update/delete of API keys.
- [ ] ⚠ **Write `last_used` on first call** so the column is real (and "unused key" cleanup becomes possible).
- [ ] ⚠ **Harden encryption**: per-row random salt, separate `ENCRYPTION_KEY` setting (not `JWT_SECRET`), support for KMS rotation.
- [ ] ⚠ **Add FKs** from `agent_configs` to `models`, `model_providers`, `model_voices`, `model_languages` (currently bare INT columns).
- [ ] ⚠ **Deprecate legacy parallel API** (`/model-providers-menu`, `/model-menu`, `/model-instances`); remove FE references in `providerService.ts` / `voiceService.ts`.
- [ ] ⚠ **Add tests** under `tests/test_services.py`.
- [ ] **Add a Postman folder** for the new UUID `/services/*` surface.
- [ ] **Add `POST /services/{id}/test_connection`** to probe the provider with the stored credential.
- [ ] **Page-regen helper**: run `/card_page` against `services` to refresh the catalog frontend.
- [ ] **Document encryption-key rotation** procedure (today: rotating invalidates all keys).

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) ⚠ `JWT_SECRET` doubles as encryption master key — rotation invalidates all keys; (2) Static salt in PBKDF2; (3) No audit logging on API-key CRUD; (4) `require_org_member` only — member can write/delete keys; (5) Missing FK from `agent_configs` to `models`/etc.; (6) Legacy parallel API (`/model-providers-menu`, etc.) drifting alongside new `/services/*`; (7) `last_used` column declared but never written; (8) No Postman folder for the new UUID surface — only legacy collections; (9) No tests; (10) Label uniqueness is application-level pre-check, not DB-level constraint — race condition possible.
