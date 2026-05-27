# MCP Servers — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

An **MCP Server** (Model Context Protocol server) is a per-organization registration of an external tool server that agents can connect to at call-time. MCP is Anthropic's open spec for "tool servers" — a remote process exposes a list of tools (with JSON schemas), and an agent's LLM can invoke them through a uniform interface. In Tone, an MCP server stored in this table provides credentials and connection metadata; downstream [[agents]] attach servers through `agent_mcp_servers` to bind them into the runtime pipeline.

Distinct from internal [[tools]] (which are function-calling tools defined inside Tone), MCP servers are **external** — the tool catalog and execution logic live on the remote MCP endpoint.

- **Target users**: org admins / agent owners who want to plug in third-party tool servers (e.g., a sales-data MCP, a calendar MCP) without re-implementing each tool.
- **Problem solved**: a uniform, multi-tenant registration surface for external MCP servers + a many-to-many attach mechanism for [[agents]].

Cross-links: [[agents]] (each agent has many MCP servers via `agent_mcp_servers`), [[tools]] (internal counterpart), [[voice-pipeline]] (consumed at call boot), [[oauth-integrations]] (MCP server may reference an OAuth connection for credentials).

## 2. User stories & use cases

- As an agent owner, I want to register an MCP server URL + auth and validate connectivity before saving.
- As an agent owner, I want to discover what tools the MCP server exposes so I know what the agent can call.
- As an agent owner, I want to attach an MCP server to one or more agents, optionally filtering which tools each agent can use.
- As an operator, I want to detach an MCP server from an agent without deleting the registration.
- As an org admin, I want to delete an MCP server registration when it's deprecated.

Typical flow: Admin → `/mcp` → "Add MCP Server" → enters URL + auth → clicks "Validate" → backend pings the server → admin clicks "Discover tools" to see the catalog → saves → in [[agents]] edit, attaches the server to specific agents.

## 3. Functional requirements

- **CRUD** (`POST /mcp-server/upsert_mcp_server`, `GET /mcp-server/get_mcp_server`, `POST /mcp-server/list`, `DELETE /mcp-server/delete_mcp_server`).
- **Connectivity check**: `POST /mcp-server/validate_mcp_server` — POSTs a probe to the server to confirm reachability + auth.
- **Tool discovery**: `GET /mcp-server/discover_tools` — queries the remote MCP server for its tool catalog.
- **Per-agent tool cache**: `GET /mcp-server/get_mcp_tools?agent_id=...` — returns the cached/persisted tool list for an agent's MCP bindings.
- **Many-to-many attach**: `POST /mcp-server/attach_mcp_server_to_agents`, `DELETE /mcp-server/detach_mcp_server_from_agents`, `PUT /mcp-server/update_agent_mcp_server` (per-agent overrides).
- **Per-agent server query**: `GET /mcp-server/get_mcp_servers_by_agent?agent_id=...`.
- **Credential storage**: `auth_config` JSONB AES-encrypted at rest (consistent with [[tools]] and [[channels]]).
- **OAuth integration**: `mcp_servers.oauth_connection_id` (FK → `oauth_connections.id` ON DELETE SET NULL) lets the server credentials come from a connected OAuth provider.

### Edge cases & failure modes

- **⚠ `selected_tools` no-op regression**: when attaching a server to an agent with `selected_tools=["foo","bar"]`, the field is currently ignored — all tools end up exposed to the agent.
- **⚠ Postman collection drift**: `postman_collection/mcp_servers.postman_collection.json` lists routes that no longer match the current Pydantic models.
- **⚠ `auth_config` is decrypted on GET**: the GET endpoint may return plaintext auth values. Verify and gate by role.
- **⚠ No audit logging** on any CRUD or attach/detach action.
- **⚠ `meta_data.timeout` is ignored**: `mcp_servers.meta_data` accepts a `timeout` field but `mcp_tool_service.py` hard-codes the HTTP timeout.
- **⚠ Unused columns**: `endpoint`, `icon`, `oauth_connection_id` (the last is FK'd but not consumed at runtime per the agent's reading).
- **⚠ No reachability re-check**: validation runs on save but there's no periodic health check.
- **⚠ No pytest** for `/mcp-server/*` endpoints.
- **`discover_tools` is unauthenticated to the remote MCP** unless credentials are supplied — relies on `auth_config`.
- **Detach is idempotent**: detaching a server not currently attached returns 200 (no error).
- **`update_agent_mcp_server`**: allows overriding `selected_tools` and `auth_config` per-agent. Behavior on conflict (multiple agents, different overrides) is per-row.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `organization_id` on `mcp_servers`.
- **AuthN**: `require_org_member`.
- **RBAC**: ⚠ none.
- **Encryption**: `auth_config` JSONB AES-encrypted.
- **Observability**: ⚠ none on validate/discover failures.
- **EE parity**: `ee/api/v1/mcp_servers.py` mirrors with `require_ee_org_member`.
- **Performance**: server-list endpoint is paginated; discover/validate hit external HTTP (timeout = hard-coded value in `mcp_tool_service`).

## 5. Test cases (as-built)

⚠ **No dedicated tests** for MCP servers.

```
TEST: upsert_create_mcp_server
  GIVEN authenticated user in org A
  WHEN  POST /mcp-server/upsert_mcp_server
        {"name":"sales-mcp","url":"https://sales-mcp.acme.com","auth_config":{"token":"..."}}
  THEN  201; new mcp_servers row; auth_config encrypted

TEST: validate_mcp_server_reachable
  WHEN  POST /mcp-server/validate_mcp_server with valid URL + auth
  THEN  200; {"valid": true, "tool_count": N}

TEST: validate_mcp_server_unreachable
  WHEN  POST /mcp-server/validate_mcp_server with bad URL
  THEN  400; {"valid": false, "error": "..."}

TEST: discover_tools
  WHEN  GET /mcp-server/discover_tools?mcp_server_id=...
  THEN  200; [{name, description, input_schema}]

TEST: list_pagination
  GIVEN 10 MCP servers in org A
  WHEN  POST /mcp-server/list {"page":1,"page_size":5}
  THEN  items.length == 5, total == 10

TEST: attach_to_agents
  WHEN  POST /mcp-server/attach_mcp_server_to_agents
        {"mcp_server_id":"...","agent_ids":["a","b"]}
  THEN  agent_mcp_servers rows inserted

TEST: attach_with_selected_tools_NO_OP
  WHEN  attach with selected_tools=["foo"]
  THEN  ⚠ selected_tools field is currently ignored

TEST: detach_idempotent
  WHEN  DELETE /mcp-server/detach_mcp_server_from_agents for non-attached server
  THEN  200 (no-op)

TEST: delete_mcp_server
  WHEN  DELETE /mcp-server/delete_mcp_server?id=...
  THEN  200; row hard-deleted; agent_mcp_servers FKs cascade

TEST: cross_org
  GIVEN MCP server X in org A; caller in org B
  WHEN  GET /mcp-server/get_mcp_server?id=X
  THEN  404
```

## 6. Data model / DB schema

**Table: `mcp_servers`** (`core/models/mcp_server.py`)

| Column                | Type         | Null | Default     | Notes                                          |
|-----------------------|--------------|------|-------------|------------------------------------------------|
| id                    | UUID         | NO   | `uuid4()`   | PK                                             |
| organization_id       | UUID         | NO   | —           | Multi-tenancy boundary                         |
| name                  | VARCHAR(100) | NO   | —           |                                                |
| url                   | VARCHAR(512) | NO   | —           | MCP server endpoint                            |
| endpoint              | VARCHAR(100) | YES  | —           | ⚠ Unused                                       |
| icon                  | VARCHAR(255) | YES  | —           | ⚠ Unused                                       |
| oauth_connection_id   | UUID         | YES  | —           | FK → `oauth_connections.id` ON DELETE SET NULL |
| auth_config           | JSONB        | YES  | —           | AES-encrypted credentials                      |
| meta_data             | JSONB        | YES  | `{}`        | `{timeout, …}` ⚠ timeout ignored               |
| is_active             | BOOL         | NO   | `true`      |                                                |
| created_at            | TIMESTAMPTZ  | NO   | `now()`     |                                                |
| updated_at            | TIMESTAMPTZ  | NO   | `now()`     |                                                |

**Table: `agent_mcp_servers`** (`core/models/agent_mcp_server.py`) — many-to-many join

| Column                | Type   | Null | Notes                                        |
|-----------------------|--------|------|----------------------------------------------|
| id                    | UUID   | NO   | PK                                           |
| agent_id              | UUID   | NO   | FK → agents.id                               |
| mcp_server_id         | UUID   | NO   | FK → mcp_servers.id                          |
| agent_config_id       | UUID   | YES  | FK → agent_configs.id                        |
| oauth_connection_id   | UUID   | YES  | FK → oauth_connections.id (per-agent override)|
| selected_tools        | JSONB  | YES  | ⚠ Currently ignored                          |
| auth_config           | JSONB  | YES  | Per-agent credential override (encrypted)    |

## 7. API design

All endpoints under prefix `/api/v1/mcp-server`. Auth: JWT bearer. RBAC: ⚠ none.

| Method | Path                                                       | Purpose                                            |
|--------|------------------------------------------------------------|----------------------------------------------------|
| POST   | `/mcp-server/list`                                         | Paginated list with search/sort                    |
| POST   | `/mcp-server/upsert_mcp_server`                            | Create or update an MCP server                     |
| POST   | `/mcp-server/validate_mcp_server`                          | Probe reachability + auth                          |
| GET    | `/mcp-server/get_mcp_server?id=...`                        | Fetch one                                          |
| GET    | `/mcp-server/discover_tools?mcp_server_id=...`             | Query remote server for tool catalog               |
| GET    | `/mcp-server/get_mcp_tools?agent_id=...`                   | Get cached tool list for agent's MCP servers       |
| DELETE | `/mcp-server/delete_mcp_server?id=...`                     | Delete registration                                |
| POST   | `/mcp-server/attach_mcp_server_to_agents`                  | Attach a server to one or more agents              |
| DELETE | `/mcp-server/detach_mcp_server_from_agents`                | Detach a server from agents                        |
| PUT    | `/mcp-server/update_agent_mcp_server`                      | Update per-agent override (selected_tools, auth)   |
| GET    | `/mcp-server/get_mcp_servers_by_agent?agent_id=...`        | List servers attached to a given agent             |

### POST /mcp-server/upsert_mcp_server

```json
{
  "id": "uuid_or_null",
  "name": "Sales MCP",
  "url": "https://sales-mcp.acme.com",
  "auth_config": {"token": "sk-..."},
  "meta_data": {"timeout": 30},
  "oauth_connection_id": "uuid_or_null",
  "is_active": true
}
```

### Response

```json
{
  "id": "uuid", "name": "Sales MCP", "url": "https://sales-mcp.acme.com",
  "is_active": true, "meta_data": {"timeout": 30},
  "oauth_connection_id": null,
  "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"
}
```

## 8. Backend implementation

- **Controller**: `core/api/v1/mcp_servers.py` — 11 routes.
- **EE Controller**: `ee/api/v1/mcp_servers.py` — mirrors.
- **Service**: `core/services/mcp_server_service.py` — 471 lines.
  - CRUD + validation + discovery + attach/detach + agent-scoped queries.
  - Encrypts `auth_config` via `core/utils/encryption`.
- **Runtime tool service**: `core/services/mcp_tool_service.py` (101 lines) — wraps the MCP HTTP client used by the pipeline to invoke tools at call-time.
- **No audit logging.**
- **No durable background jobs** — validation/discovery are synchronous HTTP.

## 9. Frontend implementation

- **Route**: `/mcp` — `frontend/src/app/(dashboard)/mcp/page.tsx` — list + create modal.
- **API service**: `frontend/src/services/mcpServerService.ts` — CRUD + attach/detach wrappers.
- **State**: Jotai atoms.
- **Layout**: card-grid list (using `CustomTable` or a card layout), modal form for create/edit, "Validate" button on the form.

## 10. Postman collection & examples

`postman_collection/mcp_servers.postman_collection.json`. ⚠ Drifted from current Pydantic shapes.

### POST /api/v1/mcp-server/upsert_mcp_server

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "Sales MCP", "url": "https://sales-mcp.acme.com",
    "auth_config": {"token": "sk-..."}, "is_active": true
  }' \
  "$BASE_URL/api/v1/mcp-server/upsert_mcp_server"
```

### POST /api/v1/mcp-server/validate_mcp_server

```json
{"id": "uuid_optional", "url": "https://sales-mcp.acme.com", "auth_config": {"token": "sk-..."}}
```

```json
{"valid": true, "tool_count": 12, "message": "Server reachable"}
```

### GET /api/v1/mcp-server/discover_tools?mcp_server_id=uuid

```json
[
  {"name": "get_account", "description": "Look up an account by id", "input_schema": {...}},
  {"name": "list_deals", "description": "List open deals", "input_schema": {...}}
]
```

### POST /api/v1/mcp-server/attach_mcp_server_to_agents

```json
{"mcp_server_id": "uuid", "agent_ids": ["uuid-a", "uuid-b"], "selected_tools": ["get_account"]}
```

⚠ `selected_tools` is currently ignored.

## 11. Next steps

- [ ] ⚠ **Fix `selected_tools` no-op regression** in `attach_mcp_server_to_agents` and `update_agent_mcp_server` — filter the tool list at runtime instead of always exposing all tools.
- [ ] ⚠ **Refresh Postman collection** to match current Pydantic shapes.
- [ ] ⚠ **Mask `auth_config` on GET** unless caller is admin/owner.
- [ ] ⚠ **Add audit logging** for create/delete/attach/detach.
- [ ] ⚠ **Wire `meta_data.timeout`** in `mcp_tool_service.py` to drive the HTTP timeout.
- [ ] ⚠ **Remove or implement** unused columns (`endpoint`, `icon`).
- [ ] ⚠ **Add reachability re-check** as a periodic Celery beat task (mark `is_active=false` on persistent failure).
- [ ] **Add tests** under `tests/test_mcp_servers.py`.
- [ ] **Add RBAC**: MCP server registration is admin-level.
- [ ] **Distinguish MCP tools from internal [[tools]]** in the frontend (different UI, different attach flows).

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) `selected_tools` no-op regression on attach — all tools always exposed; (2) Postman collection drifted from Pydantic models; (3) `auth_config` may be decrypted on GET — verify and gate; (4) No audit logging anywhere; (5) `meta_data.timeout` is ignored; (6) Unused columns `endpoint`, `icon`, `oauth_connection_id` consumption unclear; (7) No periodic reachability re-check; (8) No pytest suite.
