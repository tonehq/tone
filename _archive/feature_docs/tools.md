# Tools — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

A **Tool** is a function-calling capability that an agent can invoke during a voice conversation — e.g., a webhook tool that POSTs to an external URL, a built-in `send_sms` tool, or a Google Calendar tool that books a meeting. Tools live in the `tools` table and are attached to agents via `agent_tools`. The pipeline ([[voice-pipeline]]) loads attached tools at call boot and registers them as Pipecat function-call schemas; when the LLM calls one, `core/services/custom_tool_service.py` dispatches to the right handler (HTTP webhook, SMS, OAuth-backed API, etc.).

Tools are distinct from [[mcp-servers]] (external MCP tool servers). Tools are **internally defined** in Tone; MCP servers are external.

- **Target users**: agent owners (define and attach tools), org admins (manage template tools).
- **Problem solved**: a unified function-call surface for agents that handles credential storage, request templating, OAuth integration, and per-agent overrides.

Cross-links: [[agents]] (many-to-many via `agent_tools`), [[oauth-integrations]] (tools may reference OAuth connections), [[knowledge-base]] (separate `read_document` tool registered dynamically — not in this table), [[voice-pipeline]].

## 2. User stories & use cases

- As an agent owner, I want to create a custom webhook tool ("post_to_crm") that the agent can call mid-call.
- As an agent owner, I want to pick from a list of template tools (send_sms, google_calendar) without authoring the schema.
- As an agent owner, I want to attach a tool to multiple agents at once.
- As an admin, I want to update a tool's URL/auth and have all agents using it pick up the change.
- As a tester, I want to delete a tool I'm no longer using.

Typical flow: Owner → `/tools` → "Create Tool" → fills name + description + URL + method + JSON schema (or picks a template) → saves → in [[agents]] edit form, attaches to one or more agents.

## 3. Functional requirements

- **CRUD** (`create_tool`, `update_tool`, `delete_tool`, `get_tool`, `upsert_tool`).
- **Listing** (`POST /tool/list` with pagination/sort/filter, `GET /tool/get_all_tools` for dropdowns).
- **Templates** (`GET /tool/get_template_tools`): returns the catalog of pre-built tool definitions (`send_sms`, `google_calendar`, etc.).
- **Attach / detach** (`POST /tool/attach_tool_to_agents`, `DELETE /tool/detach_tool_from_agents`).
- **Per-agent listing** (`GET /tool/get_tools_by_agent?agent_id=...`).
- **Credential encryption**: `auth_config` JSONB AES-encrypted via `encrypt_auth_config()`.
- **Template protection**: `is_template=true` rows cannot be edited or deleted.
- **Tool type rules**: rows with `tool_type='mcp'` cannot be deleted via this surface (they belong to [[mcp-servers]]).
- **Path templating**: `{placeholder}` segments in tool URLs are substituted at call-time from LLM args via `core/services/custom_tool_service.py`.
- **Built-in dispatch**: `send_sms` and `google_calendar` route to dedicated handlers; other tools fall through to a generic HTTP webhook (POST/GET, 30s timeout).

### Edge cases & failure modes

- **⚠ `ToolService.update_tool` references `time.time()` without importing `time`**: calling `PUT /tool/update_tool` raises `NameError`. Critical bug.
- **⚠ `ToolService.create_tool` does not set `tool_type` on `Tool(...)` construction** even though the column is `NOT NULL` — likely inserts default `'custom'`, but verify.
- **⚠ `oauth_connection_id` is `Optional[int]` in the Pydantic schemas but `UUID` in the model**. Type drift — frontend casting may fail.
- **⚠ Postman drift**: two collections — `postman_collection/tools.postman_collection.json` (current) and `postman/tools_collection.json` (outdated, uses `POST /tool` instead of `/tool/create_tool`).
- **⚠ Dead columns**: `action_params_schema`, `trigger_phrases`, `entity` are declared on the model but never written or read.
- **⚠ Junction unique constraint** on `(agent_config_id, tool_id)` rather than `(agent_id, tool_id)` — per-agent dedup is enforced only at the application layer in `attach_tool_to_agents`. A direct INSERT can duplicate.
- **⚠ No automated tests** for tools.
- **`read_document` tool not in this table**: registered dynamically by `document_tool_service.py` at pipeline boot if the agent has KB uploads. See [[knowledge-base]].
- **Template tools**: `get_template_tools` returns global templates (`is_template=true`, `organization_id=NULL` or sentinel value). Verify isolation.
- **Hybrid state**: frontend uses both TanStack Query and Jotai for tool state — drift risk.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `BaseService.query()` org-filter.
- **AuthN**: `require_org_member`.
- **RBAC**: ⚠ none enforced.
- **Encryption**: `auth_config` AES-encrypted per-value.
- **Audit logging**: ⚠ none.
- **EE parity**: `ee/api/v1/tools.py` mirrors with `require_ee_org_member`.
- **Runtime HTTP**: 30s `httpx` timeout, no retries, no circuit breaker.

## 5. Test cases (as-built)

⚠ **No tests** exist for tools.

```
TEST: create_custom_tool
  WHEN  POST /tool/create_tool
        {"name":"post_to_crm","tool_type":"custom","url":"https://api.acme.com/leads",
         "method":"POST","auth_config":{"api_key":"sk-..."}}
  THEN  201; tool row; auth_config encrypted

TEST: create_tool_without_tool_type
  ⚠ Test current behavior: does NOT NULL column default to 'custom'?

TEST: update_tool_NameError
  ⚠ EXPECTED TO FAIL — PUT /tool/update_tool raises NameError (time not imported)

TEST: cannot_edit_template
  GIVEN tool T with is_template=true
  WHEN  PUT /tool/update_tool?id=T
  THEN  403 "Cannot edit template tool"

TEST: cannot_delete_mcp_tool
  GIVEN tool T with tool_type='mcp'
  WHEN  DELETE /tool/delete_tool?id=T
  THEN  400 "Cannot delete MCP tool — use mcp-server endpoints"

TEST: list_tools_pagination
  WHEN  POST /tool/list {"page":1,"page_size":20,"search":"crm"}
  THEN  paginated response

TEST: get_template_tools
  WHEN  GET /tool/get_template_tools
  THEN  [{name:"send_sms",...},{name:"google_calendar",...},...]

TEST: attach_tool_to_agents
  WHEN  POST /tool/attach_tool_to_agents
        {"tool_id":"T","agent_ids":["A","B"]}
  THEN  agent_tools rows inserted for each agent (no dup if already attached)

TEST: detach_idempotent
  WHEN  DELETE /tool/detach_tool_from_agents for non-attached
  THEN  200

TEST: get_tools_by_agent
  WHEN  GET /tool/get_tools_by_agent?agent_id=A
  THEN  list of tools currently attached to A

TEST: runtime_dispatch_custom_webhook
  GIVEN agent A with custom tool T (URL=https://x.com/{lead_id})
  WHEN  LLM calls T with {lead_id:"123"}
  THEN  httpx.POST("https://x.com/123") with auth_config injected

TEST: runtime_dispatch_send_sms
  GIVEN agent A with send_sms built-in tool
  WHEN  LLM calls send_sms with {to:"+15...", body:"hi"}
  THEN  dispatched to dedicated SMS handler (Twilio under the hood)

TEST: runtime_dispatch_google_calendar
  GIVEN agent A with google_calendar tool linked to OAuth connection
  WHEN  LLM calls google_calendar.create_event
  THEN  OAuthService.get_valid_access_token_for_connection fetches refresh-aware token,
        then Google Calendar API called with bearer token
```

## 6. Data model / DB schema

**Table: `tools`** (`core/models/tool.py`)

| Column                | Type          | Null | Default     | Notes                                                  |
|-----------------------|---------------|------|-------------|--------------------------------------------------------|
| id                    | UUID          | NO   | `uuid4()`   | PK                                                     |
| organization_id       | UUID          | YES  | —           | NULL for global templates                              |
| name                  | VARCHAR(100)  | NO   | —           | Unique within org (`UNIQUE(organization_id, name)`)    |
| description           | TEXT          | YES  | —           |                                                        |
| tool_type             | VARCHAR(30)   | NO   | —           | `custom` / `mcp` / `send_sms` / `google_calendar` / ... |
| url                   | VARCHAR(512)  | YES  | —           | Webhook target (may include `{placeholders}`)          |
| method                | VARCHAR(10)   | YES  | `'POST'`    |                                                        |
| input_schema          | JSONB         | YES  | —           | JSON Schema for LLM function args                      |
| auth_config           | JSONB         | YES  | —           | AES-encrypted credentials                              |
| oauth_connection_id   | UUID          | YES  | —           | FK → `oauth_connections.id` ON DELETE SET NULL         |
| is_template           | BOOL          | NO   | `false`     | Templates cannot be edited/deleted                     |
| is_active             | BOOL          | NO   | `true`      |                                                        |
| action_params_schema  | JSONB         | YES  | —           | ⚠ Unused                                               |
| trigger_phrases       | ARRAY(TEXT)   | YES  | —           | ⚠ Unused                                               |
| entity                | VARCHAR(100)  | YES  | —           | ⚠ Unused                                               |
| created_at            | TIMESTAMPTZ   | NO   | `now()`     |                                                        |
| updated_at            | TIMESTAMPTZ   | NO   | `now()`     |                                                        |

**Table: `agent_tools`** (`core/models/agent_tool.py`) — many-to-many join

| Column            | Type | Null | Notes                                                |
|-------------------|------|------|------------------------------------------------------|
| id                | UUID | NO   | PK                                                   |
| agent_id          | UUID | NO   | FK → agents.id                                       |
| agent_config_id   | UUID | YES  | FK → agent_configs.id                                |
| tool_id           | UUID | NO   | FK → tools.id                                        |

**⚠ Unique constraint** is on `(agent_config_id, tool_id)` not `(agent_id, tool_id)` — see edge cases.

## 7. API design

All endpoints under prefix `/api/v1/tool`. Auth: JWT bearer. RBAC: ⚠ none.

| Method | Path                                          | Purpose                                          |
|--------|-----------------------------------------------|--------------------------------------------------|
| POST   | `/tool/create_tool`                           | Create tool (201)                                |
| POST   | `/tool/list`                                  | Paginated list                                   |
| GET    | `/tool/get_all_tools`                         | Flat array of tools (dropdown)                   |
| GET    | `/tool/get_template_tools`                    | Templates catalog (global, is_template=true)     |
| GET    | `/tool/get_tool?id=...`                       | Fetch one                                        |
| POST   | `/tool/upsert_tool`                           | Create or update                                 |
| PUT    | `/tool/update_tool?id=...`                    | ⚠ NameError — broken                             |
| DELETE | `/tool/delete_tool?id=...`                    | Delete (blocked for templates and mcp type)      |
| POST   | `/tool/attach_tool_to_agents`                 | Attach a tool to one or more agents              |
| DELETE | `/tool/detach_tool_from_agents`               | Detach a tool from agents                        |
| GET    | `/tool/get_tools_by_agent?agent_id=...`       | List tools currently attached to an agent        |

### POST /tool/create_tool

```json
{
  "name": "post_to_crm",
  "description": "Submit a new lead to Acme CRM",
  "tool_type": "custom",
  "url": "https://api.acme.com/leads/{lead_type}",
  "method": "POST",
  "input_schema": {
    "type": "object",
    "properties": {
      "lead_type": {"type": "string"},
      "name": {"type": "string"},
      "email": {"type": "string"}
    },
    "required": ["lead_type","name","email"]
  },
  "auth_config": {"api_key": "sk-..."},
  "is_active": true
}
```

### Response

```json
{
  "id": "uuid", "name": "post_to_crm", "tool_type": "custom",
  "url": "https://api.acme.com/leads/{lead_type}", "method": "POST",
  "input_schema": {...}, "is_active": true, "is_template": false,
  "created_at": "...", "updated_at": "..."
}
```

## 8. Backend implementation

- **Controller**: `core/api/v1/tools.py` — 11 routes.
- **EE Controller**: `ee/api/v1/tools.py` — mirrors.
- **Service**: `core/services/tool_service.py` — CRUD, encrypts `auth_config`, template/mcp guards.
- **Runtime**:
  - `core/services/custom_tool_service.py` — builds Pipecat `ToolsSchema`, runs HTTP calls (30s timeout), substitutes `{placeholder}` segments, dispatches built-ins.
  - `core/services/document_tool_service.py` — separate path for `read_document` tool (not in this table).
- **Encryption**: `encrypt_auth_config()` AES-encrypts every value in the dict.
- **No audit logging.**

## 9. Frontend implementation

- **Route**: `/tools` — `frontend/src/app/(dashboard)/tools/page.tsx`.
- **Components** (`frontend/src/components/tools/`):
  - `ToolsListPage.tsx` — list view using TanStack Query (`/lib/api/tools.ts`).
  - `ToolFormPage.tsx` — orchestrator; branches between `CustomToolForm.tsx` and `BuiltInToolForm.tsx` based on `tool_type`.
- **API service**: `frontend/src/services/toolService.ts` (Jotai atoms in `atoms/ToolAtom.tsx`). ⚠ Hybrid state: list page uses TanStack Query while form pages use Jotai.
- **Layout**: list page + full-page form for create/edit.

## 10. Postman collection & examples

⚠ Two collections drift:
- `postman_collection/tools.postman_collection.json` — current.
- `postman/tools_collection.json` — outdated, uses `POST /tool` instead of `/tool/create_tool`.

### POST /api/v1/tool/create_tool

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"post_to_crm","tool_type":"custom","url":"https://api.acme.com/leads","method":"POST"}' \
  "$BASE_URL/api/v1/tool/create_tool"
```

### POST /api/v1/tool/list

```json
{"page": 1, "page_size": 20, "search": "crm"}
```

### POST /api/v1/tool/attach_tool_to_agents

```json
{"tool_id": "uuid", "agent_ids": ["uuid-a", "uuid-b"]}
```

### GET /api/v1/tool/get_template_tools

```json
[
  {"id": "uuid", "name": "send_sms", "tool_type": "send_sms", "is_template": true, "input_schema": {...}},
  {"id": "uuid", "name": "google_calendar", "tool_type": "google_calendar", "is_template": true, "input_schema": {...}}
]
```

## 11. Next steps

- [ ] ⚠ **Fix `update_tool` NameError** in `tool_service.py` — add `import time` or remove the `time.time()` call.
- [ ] ⚠ **Fix `create_tool` missing `tool_type` set on Tool() construction** — explicit assignment.
- [ ] ⚠ **Reconcile `oauth_connection_id` type drift**: change Pydantic schemas from `Optional[int]` to `Optional[UUID]`.
- [ ] ⚠ **Drop legacy Postman**: `postman/tools_collection.json` is stale.
- [ ] ⚠ **Fix junction unique constraint**: should be `UNIQUE(agent_id, tool_id)` not `(agent_config_id, tool_id)`. Migrate.
- [ ] ⚠ **Delete or implement** unused columns (`action_params_schema`, `trigger_phrases`, `entity`).
- [ ] ⚠ **Add tests** under `tests/test_tools.py`.
- [ ] ⚠ **Add audit logging** for tool CRUD.
- [ ] ⚠ **Unify frontend state**: pick TanStack Query OR Jotai — not both.
- [ ] ⚠ **Add RBAC**: tool credential changes are admin-level.
- [ ] **Retry / circuit-breaker** on runtime HTTP calls — today a 30s hang blocks the pipeline.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) `update_tool` raises NameError — missing `import time`; (2) `create_tool` does not set `tool_type` on construction; (3) `oauth_connection_id` is `Optional[int]` in Pydantic but `UUID` in the model — type drift; (4) Two Postman collections drift (`postman/tools_collection.json` outdated); (5) `agent_tools` unique constraint is on `(agent_config_id, tool_id)` not `(agent_id, tool_id)`; (6) Dead model columns (`action_params_schema`, `trigger_phrases`, `entity`); (7) No tests; (8) No audit logging; (9) Hybrid frontend state (TanStack Query + Jotai); (10) `read_document` tool is registered dynamically by `document_tool_service.py`, not stored in this table.
