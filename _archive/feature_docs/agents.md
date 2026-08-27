# Agents — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

An **Agent** is the core entity of the Tone platform — an AI voice assistant built on top of a configurable Pipecat pipeline (LLM ↔ STT ↔ TTS). Each agent belongs to exactly one organization and carries the full set of behaviors needed to run a voice or chat session: a name, an `agent_type` (`inbound` | `outbound` | `both`), a published [[agent-configs]] version (system prompt, language, llm/voice/stt settings), attached [[tools]], [[mcp-servers]], a [[knowledge-base]] (uploads), and a list of [[phone_numbers]] bound to channels.

Agents are the **parent entity** for almost everything else in the product: agent configs, phone numbers, knowledge-base uploads, MCP server bindings, tool bindings, call logs, and channels all hang off an agent.

- **Target users**: org admins and agent owners (the people who configure the voice agent's behavior) and operators (who attach phone numbers, monitor calls, and tweak prompts).
- **Problem solved**: gives each customer a stable, multi-tenant container for one voice agent — with the pipeline config, telephony bindings, knowledge, and tool surface area all attached.

## 2. User stories & use cases

- As an **org admin**, I want to create a new agent (pick `inbound` or `outbound`) so I can start configuring a voice assistant.
- As an **agent owner**, I want to update an agent's prompt, language, LLM/voice/STT settings, and attached tools so I can iterate on its behavior without losing config history (each save bumps an [[agent-configs]] `version`).
- As an **operator**, I want to attach a phone number and a [[channel]] to an agent so inbound calls route to its pipeline.
- As an **operator**, I want to browse all agents in my org (with search, agent-type filter, and pagination) so I can pick one to edit or test.
- As an **agent owner**, I want to delete an agent and have all child rows (config, phone numbers, tool/MCP/KB junctions) cleaned up in one transaction.
- As a **frontend client**, I want a lightweight `get_all_agents` endpoint for dropdowns that returns only `{id, uuid, name}` per row.

Typical flow: Admin → `/agents` → "Create Agent" modal → pick `inbound`/`outbound` → lands on `/agents/edit/{type}/{id}` → fills prompt + voice + tools + phone numbers.

## 3. Functional requirements

- **CRUD** on agents scoped to the caller's organization (resolved from `JWTClaims.org_id`, falls back to `settings.DEFAULT_ORG_ID` in single-tenant Core).
- **List endpoint** (`POST /agent/list`) supports server-side **search** (case-insensitive ILIKE on `name` OR `description`), **sort** (`name`, `agent_type`, `is_active`, `created_at`, `updated_at`; ascending or `-` prefix for descending), **agent_type filter** (`inbound` | `outbound` | `both`), **`is_active` tri-state filter**, and **pagination** (`page`, `page_size`).
- **Enriched listing**: each returned row carries a `phone_number[]` array (`{type, no}`) batch-fetched in a single SQL round-trip (`_phone_numbers_for` helper joins `phone_numbers` → `channels`).
- **Dropdown endpoint** `GET /agent/get_all_agents` returns a flat `[{id, uuid, name}]` array, ordered by `name ASC`, scoped to non-deleted agents — for use in selects/typeaheads.
- **Create / update** accept a nested `config` object that drives the [[agent-configs]] row (versioned), plus three many-to-many sync arrays — `tool_ids[]`, `mcp_server_ids[]`, `upload_ids[]` — and a `phone_numbers[]` array (each `{number, channel_id, label?}`).
- **Versioned config**: `_upsert_new_config` mutates the latest non-deleted `agent_config` row in place when one exists (no version bump), or creates `version=1` for a brand-new agent. The agent's `published_config_id` always points to that row.
- **Hard delete** (not soft delete): `DELETE /agent/delete_agent` cascades through `phone_numbers`, `agent_tools`, `agent_mcp_servers`, `agent_knowledge_base`, `agent_configs`, then deletes the `agents` row itself. ⚠ Inconsistent with `Agent.deleted_at` column which exists but is never written.
- **Audit logging**: ⚠ Not wired. Unlike most resources, agent CRUD does not call `AuditService`. Service-layer try/except blocks rollback on `IntegrityError` and surface a friendly `agent_name_unique` message (HTTP 409) but never emit an audit event.
- **EE parity**: `ee/api/v1/agents.py` re-uses the Core `CreateAgentRequest` / `UpdateAgentRequest` Pydantic models and the shared `list_agents_for_org` helper. Only the auth dependency differs (`require_ee_org_member` vs `require_org_member`).

### Edge cases & failure modes

- Empty list: response is `{items: [], total: 0, page, page_size}` — never null.
- `page_size` is clamped to `1..100`; `page` is clamped to `>=1`.
- Unknown `sort_by` value silently falls back to `updated_at DESC` (no error). The validated whitelist is `ALLOWED_SORT_FIELDS = {"name", "agent_type", "is_active", "created_at", "updated_at"}`.
- `is_active` is **tri-state** — `true`, `false`, or omitted (no filter). Passing `null` is treated as omitted.
- Cross-org access: GET/PUT/DELETE on an agent owned by a different org returns **404** ("Agent not found") — leaks no information about existence. Enforced by `query(Agent).filter(Agent.id == aid, Agent.deleted_at.is_(None))` scoped by `self.org_id` via `BaseService`.
- Duplicate name within same org: `UniqueConstraint("organization_id", "name", name="uq_agents_org_name")` raises `IntegrityError` → caught and returned as **HTTP 409** with `"An agent with this name already exists."`
- Concurrent deletes are NOT idempotent — second `delete_agent` raises 404 because `get_agent` is called first.
- Attaching a phone number already assigned to a **different** agent → **HTTP 409** `"Phone number {number} is already assigned to another agent"`. Same number on same agent is a no-op reassign.
- Attaching MCP servers or knowledge-base uploads without an existing `agent_config` → **HTTP 400** `"Agent config required to attach MCP servers"` / `"... knowledge base documents"`. Tool attachments do NOT require a config (they store `agent_config_id = NULL`).
- Tool / MCP / Upload IDs that don't exist → **HTTP 400** `"Tools not found: <comma-list>"` etc. — pre-validated against the respective tables before junction writes.
- `search` matches **both `name` AND `description`** (unlike tone-test where only `name` matches). Implemented as `or_(Agent.name.ilike(like), Agent.description.ilike(like))`.
- Phone-number sync is a **declarative replace** — numbers in the incoming list are kept/created; any number currently assigned to this agent but NOT in the list is **deleted** (not just unlinked). Re-creating it later requires reissuing it via the provider channel.
- ⚠ **Hard delete vs `deleted_at` mismatch**: the `Agent` model declares `deleted_at = Column(DateTime(timezone=True), nullable=True)` and read-paths filter on `deleted_at.is_(None)`, but `delete_agent` actually issues `self.db.delete(agent)` — a row-level delete. The `deleted_at` column is dead today.
- ⚠ **Dead service code**: `agent_service.py` still contains `upsert_agent`, `_agent_response_item`, `duplicate_agent`, `_normalize_agent_type`, `_build_agent_config_data` which reference removed models (`ServiceProvider`, `Account`, `ModelInstance`, `AgentChannel`, `AgentChannelPhoneNumbers`, `AgentType` enum). The file's top-of-file comment flags this — calling them will `NameError`. They are no longer wired to any HTTP route but the Postman collection still lists `upsert_agent` and `duplicate_agent`.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced on every query via `organization_id` filter. `BaseService.query()` automatically scopes to `self.org_id`; raw `db.query(...)` calls in the controller add `.filter(Agent.organization_id == org_id)` explicitly.
- **AuthN**: `Depends(require_org_member)` (Core) / `Depends(require_ee_org_member)` (EE) — JWT bearer required, must include `org_id`. No API-key auth path on this router.
- **RBAC**: ⚠ **Not enforced.** Any authenticated org member can create/update/delete any agent in the org. There is no `require_admin_or_owner` guard, no per-action role check, and no resource-owner check on `created_by_user_id`.
- **Performance**: list endpoint runs **2 queries** total — paginated `list_records(...)` + one batched `_phone_numbers_for` query joining `phone_numbers` to `channels`. Linear in returned rows per page (max 100). No FTS index on `name`/`description` — ILIKE scans could degrade on very large orgs.
- **Atomicity**: create / update / delete use a single SQLAlchemy session with `db.flush()` + `db.commit()`; on any exception the entire transaction rolls back. `delete_agent` issues 5 cascaded `DELETE`s + 1 row delete in one transaction.
- **Observability**: ⚠ No structured logging, no metrics, no audit log entry. Errors surface as `traceback.format_exc()` printed to stdout (legacy `upsert_agent` only) — should migrate to the project's logging pattern.

## 5. Test cases (as-built)

⚠ **No dedicated pytest suite exists for the agents endpoints in this repo.** The codebase has e2e Playwright specs under `frontend/e2e/` but no `backend/tests/test_*_agents.py` equivalent. The cases below are the behaviors the controller + service currently exercise and should be the locked-in spec when tests are added.

```
TEST: create_agent_minimal
  GIVEN authenticated user in org A
  WHEN  POST /agent/create_agent with body {"name": "Acme Bot", "agent_type": "inbound"}
  THEN  201; response has id, agent_type="inbound", is_active=true,
        created_by_user_id set, config=null, tools=[], mcp_servers=[],
        documents=[], phone_numbers=[]

TEST: create_agent_full
  GIVEN authenticated user
  WHEN  POST /agent/create_agent with name, agent_type, description, config{...},
        tool_ids[], mcp_server_ids[], upload_ids[], phone_numbers[]
  THEN  201; agent.published_config_id set to new agent_config.id (version=1);
        tools/mcp/kb junction rows created; phone_numbers reassigned to this agent

TEST: create_agent_duplicate_name
  GIVEN agent "Sales" already exists in org A
  WHEN  POST /agent/create_agent with {"name": "Sales", "agent_type": "inbound"}
  THEN  409; detail = "An agent with this name already exists."

TEST: list_agents_pagination
  GIVEN 25 agents in org A
  WHEN  POST /agent/list with {"page": 2, "page_size": 10}
  THEN  items.length == 10, total == 25, page == 2, page_size == 10

TEST: list_agents_search
  GIVEN agents named "Acme Bot", "AcmeBot Pro", "Other" in org A
  WHEN  POST /agent/list with {"search": "acme"}
  THEN  returns only "Acme Bot" and "AcmeBot Pro" (case-insensitive)

TEST: list_agents_agent_type_filter
  WHEN  POST /agent/list with {"agent_type": "outbound"}
  THEN  returns only agents with agent_type == "outbound"

TEST: list_agents_is_active_filter
  WHEN  POST /agent/list with {"is_active": false}
  THEN  returns only inactive agents

TEST: list_agents_invalid_sort
  WHEN  POST /agent/list with {"sort_by": "bogus_field"}
  THEN  200; falls back to updated_at DESC (no error)

TEST: list_agents_phone_enrichment
  GIVEN agent X with phone "+15551234567" attached to a SIP channel
  WHEN  POST /agent/list
  THEN  the row for X has phone_number == [{"type": "sip", "no": "+15551234567"}]

TEST: get_agent_cross_org
  GIVEN agent X in org A, user in org B
  WHEN  GET /agent/get_agent?agent_id={X.id} as user from org B
  THEN  404 "Agent not found"

TEST: update_agent_partial
  WHEN  PUT /agent/update_agent?agent_id={id} with {"description": "new"}
  THEN  200; only description changes; tools/mcp/uploads/phones untouched (None == omit)

TEST: update_agent_replace_tools
  GIVEN agent with tools [A, B]
  WHEN  PUT /agent/update_agent?agent_id={id} with {"tool_ids": ["B", "C"]}
  THEN  200; AgentTool rows for A deleted, C inserted, B kept

TEST: update_agent_attach_phone_already_assigned
  GIVEN phone "+15550001111" assigned to agent Y in same org
  WHEN  PUT /agent/update_agent?agent_id={X.id} with phone_numbers=[{number, channel_id}]
  THEN  409 "Phone number +15550001111 is already assigned to another agent"

TEST: delete_agent_cascades
  GIVEN agent X with config, 2 tools, 1 mcp server, 3 uploads, 2 phone numbers
  WHEN  DELETE /agent/delete_agent?agent_id={X.id}
  THEN  200 {"message":"Agent deleted successfully"};
        all child rows removed; subsequent GET returns 404
```

## 6. Data model / DB schema

**Table: `agents`**

| Column                | Type             | Null | Default     | Notes                                                |
|-----------------------|------------------|------|-------------|------------------------------------------------------|
| id                    | UUID             | NO   | `uuid4()`   | PK                                                   |
| organization_id       | UUID             | NO   | from ctx    | Indexed; multi-tenancy boundary                      |
| name                  | VARCHAR(50)      | NO   | —           | Unique within org (`uq_agents_org_name`)             |
| description           | VARCHAR(200)     | YES  | —           |                                                      |
| agent_type            | VARCHAR(20)      | NO   | —           | `inbound` \| `outbound` \| `both` (string, not enum) |
| llm_model             | VARCHAR          | YES  | —           | ⚠ Read in `agent_response` but never written         |
| published_config_id   | UUID             | YES  | —           | FK → `agent_configs.id` (`ON DELETE SET NULL`, `use_alter=True`) |
| created_by_user_id    | UUID             | NO   | —           | FK → `users.id`                                      |
| is_active             | BOOL             | NO   | `true`      |                                                      |
| deleted_at            | TIMESTAMPTZ      | YES  | —           | ⚠ Declared but never written — see §3                |
| archived_at           | TIMESTAMPTZ      | YES  | —           | ⚠ Declared but never written                         |
| created_at            | TIMESTAMPTZ      | NO   | `now()`     |                                                      |
| updated_at            | TIMESTAMPTZ      | NO   | `now()`     | Auto-updates on row change                           |

**Indexes**
- Implicit B-tree on `organization_id` (declared `index=True` in `OrgScopedModel`).
- Unique composite index on `(organization_id, name)` via `uq_agents_org_name`.

**Relationships** (FKs declared on the child side):
- `agent_configs.agent_id → agents.id` (`ON DELETE CASCADE`) — see [[agent-configs]]
- `agents.published_config_id → agent_configs.id` (`ON DELETE SET NULL`, deferred via `use_alter=True` to break the cycle)
- `phone_numbers.agent_id → agents.id` (`ON DELETE SET NULL`)
- `agent_tools.agent_id → agents.id`
- `agent_mcp_servers.agent_id → agents.id`
- `agent_knowledge_base.agent_id → agents.id`

**Companion table: `agent_configs`** (see [[agent-configs]] for the full PRD)
- `(agent_id, version)` unique. Holds `first_message`, `system_prompt_template`, `conversation_history_token_limit`, `language_id` → `model_languages`, `knowledge_model_id` → `models`, and four JSONB blobs: `llm_settings`, `voice_settings`, `stt_settings`, `conversation_settings`.

**Migration notes**: Standard pattern — UUID PK, org_id default from `TenantContext`, no soft-delete write path today.

## 7. API design

All endpoints under prefix `/api/v1/agent` (router prefix `/agent` + global v1 prefix). Note the singular `/agent` — not `/agents`. Auth: JWT bearer, any authenticated org member. RBAC: ⚠ currently none enforced.

### Implemented

| Method | Path                              | Purpose                                            |
|--------|-----------------------------------|----------------------------------------------------|
| GET    | `/agent/get_all_agents`           | Dropdown — flat `[{id, uuid, name}]`, ordered      |
| POST   | `/agent/create_agent`             | Create agent + optional config + attachments (201) |
| GET    | `/agent/get_agent?agent_id=...`   | Fetch one (full response with config + relations)  |
| PUT    | `/agent/update_agent?agent_id=...`| Partial update (`exclude_unset=True`)              |
| DELETE | `/agent/delete_agent?agent_id=...`| Hard delete + cascade (200, `{"message": "..."}`)  |
| POST   | `/agent/list`                     | Paginated list with search/sort/filter             |

EE router (`ee/api/v1/agents.py`) mounts the **same six routes** at the same path with `require_ee_org_member` auth. In `main.py`, EE is registered first and Core is registered second under the same `/agent` prefix.

**List request shape**:
```json
{"page": 1, "page_size": 20, "search": "acme", "sort_by": "-updated_at", "is_active": true, "agent_type": "inbound"}
```

**List response shape** (from `_serialize_agent`):
```json
{
  "items": [{"id": "uuid", "uuid": "uuid", "name": "...", "description": "...", "agent_type": "inbound", "is_active": true, "phone_number": [{"type": "sip", "no": "+15551234567"}], "created_at": 1716800000.0, "updated_at": 1716800500.0}],
  "total": 42, "page": 1, "page_size": 20
}
```

**Full create/get response shape** (from `agent_service.agent_response`):
```json
{
  "id": "uuid", "name": "...", "description": "...", "agent_type": "inbound", "llm_model": null, "is_active": true,
  "created_by_user_id": "uuid", "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00",
  "config": {"id": "uuid", "version": 1, "first_message": "...", "system_prompt_template": "...", "language_id": "uuid", "llm_settings": {}, "voice_settings": {}, "stt_settings": {}, "conversation_settings": {}},
  "tools": [{"id": "uuid", "name": "..."}],
  "mcp_servers": [{"id": "uuid", "name": "..."}],
  "documents": [{"id": "uuid", "file_path": "...", "file_name": "..."}],
  "phone_numbers": [{"id": "uuid", "number": "+15551234567", "channel_id": "uuid", "label": "..."}]
}
```

### ⚠ Referenced but NOT implemented (stale Postman entries)

`postman_collection/agents.postman_collection.json` still lists routes the controller no longer exposes:

- `POST   /agent/upsert_agent` — replaced by `create_agent` + `update_agent`. The service method `upsert_agent` still exists but is dead code (references removed models).
- `POST   /agent/duplicate_agent` — service method `duplicate_agent` exists but no HTTP handler wires it.

The Postman collection's `Get All Agents` example also shows the legacy response shape (integer `id`, `status`, `meta_data`, ISO `created_at`) which no longer matches the actual `[{id, uuid, name}]` response.

## 8. Backend implementation

- **Controller**: `core/api/v1/agents.py`
  - Routes: `get_all_agents`, `create_agent`, `get_agent`, `update_agent`, `delete_agent`, `list_agents`
  - Pydantic models: `AgentConfigRequest`, `PhoneNumberAttachment`, `CreateAgentRequest`, `UpdateAgentRequest`
  - Helpers: `_get_service`, `_phone_numbers_for`, `_serialize_agent`, `list_agents_for_org` — the last three are **shared with EE** by direct import.
- **EE Controller**: `ee/api/v1/agents.py` — re-exports Core's Pydantic models, swaps auth dep, calls into the same `AgentService` and `list_agents_for_org`.
- **Service**: `core/services/agent_service.py` (`AgentService(BaseService)`)
  - Wired methods: `create_agent`, `update_agent`, `get_agent`, `delete_agent`, `agent_response`
  - Internal helpers: `_apply_attachments`, `_upsert_new_config`, `_sync_tools`, `_sync_mcp_servers`, `_sync_knowledge_base`, `_sync_phone_numbers`
  - ⚠ Dead code: `upsert_agent`, `_agent_response_item`, `duplicate_agent`, `_normalize_agent_type`, `_normalize_agent_value`, `_build_agent_config_data`, the `AGENT_METADATA_KEYS` constant
- **Models**: `core/models/agent.py` (`Agent`), `core/models/agent_config.py` (`AgentConfig`), `core/models/phone_number.py` (`PhoneNumber`), plus three junctions: `agent_tool.py`, `agent_mcp_server.py`, `agent_knowledge_base.py`
- **No CRUD helpers** beyond `list_records` (used in `list_agents_for_org`). Create/update/delete are hand-rolled with direct SQLAlchemy.
- **No audit logging, no Celery tasks, no background jobs.**
- **Pipeline runtime consumers**: `core/bot.py` (`run_bot`) and `core/services/agent_factory_service.py` read agent + agent_config rows at call-start to instantiate the Pipecat pipeline (LLM/STT/TTS services, decrypted provider API keys from `accounts`). See [[voice-pipeline]].

## 9. Frontend implementation

- **Routes** (under `frontend/src/app/(dashboard)/agents/`):
  - `/agents` — `page.tsx` → renders `AgentListPage` (list view).
  - `/agents/create/inbound` — `create/inbound/page.tsx` — full-page create form for inbound agents.
  - `/agents/create/outbound` — `create/outbound/page.tsx` — full-page create form for outbound agents.
  - `/agents/edit/[type]/[id]` — dynamic route handling edit for any `agent_type`.
  - No standalone `/agents/[id]` detail view — edit is the detail view.
- **Page components** (`frontend/src/components/agents/`):
  - `AgentListPage.tsx` — list with `CustomTable`, `SearchBar`, agent-type `SelectInput`, page-size selector, `AgentActionMenu` (edit/delete), `CreateAgentModal`.
  - `CreateAgentModal.tsx` — modal that asks `inbound` vs `outbound` then routes to the right `/agents/create/{type}` page.
  - `AgentFormPage.tsx` — wraps create/edit pages with `FormProvider`. Loads agent data in edit mode and uses `AgentFormState` from `agent-form/agentFormUtils.ts`.
  - `agent-form/` — sub-folder with `GeneralTab`, `VoiceTab`, `CallConfigurationTab`, `PromptPage`, `DynamicProviderFields.tsx`, `agentFormUtils.ts` (form-state shape + `formStateToUpsertPayload` serializer).
  - `AgentActionMenu.tsx`, `AgentTypeBadge.tsx` — row action menu and the inbound/outbound badge.
- **API service** (`frontend/src/services/agentsService.ts`):
  - `listAgents(params)` → `POST /agent/list`
  - `getAllAgents()` → `GET /agent/get_all_agents`
  - `getAgent(id)` → `GET /agent/get_agent?agent_id=...`
  - `createAgent(payload)` → `POST /agent/create_agent`
  - `updateAgent(id, payload)` → `PUT /agent/update_agent?agent_id=...`
  - `deleteAgent(id)` → `DELETE /agent/delete_agent?agent_id=...`
- **State** (`frontend/src/atoms/AgentsAtom.tsx`): `paginatedAgentsAtom`, `fetchPaginatedAgentList` (write atom), `deleteAgentAtom`. The list page calls `fetchPaginatedAgentList` with params derived from local state and refetches whenever `page`, `pageSize`, `search`, `sortBy`, or `agentTypeFilter` changes.
- **Layout mode for forms**: **page** (full route `/agents/create/{type}` and `/agents/edit/{type}/{id}`), not modal/drawer. The agent form has ~20+ fields spread across four tabs — page is the right choice. The only modal is `CreateAgentModal` which is just a type-picker, not the actual form.
- **Listing**: `CustomTable` (TanStack React Table) with `CustomTableColumn` definitions. Columns include: name + description, `AgentTypeBadge`, `PhoneNumberDisplay` (renders the `phone_number[]` array from the list response), `is_active` badge, `formatDate(updated_at)`, row actions (edit, delete).
- **Filter / sort UX**: server-side everywhere. `sortBy` is encoded as `"-field"` for desc, `"field"` for asc. Agent-type filter defaults to `"all"` (sent as `undefined`).
- **Page-size options**: `[10, 25, 50, 100]` (matches backend clamp upper bound).
- **Toasts**: `showToast.success` / `showToast.error` from `@/utils/toast`. API errors caught by `handleApiError` which extracts `error.response.data.detail`.
- **Constants**: `AGENT_TYPE_OPTIONS` from `@/lib/constants/filters` (`all`, `inbound`, `outbound`).

## 10. Postman collection & examples

Located in `postman_collection/agents.postman_collection.json` under the **"Agent API"** collection. ⚠ The collection is **stale** (see §7) — `upsert_agent` and `duplicate_agent` are listed but no longer routable, and example bodies use the legacy `status` / `meta_data` shape. The collection should be regenerated via `/postman` after this PRD is reviewed.

### POST /api/v1/agent/create_agent — Create

**Request body**
```json
{
  "name": "Acme Support Bot",
  "description": "Tier-1 support assistant for Acme",
  "agent_type": "inbound",
  "is_active": true,
  "config": {
    "first_message": "Hi, this is Acme Support — how can I help?",
    "system_prompt_template": "You are a helpful support agent...",
    "conversation_history_token_limit": 4000,
    "language_id": "550e8400-e29b-41d4-a716-446655440aaa",
    "knowledge_model_id": "550e8400-e29b-41d4-a716-446655440bbb",
    "llm_settings": {"provider": "openai", "model": "gpt-4o"},
    "voice_settings": {"provider": "elevenlabs", "voice_id": "21m00Tcm4TlvDq8ikWAM"},
    "stt_settings": {"provider": "deepgram", "model": "nova-2"},
    "conversation_settings": {"interruption_handling": "polite"}
  },
  "tool_ids": ["uuid-1", "uuid-2"],
  "mcp_server_ids": ["uuid-3"],
  "upload_ids": ["uuid-4"],
  "phone_numbers": [{"number": "+15551234567", "channel_id": "uuid-channel", "label": "Main line"}]
}
```

**Response 201** — see §7 "Full create/get response shape"

**curl**
```bash
curl -X POST "$BASE_URL/api/v1/agent/create_agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Support Bot","agent_type":"inbound"}'
```

### POST /api/v1/agent/list — List

**Request body**
```json
{"page": 1, "page_size": 20, "search": "acme", "sort_by": "-updated_at", "is_active": true, "agent_type": "inbound"}
```

**Response 200**
```json
{
  "items": [{"id": "uuid", "uuid": "uuid", "name": "Acme Support Bot", "description": "Tier-1 support assistant for Acme", "agent_type": "inbound", "is_active": true, "phone_number": [{"type": "sip", "no": "+15551234567"}], "created_at": 1716800000.0, "updated_at": 1716800500.0}],
  "total": 1, "page": 1, "page_size": 20
}
```

### GET /api/v1/agent/get_all_agents — Dropdown

```bash
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/agent/get_all_agents"
```

```json
[{"id": "uuid-1", "uuid": "uuid-1", "name": "Acme Support Bot"}, {"id": "uuid-2", "uuid": "uuid-2", "name": "Sales Bot"}]
```

### PUT /api/v1/agent/update_agent?agent_id={id}

```json
{"name": "Acme Support Bot v2", "config": {"system_prompt_template": "Updated prompt..."}, "tool_ids": ["uuid-1", "uuid-2", "uuid-5"]}
```

Behavior: only fields present in the body are touched. `tool_ids` is a full replacement — pass the full desired set, not just additions. Same rule for `mcp_server_ids`, `upload_ids`, `phone_numbers`.

### DELETE /api/v1/agent/delete_agent?agent_id={id}

`200 OK` with `{"message": "Agent deleted successfully"}`. Hard delete — cascades through phone numbers, tool/MCP/KB junctions, and the agent_config row.

## 11. Next steps

This feature is **already built**. Use the items below when modifying it or filling in the gaps flagged above.

- [ ] ⚠ **Add RBAC**: wrap controller endpoints with role/permission checks (e.g. `require_admin_or_owner` for create/update/delete, `require_org_member` for read-only). Today any org member can mutate any agent.
- [ ] ⚠ **Decide soft vs hard delete**: either start writing `deleted_at` in `delete_agent` (and switch the cascade to `is_active=false` for related junctions) OR drop the `deleted_at` / `archived_at` columns. Same applies to `agent_configs`.
- [ ] ⚠ **Wire audit logging**: agent CRUD is one of the highest-impact mutations in the product but emits no audit events. Add `AuditService` calls on create/update/delete.
- [ ] ⚠ **Delete dead service code**: remove `upsert_agent`, `duplicate_agent`, `_agent_response_item`, `_normalize_agent_type`, `_normalize_agent_value`, `_build_agent_config_data`, and the `AGENT_METADATA_KEYS` constant from `agent_service.py`. They reference removed models and will `NameError` if invoked.
- [ ] ⚠ **Regenerate Postman collection**: drop `upsert_agent` / `duplicate_agent` entries, refresh example payloads to match the current Pydantic schemas, add `create_agent` / `update_agent` / `list` entries. Run `/postman`.
- [ ] **Add backend test coverage**: there is no `tests/test_*_agents.py`. The §5 cases should become pytest tests against an in-memory SQLite or Postgres test DB.
- [ ] **Add a DB index on `agents.name` (and `description`)** if list search performance degrades. Consider a `pg_trgm` GIN index for ILIKE.
- [ ] If regenerating the listing page: run `/table_page` with entity `agent`.
- [ ] If regenerating the create/edit form: run `/form_page` with layout `page` and entity `agent`.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) RBAC missing on controller; (2) `delete_agent` hard-deletes despite `deleted_at` column existing; (3) `upsert_agent` / `duplicate_agent` are dead service methods still referenced in Postman; (4) no audit logging on agent CRUD; (5) no backend pytest suite for agents.
