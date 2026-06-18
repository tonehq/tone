# Feature Doc: MCP Servers

Feature documentation for the MCP Servers list + create/edit/detail pages. Used
by `/generate-tests mcp-servers` (or `--docs e2e/ux_flow_docs/mcp-servers.md`) to ensure
all user cases are covered.

An **MCP Server** (Model Context Protocol) is a per-organization registration
of an external tool server. Agents attach MCP servers so the LLM can call the
remote tools at runtime.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Pages

- **Routes**:
  - `/mcp` — list (card grid)
  - `/mcp/create` — create form (full page)
  - `/mcp/edit/[id]` — edit form (full page)
  - `/mcp/[id]/tools` — server detail (discovered tools)
- **Wrappers**:
  - `src/app/(dashboard)/mcp/page.tsx`
  - `src/app/(dashboard)/mcp/create/page.tsx`
  - `src/app/(dashboard)/mcp/edit/[id]/page.tsx`
  - `src/app/(dashboard)/mcp/[id]/tools/page.tsx`
- **Main components**:
  - `src/components/mcp/MCPListPage.tsx`
  - `src/components/mcp/MCPServerCard.tsx`
  - `src/components/mcp/MCPFormPage.tsx` (shared by create + edit)
  - `src/components/mcp/MCPToolsListPage.tsx`
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fmcp` without `tone_access_token` cookie)

---

## User Stories

### US-1: Browse MCP servers

**As an** agent owner, **I want to** see all MCP servers my org has registered, **so that** I know which external tool servers are available to attach.

**Acceptance criteria**:

- [ ] Page header shows "MCP Servers" (h1) + subtitle "Connect Model Context Protocol servers to extend your agents with external tools and resources."
- [ ] Primary CTA "Create MCP Server" appears in the header
- [ ] Filter toolbar: search placeholder "Search MCP servers… (e.g. name:clickup)" + sort dropdown (Newest / Oldest / Name A–Z / Name Z–A / Recently updated)
- [ ] List renders as a 3-column responsive card grid
- [ ] Each card shows: favicon (from server URL with fallback to a Server icon on sky-500), name, hostname, 2-line clamped description, transport-type badge (Streamable HTTP / SSE), status pill (Live with green ping / Paused), action menu (⋮ Edit / Delete)
- [ ] Loading state: card-grid skeletons
- [ ] A dashed "+ New MCP Server" card always appears at the end of the grid

### US-2: Create a new MCP server

**As an** agent owner, **I want to** register a new MCP server URL with auth and timeout, **so that** my agents can later attach and discover its tools.

**Acceptance criteria**:

- [ ] "Create MCP Server" navigates to `/mcp/create`
- [ ] Form renders sections: Settings, Server, Protocol, Auth
- [ ] Settings: name (required), description (optional), is_active toggle (default true)
- [ ] Server: server_url (required), transport_type radio (Streamable HTTP / SSE, required), timeout slider (1–60 s, default 20)
- [ ] Protocol: HTTP headers builder — dynamic key/value pairs, add and remove rows
- [ ] Auth: bearer token toggle + input, API key toggle + input, OAuth connection dropdown (from `oauthAtom`)
- [ ] "Save server" calls `POST /mcp-server/upsert_mcp_server`; "Cancel" returns to `/mcp`
- [ ] On success: redirects to `/mcp`; new card appears
- [ ] On error: `handleApiError` toast, user remains on the form with state preserved

### US-3: Edit an existing MCP server

**As an** agent owner, **I want to** edit name, URL, headers, auth, or timeout on an existing server, **so that** I can fix mistakes or rotate credentials without recreating it.

**Acceptance criteria**:

- [ ] "Edit" from the card action menu navigates to `/mcp/edit/[id]`
- [ ] Form loads with all fields pre-populated from `GET /mcp-server/get_mcp_server`
- [ ] "Update server" calls `POST /mcp-server/upsert_mcp_server` with the existing id
- [ ] Reserved URL segments (`/mcp/create/tools`, `/mcp/edit/tools`) redirect to `/mcp`

### US-4: Inspect discovered tools

**As an** agent owner, **I want to** see which tools an MCP server exposes, **so that** I know what capabilities the agent will gain when attached.

**Acceptance criteria**:

- [ ] Click a card → navigates to `/mcp/[id]/tools`
- [ ] Header shows back arrow + server name + transport-type badge + status badge
- [ ] "Refresh tools" button calls `GET /mcp-server/discover_tools`
- [ ] Search bar (token-based) filters tools by name
- [ ] Table columns: Name, Description, Parameters (JSON snippet), action icons
- [ ] Loading state: skeleton while discovery runs
- [ ] Empty state with no tools: "No tools available"
- [ ] Empty state with search but no matches: "No tools match your search"

### US-5: Delete an MCP server

**As an** org admin, **I want to** delete a registration I no longer need, **so that** it can't be attached to new agents by mistake.

**Acceptance criteria**:

- [ ] "Delete" from the card action menu calls `DELETE /mcp-server/delete_mcp_server`
- [ ] Card is removed from the list on success
- [ ] Deleting a server attached to agents is blocked by the backend (or detaches the binding, depending on backend rules); the response is surfaced via `handleApiError`

### US-6: OAuth flow without losing form state

**As an** agent owner, **I want to** start an OAuth flow from the MCP form and return to the same form with my draft intact, **so that** I don't re-enter everything.

**Acceptance criteria**:

- [ ] When the user triggers OAuth from the Auth section, the form snapshot is written to `sessionStorage` under key `mcp-form-oauth-draft`
- [ ] On return from OAuth, the form restores its prior fields and the new OAuth connection is selectable in the dropdown
- [ ] Successful save clears the draft

---

## Input Specifications

### Create / Edit MCP form (`MCPFormPage.tsx`)

| Field                  | Type      | Required | Validation Rules                                                                                                 | Exact Error Message                                                       |
| ---------------------- | --------- | -------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Server Name            | text      | yes      | RHF `rules.required: 'Server name is required'`; rendered inline below the input                                  | `Server name is required`                                                  |
| Description            | textarea  | no       | `maxLength={1000}`; counter shows `n/1000`                                                                        | (counter only — no toast)                                                  |
| Server URL             | textarea  | yes      | RHF `rules.required: 'Server URL is required'`; backend re-validates as URL                                       | Inline: `Server URL is required`. Backend: `Invalid server URL. Please check the URL and try again.` |
| Timeout                | slider    | yes      | `min=1, max=300, step=1`; default 20; stored in `meta_data.timeout`                                               | (range-enforced; no error)                                                 |
| Transport type         | radio     | yes      | One of `shttp` (UI value) / `sse`; mapped to `streamable_http` / `sse` on save                                    | Backend: `Invalid transport_type 'X'. Must be one of: sse, streamable_http` |
| Use Bearer Token       | checkbox  | no       | When ON, `bearer_token` text input appears; trim-non-empty → saved under `auth_config.bearer_token`                | (none)                                                                     |
| Bearer Token           | password  | conditional | Required-feel when Bearer toggle is ON; empty just omits the field                                            | Backend: `Authentication failed. Please check your token or API key and try again.` |
| Use API Key            | checkbox  | no       | When ON, `api_key` text input appears; trim-non-empty → saved under `auth_config.api_key`                          | (none)                                                                     |
| OAuth connection       | select    | no       | Default `__none__` (sentinel); selected connections with `status=='pending'` are filtered out                      | (none)                                                                     |
| HTTP Headers           | repeater  | no       | Rows with empty `key` are stripped at save time; whitespace `.trim()`'d                                            | (none — silent strip)                                                      |
| is_active              | switch    | no       | Default ON; controls `is_active` field                                                                            | (none)                                                                     |

OAuth discovery extra guard: clicking "Auto-discover" with an empty `server_url` → inline toast `Enter the server URL first`.

### Tools page (`MCPToolsListPage.tsx`)

| Field   | Type  | Required | Validation                                                  | Error                |
| ------- | ----- | -------- | ----------------------------------------------------------- | -------------------- |
| Search  | token | no       | Single token of `field: 'name'`; client-side filter only    | (no validation)      |

---

## UI Elements

| Element                       | Type            | Content / Label                                                 | Behavior                                                       |
| ----------------------------- | --------------- | --------------------------------------------------------------- | -------------------------------------------------------------- |
| Page heading                  | h1              | "MCP Servers"                                                   | Static                                                         |
| Page subtitle                 | body1           | "Connect Model Context Protocol servers…"                       | Static                                                         |
| Create MCP Server button      | Button          | "Create MCP Server"                                             | Navigates to `/mcp/create`                                     |
| Search bar                    | TokenSearch     | "Search MCP servers… (e.g. name:clickup)"                       | Token-based, sends params to `/mcp-server/list`                |
| Sort dropdown                 | Select          | Newest / Oldest / Name A–Z / Name Z–A / Recently updated        | Re-fetches list with `sort_by`/`sort_order`                    |
| Server card                   | Card            | favicon + name + hostname + description + badges                | Click navigates to `/mcp/[id]/tools`                           |
| Action menu (card)            | Icon button     | ⋮ Edit / Delete                                                 | Edit → `/mcp/edit/[id]`; Delete → DELETE call                   |
| Transport-type badge          | Badge           | "Streamable HTTP" (Zap icon) / "SSE" (Radio icon)               | Static                                                         |
| Status pill                   | Pill            | "Live" (green, animated ping) / "Paused" (gray)                 | Reflects `is_active`                                           |
| "+ New MCP Server" card       | Dashed card     | "+ New MCP Server"                                              | Navigates to `/mcp/create`                                     |
| Empty state (no matches)      | Card            | "No MCP servers match your filters" + "Clear filters"           | Shown when filtered total is 0                                 |
| Empty state (no servers)      | Card            | "Create your first MCP server" + "Create MCP Server" button     | Shown when total is 0 and no filters                           |
| Form: Name input              | TextInput       | required                                                         | Validated                                                      |
| Form: Description             | TextAreaField   | optional                                                         | Renders the value in card with italic placeholder when empty   |
| Form: Active toggle           | Switch          | default ON                                                       | Maps to `is_active`                                            |
| Form: Server URL              | TextInput       | full URL, required                                               | Validated                                                      |
| Form: Transport type          | Radio           | "Streamable HTTP" / "SSE"                                        | Required                                                       |
| Form: Timeout slider          | Slider          | 1–60 s, default 20                                               | Stored in `meta_data.timeout`                                  |
| Form: Headers builder         | Repeater        | dynamic key/value rows                                           | Add / remove rows                                              |
| Form: Bearer token toggle     | Switch          | —                                                                | Reveals bearer-token text input                                |
| Form: API key toggle          | Switch          | —                                                                | Reveals api-key text input                                     |
| Form: OAuth connection select | SelectInput     | optional                                                         | Source: `oauthAtom`                                            |
| Form: Save button             | Button          | "Save server" (create) / "Update server" (edit)                  | Disabled while submitting                                      |
| Detail: Back arrow            | IconLink        | back to `/mcp`                                                   | Always                                                         |
| Detail: Refresh tools button  | Button          | "Refresh tools"                                                  | Calls discover endpoint                                        |
| Detail: Tools table           | Table           | Name / Description / Parameters / actions                        | Filtered by search bar                                         |

---

## Navigation

| Trigger                                | Destination                                  | Condition                                |
| -------------------------------------- | -------------------------------------------- | ---------------------------------------- |
| Click "Create MCP Server" button       | `/mcp/create`                                | Always                                   |
| Click "+ New MCP Server" card          | `/mcp/create`                                | Always                                   |
| Click action menu → Edit               | `/mcp/edit/[id]`                             | Always                                   |
| Click action menu → Delete             | Confirm → `DELETE /mcp-server/delete_mcp_server` | Always                                   |
| Click server card                      | `/mcp/[id]/tools`                            | Always                                   |
| Click back arrow on detail             | `/mcp`                                       | Always                                   |
| Click "Save server" on create          | `/mcp` (after success)                       | Form valid                               |
| Click "Update server" on edit          | `/mcp` (after success)                       | Form valid                               |
| Click "Cancel" on create/edit          | `/mcp`                                       | Always                                   |
| Visit `/mcp/create/tools` (reserved)   | `/mcp` (redirect)                            | Reserved segment                         |
| Visit `/mcp/edit/tools` (reserved)     | `/mcp` (redirect)                            | Reserved segment                         |
| Visit `/mcp/[invalid-id]/tools`        | `/mcp` (redirect via `useEffect`)            | Server not found                         |
| No auth cookie                         | `/auth/login?redirect=%2Fmcp`                | `src/middleware.ts` redirect             |

---

## API Contracts

Prefix: `/api/v1`. Verified against the Postman `MCP Servers` folder and `src/services/mcpServerService.ts`.

| Endpoint                                              | Method | Request                                                         | Success                                                          | Error                |
| ----------------------------------------------------- | ------ | --------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------- |
| `/mcp-server/list`                                    | POST   | `{ page, page_size, search?, is_active?, sort? }`               | `200 { data: McpServer[], pagination: {...} }`                   | `{ detail: "..." }`  |
| `/mcp-server/upsert_mcp_server`                       | POST   | full payload (with `id` on update)                              | `200 McpServer`                                                  | `{ detail: "..." }`  |
| `/mcp-server/validate_mcp_server`                     | POST   | `{ server_url, transport_type, auth_config? }`                   | `200 { tools: McpTool[], tool_count }`                           | `{ detail: "..." }`  |
| `/mcp-server/get_mcp_server`                          | GET    | `?mcp_server_id=<id>`                                            | `200 McpServer`                                                  | `{ detail: "..." }`  |
| `/mcp-server/discover_tools`                          | GET    | `?mcp_server_id=<id>`                                            | `200 { server_name, server_url, transport_type, tools, tool_count }` | `{ detail: "..." }` |
| `/mcp-server/get_mcp_tools`                           | GET    | `?mcp_server_id=<id>`                                            | `200 McpTool[]`                                                  | `{ detail: "..." }`  |
| `/mcp-server/delete_mcp_server`                       | DELETE | `?mcp_server_id=<id>`                                            | `200 { message: "MCP server deleted successfully" }`             | `{ detail: "..." }`  |
| `/mcp-server/facets`                                  | POST   | `{ filters: Array<{field, operator, value}> }`                   | `200 { auth_type: { none, oauth, bearer } }`                     | `{ detail: "..." }`  |
| `/mcp-server/filter-values`                           | GET    | `?column_name=auth_type`                                         | `200 { values: string[] }`                                       | `{ detail: "..." }`  |
| `/mcp-server/attach_mcp_server_to_agents`             | POST   | `{ mcp_server_id, agent_ids: string[], selected_tools?: string[] }` | `200 { message }`                                              | `{ detail: "..." }`  |
| `/mcp-server/detach_mcp_server_from_agents`           | DELETE | `{ mcp_server_id, agent_ids: string[] }`                         | `200 { message }`                                                | `{ detail: "..." }`  |

### Example — `POST /mcp-server/upsert_mcp_server`

Create request:
```json
{
  "name":"sales-mcp",
  "description":"Sales CRM tools",
  "server_url":"https://sales-mcp.acme.com/mcp",
  "transport_type":"streamable_http",
  "auth_config":{"bearer_token":"sk-mcp-token-here"},
  "oauth_connection_id":null,
  "meta_data":{"timeout":30,"http_headers":{"X-Custom":"abc"}},
  "is_active":true
}
```

Errors:
- `400 {"detail":"name is required when creating a new MCP server"}`
- `400 {"detail":"server_url is required when creating a new MCP server"}`
- `400 {"detail":"Invalid transport_type 'websocket'. Must be one of: sse, streamable_http"}`
- `400 {"detail":"Invalid server URL. Please check the URL and try again."}`
- `400 {"detail":"Authentication failed. Please check your token or API key and try again."}`
- `404 {"detail":"MCP server not found"}` (on update)
- `409 {"detail":"An MCP server with name 'sales-mcp' already exists in this organization"}`

---

## Test Cases

> Every test case is **one Action + multiple Observations**. ID prefix legend:
> `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation), `TC-ERROR-` (server
> errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled), `TC-EDGE-`
> (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Browse MCP servers list (WF-1)

**Preconditions**:
- Authenticated via `loginViaUI(page)`.

**Action**:
1. Navigate to `/mcp`

**Observation 1 — Page header**:
1. Heading "MCP Servers" is visible
2. Subtitle is visible
3. "Create MCP Server" primary CTA is visible

**Observation 2 — List fetch**:
1. Exactly one `POST /mcp-server/list` is recorded

**Observation 3 — Grid render**:
1. A 3-column responsive card grid renders
2. Each card shows favicon, name, hostname, transport badge, and status pill
3. A dashed "+ New MCP Server" card appears at the end of the grid

---

### TC-HAPPY-002: List renders 2 cards plus the dashed "+ New MCP Server" card (PS-1)

**Action**:
1. Visit `/mcp`

**Observation 1 — Cards count**:
1. Two cards render: one Live (`sales-mcp`) and one Paused (`clickup_mcp`)

**Observation 2 — Transport badges**:
1. "Streamable HTTP" badge is visible on sales-mcp
2. "SSE" badge is visible on clickup_mcp

**Observation 3 — Dashed tile**:
1. A dashed "+ New MCP Server" tile appears at the end of the grid

**API mock**: `POST /mcp-server/list` → 200 with two-item `data` payload.

---

### TC-HAPPY-003: Empty list shows the no-servers empty state (PS-2)

**Action**:
1. Visit `/mcp`

**Observation 1 — Empty state**:
1. `MCPEmptyState` renders with "Create MCP Server" CTA

**Observation 2 — Toolbar hidden**:
1. The search + sort toolbar is hidden

**API mock**: `POST /mcp-server/list` → 200 `{ data: [], pagination: { total: 0, ... } }`.

---

### TC-HAPPY-004: Empty list with active filters shows the no-matches state (PS-3)

**Preconditions**:
- A search or filter is set such that `hasActiveFilters` is true.

**Action**:
1. Visit `/mcp` with an applied search

**Observation 1 — No-matches state**:
1. Text `No MCP servers match your filters` is visible
2. A "Clear filters" link is visible

**API mock**: `POST /mcp-server/list` → 200 `{ data: [], pagination: { total: 0, ... } }` with filters set.

---

### TC-HAPPY-005: Sort by Name A–Z refetches list (WF-1 step 3)

**Action**:
1. Visit `/mcp`
2. Change the sort dropdown to "Name A–Z"

**Observation 1 — Refetch**:
1. `POST /mcp-server/list` re-fires with `sort_by: "name", sort_order: "asc"` (or equivalent)

---

### TC-HAPPY-006: Search by token (WF-1 step 4)

**Action**:
1. Visit `/mcp`
2. Type `name:clickup` into the search bar

**Observation 1 — Refetch**:
1. `POST /mcp-server/list` re-fires with `search_query` reflecting the token

---

### TC-HAPPY-007: Create a new MCP server (WF-2 / PS-4)

**Preconditions**:
- Authenticated; on `/mcp`.

**Action**:
1. Click "Create MCP Server"
2. Fill "Server Name" = `clickup_mcp`
3. Fill "Server URL" = `https://api.clickup.com/mcp`
4. Leave transport "Streamable HTTP" (default) and timeout at 20
5. Toggle "Use Bearer Token" on and enter `sk-bearer-xxx`
6. Click "Save server"

**Observation 1 — Navigation to create**:
1. Route navigates to `/mcp/create`
2. Top bar shows "New MCP Server" + status pill "Active"

**Observation 2 — Rail preview updates**:
1. The rail preview hostname becomes `api.clickup.com`
2. The chip row shows `SHTTP`, `20s timeout`, `Bearer auth` (after step 5), `0 headers`

**Observation 3 — Save fires**:
1. Exactly one `POST /mcp-server/upsert_mcp_server` is recorded
2. Body includes `auth_config.bearer_token = "sk-bearer-xxx"`

**Observation 4 — Success**:
1. Toast title equals `MCP server created successfully`
2. URL becomes `/mcp`

**API mock**: `POST /mcp-server/upsert_mcp_server` → 200.

---

### TC-HAPPY-008: Edit an existing MCP server (WF-3 / PS-5)

**Preconditions**:
- A server exists on `/mcp`.

**Action**:
1. Click ⋮ on a card → "Edit"
2. Edit the description
3. Click "Save Changes"

**Observation 1 — Navigation + hydration**:
1. Route becomes `/mcp/edit/[id]`
2. `GET /mcp-server/get_mcp_server?mcp_server_id=<id>` is recorded
3. Form fields hydrate from the response

**Observation 2 — Save fires**:
1. `POST /mcp-server/upsert_mcp_server` is recorded with `{ id, ...payload }`

**Observation 3 — Success**:
1. Toast title equals `MCP server updated successfully`
2. URL becomes `/mcp`

---

### TC-HAPPY-009: Discover tools (WF-4 / PS-6)

**Action**:
1. Click a server card

**Observation 1 — Navigation + fetches**:
1. Route becomes `/mcp/[id]/tools`
2. `GET /mcp-server/get_mcp_server` fires
3. `GET /mcp-server/discover_tools` fires

**Observation 2 — Tools table**:
1. Table renders with columns Name, Method, Params count chip, Required count chip
2. Total badge shows the tool count (e.g. `2`)

**API mock**: `discover_tools` → 200 with two tools (`get_account` + `list_deals`).

---

### TC-HAPPY-010: Tools client-side filter

**Action**:
1. On the tools page, type `name:get_account` into the search bar

**Observation 1 — Client filter**:
1. Only matching rows are visible
2. No additional `discover_tools` request fires

---

### TC-HAPPY-011: Refresh tools button (MCP-043)

**Action**:
1. Click "Refresh tools" on the tools page

**Observation 1 — Refetch**:
1. `GET /mcp-server/discover_tools` re-fires
2. The table updates with the new response

---

### TC-HAPPY-012: Delete a server (WF-5 / PS-7)

**Action**:
1. Click ⋮ on a card → "Delete"
2. Confirm

**Observation 1 — Delete request**:
1. `DELETE /mcp-server/delete_mcp_server?mcp_server_id=<id>` is recorded

**Observation 2 — Success**:
1. Toast title equals `MCP server deleted successfully`
2. Card is removed
3. List refetches

**API mock**: `DELETE` → 200 `{ message: "MCP server deleted successfully" }`.

---

### TC-HAPPY-013: OAuth round-trip with sessionStorage draft (WF-6 / PS-8 / MCP-047)

**Preconditions**:
- Authenticated; on `/mcp/create`.

**Action**:
1. Open `/mcp/create` and fill name + server URL + headers
2. Click "Auto-discover" (mocked to return a `https://provider.example/authorize?...` URL)
3. Re-navigate to `/mcp/create?mcp_oauth=success&connection_id=conn-new`
4. Click "Save"

**Observation 1 — Initial draft empty**:
1. `sessionStorage.getItem('mcp-form-oauth-draft')` returns `null` before step 2

**Observation 2 — Draft written before OAuth redirect**:
1. After step 2, `sessionStorage['mcp-form-oauth-draft']` contains a JSON snapshot of the form state
2. The browser is redirected to the authorize URL

**Observation 3 — Restoration**:
1. After step 3, the form fields are restored from the draft
2. `oauth_connection_id` equals `conn-new`
3. `sessionStorage['mcp-form-oauth-draft']` is cleared
4. URL query params are stripped (`page.url()` equals `http://localhost:3000/mcp/create`)

**Observation 4 — Save clears draft**:
1. Save payload includes `oauth_connection_id`
2. Success toast appears
3. Draft remains cleared after save

---

### TC-HAPPY-014: Reserved segment redirect (PS-9)

**Action**:
1. Visit `/mcp/create/tools`
2. Visit `/mcp/edit/tools`

**Observation 1 — Both redirect**:
1. URL becomes `/mcp` in both cases
2. No API call fires

---

### TC-VALIDATE-001: Create — missing name (FS-1 / MCP-019)

**Action**:
1. Navigate to `/mcp/create`
2. Leave Server Name blank, fill Server URL
3. Click Save

**Observation 1 — Inline error**:
1. Text under Server Name reads `Server name is required`

**Observation 2 — No network call**:
1. Zero `POST /mcp-server/upsert_mcp_server` requests are recorded

---

### TC-VALIDATE-002: Create — missing server URL (FS-2 / MCP-020)

**Action**:
1. Navigate to `/mcp/create`
2. Fill Server Name, leave Server URL blank
3. Click Save

**Observation 1 — Inline error**:
1. Text under Server URL reads `Server URL is required`

**Observation 2 — No network call**:
1. Zero `POST /mcp-server/upsert_mcp_server` requests are recorded

---

### TC-VALIDATE-003: Whitespace-only Server Name is rejected (MCP-019)

**Action**:
1. Navigate to `/mcp/create`
2. Type `   ` into Server Name
3. Fill Server URL
4. Click Save

**Observation 1 — Inline error**:
1. Text under Server Name reads `Server name is required`

**Observation 2 — No network call**:
1. Zero `POST /mcp-server/upsert_mcp_server` requests are recorded

---

### TC-VALIDATE-004: Whitespace-only Server URL is rejected (MCP-020)

**Action**:
1. Navigate to `/mcp/create`
2. Fill Server Name
3. Type `   ` into Server URL
4. Click Save

**Observation 1 — Inline error**:
1. Text under Server URL reads `Server URL is required`

**Observation 2 — No network call**:
1. Zero `POST /mcp-server/upsert_mcp_server` requests are recorded

---

### TC-VALIDATE-005: Auto-discover OAuth with empty server URL (FS-12 / MCP-042)

**Action**:
1. Navigate to `/mcp/create`
2. Leave Server URL blank
3. Click "Auto-discover"

**Observation 1 — Inline toast**:
1. Toast title equals `Enter the server URL first`

**Observation 2 — No side effects**:
1. No sessionStorage write
2. No external redirect

---

### TC-ERROR-001: Create — server-side duplicate name (409) (FS-3 / MCP-010)

**Action**:
1. Navigate to `/mcp/create`
2. Fill valid form fields
3. Click Save

**Observation 1 — Toast**:
1. Toast title is `An MCP server with name 'sales-mcp' already exists in this organization`

**Observation 2 — Form persists**:
1. User remains on `/mcp/create`
2. Form state is intact

**API mock**: `POST /mcp-server/upsert_mcp_server` → 409 with exact detail.

---

### TC-ERROR-002: Create — invalid URL (400) (FS-4 / MCP-024)

**Action**:
1. Navigate to `/mcp/create`
2. Fill Server Name + Server URL = `not-a-url`
3. Click Save

**Observation 1 — Toast**:
1. Toast title equals `Invalid server URL. Please check the URL and try again.`

**API mock**: `POST /mcp-server/upsert_mcp_server` → 400.

---

### TC-ERROR-003: Create — auth failed (400) (FS-5)

**Action**:
1. Navigate to `/mcp/create`
2. Fill all fields including a bearer token
3. Click Save

**Observation 1 — Toast**:
1. Toast title equals `Authentication failed. Please check your token or API key and try again.`

**API mock**: 400 with the auth detail.

---

### TC-ERROR-004: Create — invalid transport_type (400) (FS-6)

**Action**:
1. Mutate transport_type to `websocket` via DevTools
2. Click Save

**Observation 1 — Toast**:
1. Toast title equals `Invalid transport_type 'websocket'. Must be one of: sse, streamable_http`

**API mock**: 400 with the transport detail.

---

### TC-ERROR-005: Edit — 404 on load (FS-7)

**Action**:
1. Navigate to `/mcp/edit/[id]`

**Observation 1 — Toast**:
1. Toast title equals `MCP server not found`

**Observation 2 — Form defaults**:
1. Form fields render the `useForm` defaults

**API mock**: `GET /mcp-server/get_mcp_server` → 404.

---

### TC-ERROR-006: Edit — 404 on save (FS-8)

**Action**:
1. Navigate to `/mcp/edit/[id]`
2. Edit a field
3. Click Save

**Observation 1 — Toast**:
1. Toast title equals `MCP server not found`

**Observation 2 — User persists**:
1. URL remains `/mcp/edit/[id]`

**API mock**: `POST /mcp-server/upsert_mcp_server` → 404.

---

### TC-ERROR-007: Delete — 404 (FS-9 / MCP-009)

**Action**:
1. Click ⋮ on a card → Delete → confirm

**Observation 1 — Toast**:
1. Toast title equals `MCP server not found`

**Observation 2 — Refetch removes stale row**:
1. The card disappears after the refetch

**API mock**: `DELETE` → 404.

---

### TC-ERROR-008: Discover tools — connection refused (400) (FS-10)

**Action**:
1. Click a card to load `/mcp/[id]/tools`

**Observation 1 — Toast**:
1. Toast title equals `Failed to connect to MCP server: connection refused`

**Observation 2 — Empty state**:
1. The tools table shows the `No tools available` empty state (NOT `No tools match your search`)

**API mock**: `GET /mcp-server/discover_tools` → 400.

---

### TC-ERROR-009: Discover tools — server not found (404) (FS-11)

**Preconditions**:
- Both `getMcpServer` AND `discoverMcpTools` fail.

**Action**:
1. Navigate to `/mcp/[id]/tools` for a deleted server

**Observation 1 — Toast**:
1. Toast title equals `MCP server not found`

**Observation 2 — Header subtitle**:
1. Reads `Could not load this MCP server. It may have been deleted or you may not have access.`

**API mock**: both endpoints → 404.

---

### TC-ERROR-010: Auto-discover OAuth — backend error (FS-13)

**Action**:
1. Click Auto-discover with a filled URL
2. Backend mock throws

**Observation 1 — Draft cleared**:
1. `sessionStorage['mcp-form-oauth-draft']` is removed

**Observation 2 — Toast**:
1. Toast surfaces server `detail` OR default via `handleApiError`

---

### TC-ERROR-011: OAuth round-trip with corrupted draft (FS-14 / MCP-048)

**Action**:
1. Manually set `sessionStorage['mcp-form-oauth-draft'] = '{not valid json'`
2. Navigate to `/mcp/create?mcp_oauth=success&connection_id=conn-new`

**Observation 1 — No crash**:
1. The catch block runs; no JS exception bubbles to the user

**Observation 2 — Form state**:
1. Only `oauth_connection_id` is set on the form (equal to `conn-new`)

**Observation 3 — Cleanup**:
1. `sessionStorage['mcp-form-oauth-draft']` is cleared after handling

---

### TC-ERROR-012: List — 401 unauthorized (FS-15)

**Action**:
1. Visit `/mcp`

**Observation 1 — Empty state**:
1. No infinite spinner
2. Empty state renders (list silently empty)

**API mock**: `POST /mcp-server/list` → 401.

---

### TC-ERROR-013: List — 422 validation (FS-16)

**Action**:
1. Visit `/mcp`

**Observation 1 — Empty state**:
1. Empty state renders
2. No crash

**API mock**: `POST /mcp-server/list` → 422 with array `detail`.

---

### TC-ERROR-014: Upsert — 422 array detail falls back to generic toast (FS-19)

**Action**:
1. Navigate to `/mcp/create`, fill valid form
2. Click Save

**Observation 1 — Fallback toast**:
1. Toast title equals `Something went wrong. Please try again.` (because `detail` is array)

**API mock**: 422 with `detail: [...]`.

---

### TC-ERROR-015: Network failure on save (FS-20 / MCP-013)

**Action**:
1. Navigate to `/mcp/create`, fill valid form
2. Click Save with `route.abort('failed')`

**Observation 1 — Toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Form persists**:
1. User stays on the form
2. Form state is intact

---

### TC-ERROR-016: List — 400 (malformed filter) renders empty grid without spam (MCP-007)

**Action**:
1. Visit `/mcp`

**Observation 1 — Grid state**:
1. Empty grid is rendered
2. No toast spam (list silently empty)
3. No crash

**API mock**: `POST /mcp-server/list` → 400.

---

### TC-ERROR-017: Save 401 surfaces error toast without redirect (MCP-008)

**Preconditions**:
- Token expires between page load and save.

**Action**:
1. Navigate to `/mcp/create` (loaded with valid token), fill form
2. Click Save

**Observation 1 — Toast**:
1. Toast title surfaces `Invalid token` / `Could not validate credentials`

**Observation 2 — Form persists**:
1. Form stays open with state preserved
2. No automatic redirect

**API mock**: `POST /mcp-server/upsert_mcp_server` → 401.

---

### TC-ERROR-018: Upsert 500 server error (MCP-011)

**Action**:
1. Navigate to `/mcp/create`, fill valid form
2. Click Save

**Observation 1 — Toast**:
1. Toast title equals `Internal Server Error` OR default

**Observation 2 — Form persists**:
1. Form stays open with state intact

**API mock**: 500.

---

### TC-ERROR-019: Discover tools — 401 mid-flow (MCP-012)

**Action**:
1. Navigate to `/mcp/[id]/tools`

**Observation 1 — Toast**:
1. Toast surfaces backend detail

**Observation 2 — Tools table empty**:
1. The table renders empty

**API mock**: `GET /mcp-server/discover_tools` → 401.

---

### TC-LOADING-001: Slow save disables button with saving label (MCP-014)

**Action**:
1. Navigate to `/mcp/create`, fill valid form
2. Click Save with ≥3s slow `upsert_mcp_server`

**Observation 1 — Loading state**:
1. Save button is `disabled` throughout
2. Button label is `Saving…` (or `Updating…` on edit)

**Observation 2 — No double-submit**:
1. Multi-clicks yield exactly one upsert request

**API mock**: 200 delayed 3500 ms.

---

### TC-LOADING-002: Slow edit hydration keeps save disabled (MCP-015)

**Action**:
1. Navigate to `/mcp/edit/[id]` with ≥3s slow `get_mcp_server`

**Observation 1 — Hydration state**:
1. Form fields remain blank until hydration completes

**Observation 2 — Save disabled**:
1. Save button is disabled until hydration completes

---

### TC-LOADING-003: Double-click on save does not double-submit (MCP-017)

**Action**:
1. Navigate to `/mcp/create`, fill valid form
2. Click Save twice rapidly

**Observation 1 — Single request**:
1. Exactly one upsert request fires
2. The second click is ignored while `saving` is true

---

### TC-LOADING-004: Rapid refresh tools resolves to the latest response (MCP-018)

**Action**:
1. Open `/mcp/[id]/tools`
2. Click Refresh tools twice rapidly

**Observation 1 — Sequence guard**:
1. `fetchSeqRef.current` increments on each invocation
2. Only the final response renders in the table
3. No flicker between intermediate responses

---

### TC-EDGE-001: Server URL trims surrounding whitespace before submit (MCP-021)

**Action**:
1. Navigate to `/mcp/create`
2. Type ` https://api.clickup.com/mcp ` into Server URL
3. Fill remaining fields
4. Click Save

**Observation 1 — Trimmed payload**:
1. `POST /mcp-server/upsert_mcp_server` body `server_url` equals `https://api.clickup.com/mcp`

---

### TC-EDGE-002: Server Name accepts unicode + html-ish input without XSS (MCP-022)

**Action**:
1. Navigate to `/mcp/create`
2. Enter `__e2e__ 🚀 <script>` into Server Name
3. Fill remaining fields
4. Click Save

**Observation 1 — Round-trip**:
1. The new card displays the unicode + html-ish text as visible text

**Observation 2 — No XSS**:
1. `window.alert` is not invoked
2. No script tag is parsed into the DOM

---

### TC-EDGE-003: Very long server name handled with backend validation (MCP-023)

**Action**:
1. Navigate to `/mcp/create`
2. Enter a >500-char name
3. Fill remaining fields and Save

**Observation 1 — Backend handling**:
1. Either accepted OR backend returns 400/422 with toast detail
2. Form stays open in the error branch

---

### TC-EDGE-004: Malformed server URL surfaces invalid url toast (MCP-024)

**Action**:
1. Navigate to `/mcp/create`
2. Fill Server URL = `not-a-url`
3. Click Save

**Observation 1 — Toast**:
1. Toast title equals `Invalid server URL. Please check the URL and try again.`

---

### TC-EDGE-005: Unreachable server URL surfaces connection error (MCP-025)

**Action**:
1. Navigate to `/mcp/create`
2. Fill Server URL = `https://localhost:9`
3. Click "Auto-discover" / Save (whichever triggers discover_tools)

**Observation 1 — Toast**:
1. Toast title equals `Failed to connect to MCP server: connection refused`

---

### TC-EDGE-006: Empty header key rows are stripped on save (MCP-026)

**Action**:
1. Navigate to `/mcp/create`
2. Add a header row with empty key and a non-empty value
3. Fill required fields
4. Click Save

**Observation 1 — Stripped payload**:
1. `POST upsert_mcp_server` body `meta_data.http_headers` does NOT contain the empty-key row

---

### TC-EDGE-007: Header rows trim whitespace and drop empties (MCP-027)

**Action**:
1. Navigate to `/mcp/create`
2. Add header rows with whitespace-only key + value
3. Click Save

**Observation 1 — Trim + drop**:
1. Body strips empty-after-trim rows
2. Remaining rows are trimmed in both key and value

---

### TC-EDGE-008: Description maxLength enforced by counter (MCP-028)

**Action**:
1. Navigate to `/mcp/create`
2. Paste 1500 chars into Description

**Observation 1 — maxLength**:
1. Input value length is clamped to 1000
2. Counter reads `1000/1000`

---

### TC-EDGE-009: Out-of-range timeout surfaces backend validation (MCP-029)

**Action**:
1. Mutate the timeout slider value via DevTools to an out-of-range number
2. Click Save

**Observation 1 — Toast**:
1. Backend 400 surfaces a detail toast (clamp range `[1, 60]`)

---

### TC-EDGE-010: Concurrent edit handled by last-write or 409 (MCP-016)

**Action**:
1. User A and User B both edit the same server; B saves first, A saves second

**Observation 1 — Outcome**:
1. A's save either succeeds (last-write-wins) OR backend returns 409
2. Toast reflects the backend response

---

### TC-EDGE-011: Pagination disables prev on the first page (MCP-032)

**Action**:
1. Visit `/mcp`

**Observation 1 — Prev disabled**:
1. The Previous control is disabled (or absent if all items fit on a page)

---

### TC-EDGE-012: Pagination disables next on the last page (MCP-033)

**Action**:
1. Visit `/mcp`
2. Navigate to the last page

**Observation 1 — Next disabled**:
1. Next control is disabled
2. Previous control is enabled

---

### TC-EDGE-013: Sort by date orders rows appropriately (MCP-034)

**Action**:
1. Visit `/mcp`
2. Select Newest, then Oldest

**Observation 1 — Refetch with sort**:
1. `POST /mcp-server/list` fires with `sort: '-created_at'` for Newest
2. `POST /mcp-server/list` fires with `sort: 'created_at'` for Oldest

---

### TC-EDGE-014: Sort by name cycles asc and desc (MCP-035)

**Action**:
1. Visit `/mcp`
2. Select Name A–Z, then Name Z–A

**Observation 1 — Refetch with sort_by**:
1. Request body uses `sort_by: 'name'` with `asc` then `desc`

---

### TC-EDGE-015: Sort by recently updated orders descending (MCP-036)

**Action**:
1. Visit `/mcp`
2. Select Recently updated

**Observation 1 — Refetch**:
1. Request body uses `sort: '-updated_at'`

---

### TC-EDGE-016: Whitespace-only search treated as empty (MCP-037)

**Action**:
1. Type `   ` into the search bar

**Observation 1 — Empty search**:
1. List request is sent with an empty search
2. List reverts to default sort

---

### TC-EDGE-017: Clear filters resets state (MCP-038)

**Action**:
1. Apply a search/filter
2. Click "Clear filters"

**Observation 1 — Reset**:
1. All toolbar filters reset
2. `POST /mcp-server/list` re-fires without filters

---

### TC-EDGE-018: Dashed new server card appears as final tile (MCP-039)

**Preconditions**:
- At least one server exists.

**Action**:
1. Visit `/mcp`

**Observation 1 — Final tile**:
1. The dashed "+ New MCP Server" card is the last tile in the grid

---

### TC-EDGE-019: Validate connection success reflected in UI (MCP-040)

**Action**:
1. Click "Auto-discover" with a valid URL

**Observation 1 — Validation success**:
1. `validate_mcp_server` OR `discoverMcpOAuth` fires
2. UI reflects success (tools count / OAuth URL ready)

---

### TC-EDGE-020: Validate connection failure clears discovering state (MCP-041)

**Action**:
1. Click "Auto-discover" with a malformed URL

**Observation 1 — Backend toast**:
1. Toast title equals `Invalid server URL. Please check the URL and try again.`

**Observation 2 — Discovering cleared**:
1. The in-flight `discovering` UI state clears

---

### TC-EDGE-021: Tool list refreshes after server change (MCP-044)

**Action**:
1. Edit a server's URL and Save
2. Revisit `/mcp/<id>/tools`

**Observation 1 — Refetch**:
1. `discover_tools` re-fires with the new URL

---

### TC-EDGE-022: Attach to agent updates agent tools list (MCP-045)

**Action**:
1. Call `POST /mcp-server/attach_mcp_server_to_agents` with `agent_ids` + `selected_tools`

**Observation 1 — Agent updated**:
1. The agent's tools list contains the attached MCP tools

---

### TC-EDGE-023: Detach from agent removes tools from agent (MCP-046)

**Action**:
1. Call `DELETE /mcp-server/detach_mcp_server_from_agents` with `agent_ids`

**Observation 1 — Agent updated**:
1. The agent's tools list no longer contains the detached MCP tools

---

### TC-EDGE-024: Pending OAuth connections not selectable (MCP-049)

**Preconditions**:
- An OAuth connection with `public_metadata.status === 'pending'` exists.

**Action**:
1. Navigate to `/mcp/create`
2. Open the OAuth connection dropdown

**Observation 1 — Pending hidden**:
1. The pending connection is not in the dropdown options

---

### TC-NAV-001: Unauthenticated visit redirects to login (FS-17 / MCP-001)

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/mcp`

**Observation 1 — Redirect**:
1. Middleware 307 redirects to `/auth/login?redirect=%2Fmcp`

---

### TC-NAV-002: Unauthenticated create page redirects to login (MCP-002)

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/mcp/create`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmcp%2Fcreate`

---

### TC-NAV-003: Unauthenticated edit deep link redirects to login (MCP-003)

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/mcp/edit/<id>`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmcp%2Fedit%2F<id>`

---

### TC-NAV-004: Unauthenticated tools deep link redirects to login (MCP-004)

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/mcp/<id>/tools`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmcp%2F<id>%2Ftools`

---

### TC-NAV-005: Expired token redirects to login and clears cookie (MCP-005)

**Preconditions**:
- Expired token cookie.

**Action**:
1. Visit `/mcp`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmcp`

**Observation 2 — Cookie cleared**:
1. The expired cookie is removed

---

### TC-NAV-006: Member role delete surfaces forbidden toast (MCP-006)

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Click ⋮ on a card → Delete → confirm

**Observation 1 — Toast**:
1. Toast title equals `Admin or Owner role required`

**Observation 2 — Card persists**:
1. The card remains in the grid

**API**: `DELETE` → 403.

---

### TC-NAV-007: Reserved sub-routes redirect to mcp list (FS-18 / MCP-050)

**Action**:
1. Visit `/mcp/create/tools`
2. Visit `/mcp/edit/tools`

**Observation 1 — Both redirect**:
1. URL becomes `/mcp` in both cases
2. No API call fires

---

### TC-NAV-008: Invalid tools deep link redirects to list after 404 (FS-18 / MCP-051)

**Action**:
1. Visit `/mcp/[invalid-uuid]/tools`

**Observation 1 — getMcpServer fails**:
1. `GET /mcp-server/get_mcp_server` returns 404

**Observation 2 — Redirect**:
1. `useEffect` in `MCPToolsListPage` redirects to `/mcp`

---

### TC-NAV-009: Cancel on create returns to list (MCP-061)

**Action**:
1. Navigate to `/mcp/create`
2. Click Cancel

**Observation 1 — Return URL**:
1. URL becomes `/mcp`

**Observation 2 — State discarded**:
1. Form state is not persisted

---

### TC-NAV-010: Browser back from edit returns to list (MCP-062)

**Action**:
1. Navigate to `/mcp/edit/<id>`
2. Press browser Back

**Observation 1 — Return URL**:
1. URL becomes `/mcp`

**Observation 2 — List state preserved**:
1. The previously rendered list is visible

---

### TC-NAV-011: Reload on edit page rehydrates the form (MCP-063)

**Action**:
1. Navigate to `/mcp/edit/<id>`
2. Reload the page

**Observation 1 — Refetch**:
1. `GET /mcp-server/get_mcp_server` re-fires

**Observation 2 — Form rehydrates**:
1. All form fields are repopulated

---

### TC-NAV-012: Back arrow on tools page returns to list (MCP-064)

**Action**:
1. Visit `/mcp/<id>/tools`
2. Click the back arrow

**Observation 1 — Return URL**:
1. URL becomes `/mcp`

**Observation 2 — State preserved**:
1. The list state is preserved

---

### TC-NAV-013: Cross-link to attached agent navigates correctly (MCP-065)

**Preconditions**:
- The MCP server is attached to an agent.

**Action**:
1. From the tools page, click an attached-agent link (if supported)

**Observation 1 — Navigation**:
1. URL becomes the agent edit page

---

### TC-A11Y-001: Tab order through MCP form reaches every control (MCP-052)

**Action**:
1. Navigate to `/mcp/create`
2. Tab through the form

**Observation 1 — Tab order**:
1. Focus moves Name → Description → Active toggle → Server URL → Transport radio → Timeout → Headers → Auth toggles → OAuth select → Cancel → Save

---

### TC-A11Y-002: Enter in server name submits the form when valid (MCP-053)

**Action**:
1. Navigate to `/mcp/create`
2. Fill all required fields
3. Focus Server Name, press Enter

**Observation 1 — Submit**:
1. Exactly one upsert request fires

---

### TC-A11Y-003: Error toast does not steal focus from form (MCP-054)

**Action**:
1. Trigger a save error

**Observation 1 — Focus stays**:
1. Focus remains on the Save button

**Observation 2 — Toast announcement**:
1. The toast is announced via `aria-live`

---

### TC-A11Y-004: Action menu trigger exposes accessible name (MCP-055)

**Action**:
1. Inspect a card's action menu trigger

**Observation 1 — ARIA**:
1. The trigger has `aria-label="Server actions"` (or equivalent accessible name)

---

### TC-A11Y-005: Status pill exposes readable text (MCP-056)

**Action**:
1. Inspect a card status pill

**Observation 1 — Text content**:
1. The pill contains the literal text `Live` or `Paused`

---

### TC-A11Y-006: Switches expose accessible state (MCP-057)

**Action**:
1. Open the create form
2. Inspect Active / Bearer / API key switches

**Observation 1 — ARIA**:
1. Each switch exposes `aria-checked`
2. Each switch has a visible label

---

### TC-A11Y-007: Timeout slider exposes value to screen readers (MCP-058)

**Action**:
1. Open the create form
2. Focus the Timeout slider

**Observation 1 — Accessible name / value**:
1. Slider exposes the current value as text (e.g. "Timeout: 20 seconds")

---

### TC-A11Y-008: Search input has accessible name (MCP-059)

**Action**:
1. Visit `/mcp`
2. Inspect the search input

**Observation 1 — Label / aria-label**:
1. The search input has an associated label or `aria-label`

---

### TC-A11Y-009: Card link is keyboard activatable (MCP-060)

**Action**:
1. Tab to a server card
2. Press Enter

**Observation 1 — Activation**:
1. The card itself is a real `<a>` link
2. URL navigates to `/mcp/[id]/tools`

---

### TC-FULL-001: Lifecycle — walk create validate attach detach delete of an MCP server end to end (MCP-FULL)

**Preconditions**:
- Authenticated via `loginViaUI`.

**Action**:
1. Visit `/mcp`
2. Assert headings + Create CTA + dashed card
3. Click "Create MCP Server"
4. Fill Server Name `__e2e__ clickup_mcp`, Server URL `https://api.clickup.com/mcp`
5. Leave Streamable HTTP default + timeout 20
6. Click Save
7. Click the new card
8. Click "Refresh tools"
9. Click the back arrow
10. Open action menu → Edit
11. Change description to `__e2e__ updated`
12. Save
13. Seed an `__e2e__` agent via API
14. Attach the MCP server to the agent via API
15. Revisit the agent's tools tab
16. Detach via API
17. Return to `/mcp`
18. Open action menu → Delete
19. Cleanup any residual data (agent, MCP server) via API in `try/finally`

**Observation 1 — Initial page**:
1. Heading `MCP Servers` visible
2. "Create MCP Server" CTA visible
3. Dashed "+ New MCP Server" card visible

**Observation 2 — Create success**:
1. `POST /mcp-server/upsert_mcp_server` body contains the typed name + URL
2. Toast title `MCP server created successfully`
3. URL becomes `/mcp`
4. The new `__e2e__ clickup_mcp` card is visible

**Observation 3 — Tools page**:
1. URL becomes `/mcp/<id>/tools`
2. Header shows back arrow + transport badge + status badge
3. Clicking Refresh fires another `GET /mcp-server/discover_tools`

**Observation 4 — Edit success**:
1. `POST /mcp-server/upsert_mcp_server` body contains the existing `id` + new description
2. Toast title `MCP server updated successfully`
3. URL becomes `/mcp`

**Observation 5 — Attach reflects in agent**:
1. `POST /mcp-server/attach_mcp_server_to_agents` succeeds
2. The agent's tools list contains the new MCP tools

**Observation 6 — Detach reflects in agent**:
1. `DELETE /mcp-server/detach_mcp_server_from_agents` succeeds
2. The agent's tools list no longer contains those tools

**Observation 7 — Delete success**:
1. `DELETE /mcp-server/delete_mcp_server?mcp_server_id=<id>` fires
2. Toast title `MCP server deleted successfully`
3. Card removed from the grid

**Observation 8 — Cleanup**:
1. The cleanup block runs even if assertions fail
2. No `__e2e__` residue (agent or server) remains after the test

---

## Expected Toast Messages

Sonner toast titles + descriptions from `MCPListPage.tsx`, `MCPFormPage.tsx`, `MCPToolsListPage.tsx`, `src/utils/toast.tsx`, `src/utils/helpers.ts`.

| Trigger                                                    | Toast title                                          | Variant |
| ---------------------------------------------------------- | ---------------------------------------------------- | ------- |
| Create success                                              | `MCP server created successfully`                    | success |
| Update success                                              | `MCP server updated successfully`                    | success |
| Delete success                                              | `MCP server deleted successfully`                    | success |
| Save server form error (any API failure)                    | (server `detail` string OR `Something went wrong. Please try again.`) | error   |
| Auto-discover OAuth — empty URL guard                       | `Enter the server URL first`                         | error   |
| Auto-discover OAuth — API throws                            | (server `detail` string OR `Something went wrong. Please try again.`) | error   |
| Discover tools — failure                                    | (server `detail` string OR default)                  | error   |
| Get MCP server (load on tools page) — failure               | (server `detail` string OR default)                  | error   |
| List — failure                                              | (none — list silently empty)                         | —       |

---

## Edge Cases (each appears as a `TC-EDGE-*` or related test case above)

- [x] Unauthenticated access → middleware redirect — TC-NAV-001..004
- [ ] Favicon load failure → fallback to Server icon on sky-500 background — not yet covered ⚠
- [ ] Description missing → italic placeholder — not yet covered ⚠
- [x] Reserved segments `create/tools` and `edit/tools` → TC-NAV-007
- [x] Invalid `[id]` on `/mcp/[id]/tools` → TC-NAV-008
- [x] Discover tools call fails → TC-ERROR-008..009
- [x] OAuth flow mid-form — TC-HAPPY-013
- [ ] Timeout slider value clamped — partially covered TC-EDGE-009 ⚠
- [x] Filtering with no matches vs. no servers at all → TC-HAPPY-003 + TC-HAPPY-004
- [ ] Inactive server → status pill reads "Paused" — covered via TC-HAPPY-002 transport/badge assertion
- [x] Headers builder strip-on-save — TC-EDGE-006, TC-EDGE-007
- [ ] Long server URL — not yet covered ⚠
- [ ] Bulk-delete partial failure — N/A (no bulk-delete UI today)
- [x] Discovery polling — TC-LOADING-004
- [ ] sessionStorage key collision — not yet covered ⚠
- [x] Auto-discover empty URL inline toast — TC-VALIDATE-005
- [ ] `is_active` flip timing — not yet covered ⚠
- [x] Sequence guard on tools page — TC-LOADING-004
- [x] Header builder strip-on-save — TC-EDGE-006
- [x] Pending OAuth connections filtered — TC-EDGE-024

---

## Business Rules

- Two transport types are supported: `streamable_http` and `sse`. The form enforces one or the other.
- Auth options are mutually compatible — a server can have headers + bearer + api-key + OAuth at the same time; backend chooses precedence at runtime.
- An `oauth_connection_id` on an MCP server cross-references `oauth_connections` (see `oauth-integrations.md`). Disconnecting that OAuth connection invalidates the MCP server's auth.
- Card hover styling is purely visual; cards remain clickable on focus.
- The frontend never sees the discovered tools schema until `discover_tools` is explicitly called — there is no auto-discovery on list view.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] All card actions are keyboard reachable; the card itself is a real `<a>` link — TC-A11Y-009
- [x] Action menu trigger has an accessible label — TC-A11Y-004
- [x] Slider exposes value as text for screen readers — TC-A11Y-007
- [x] Switches have visible labels and announce state — TC-A11Y-006
- [x] Status pill includes text, not just color — TC-A11Y-005
- [ ] Modals/forms trap focus and restore it on close/cancel — Radix/shadcn default; not yet a dedicated TC ⚠
- [x] Search inputs have associated labels — TC-A11Y-008

---

## Mapping: old scenario IDs → new TC IDs

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| WF-1            | TC-HAPPY-001      | browse MCP servers list                                              |
| PS-1            | TC-HAPPY-002      | list renders 2 cards plus dashed new server card                     |
| PS-2            | TC-HAPPY-003      | empty list shows the no-servers empty state                          |
| PS-3            | TC-HAPPY-004      | empty list with active filters shows the no-matches state            |
| WF-1 step 3     | TC-HAPPY-005      | sort by Name A–Z refetches list                                      |
| WF-1 step 4     | TC-HAPPY-006      | search by token                                                      |
| WF-2 / PS-4     | TC-HAPPY-007      | create a new MCP server                                              |
| WF-3 / PS-5     | TC-HAPPY-008      | edit an existing MCP server                                          |
| WF-4 / PS-6     | TC-HAPPY-009      | discover tools                                                       |
| WF-4 step 3     | TC-HAPPY-010      | tools client-side filter                                             |
| MCP-043         | TC-HAPPY-011      | refresh tools button re-fetches tool list                            |
| WF-5 / PS-7     | TC-HAPPY-012      | delete a server                                                      |
| WF-6 / PS-8 / MCP-047 | TC-HAPPY-013 | oauth round trip restores form and clears draft                      |
| PS-9            | TC-HAPPY-014      | reserved segment redirect                                            |
| FS-1 / MCP-019  | TC-VALIDATE-001   | create — missing name                                                |
| FS-2 / MCP-020  | TC-VALIDATE-002   | create — missing server URL                                          |
| MCP-019 (ws)    | TC-VALIDATE-003   | whitespace-only server name is rejected                              |
| MCP-020 (ws)    | TC-VALIDATE-004   | whitespace-only server url is rejected                               |
| FS-12 / MCP-042 | TC-VALIDATE-005   | auto-discover OAuth — empty server URL                               |
| FS-3 / MCP-010  | TC-ERROR-001      | create — server-side duplicate name (409)                            |
| FS-4 / MCP-024  | TC-ERROR-002      | create — invalid URL (400)                                           |
| FS-5            | TC-ERROR-003      | create — auth failed (400)                                           |
| FS-6            | TC-ERROR-004      | create — invalid transport_type (400)                                |
| FS-7            | TC-ERROR-005      | edit — 404 on load                                                   |
| FS-8            | TC-ERROR-006      | edit — 404 on save                                                   |
| FS-9 / MCP-009  | TC-ERROR-007      | delete — 404                                                         |
| FS-10           | TC-ERROR-008      | discover tools — connection refused (400)                            |
| FS-11           | TC-ERROR-009      | discover tools — server not found (404)                              |
| FS-13           | TC-ERROR-010      | auto-discover OAuth — backend error                                  |
| FS-14 / MCP-048 | TC-ERROR-011      | OAuth round-trip with corrupted draft                                |
| FS-15           | TC-ERROR-012      | list — 401 unauthorized                                              |
| FS-16           | TC-ERROR-013      | list — 422 validation                                                |
| FS-19           | TC-ERROR-014      | upsert — 422 array detail falls back to generic toast                |
| FS-20 / MCP-013 | TC-ERROR-015      | network failure on save                                              |
| MCP-007         | TC-ERROR-016      | list — 400 (malformed filter)                                        |
| MCP-008         | TC-ERROR-017      | save 401 surfaces error toast without redirect                       |
| MCP-011         | TC-ERROR-018      | upsert 500 server error                                              |
| MCP-012         | TC-ERROR-019      | discover tools — 401 mid-flow                                        |
| MCP-014         | TC-LOADING-001    | slow save disables button with saving label                          |
| MCP-015         | TC-LOADING-002    | slow edit hydration keeps save disabled                              |
| MCP-017         | TC-LOADING-003    | double-click on save does not double-submit                          |
| MCP-018         | TC-LOADING-004    | rapid refresh tools resolves to the latest response                  |
| MCP-021         | TC-EDGE-001       | server url trims surrounding whitespace before submit                |
| MCP-022         | TC-EDGE-002       | server name accepts unicode and html-ish input without xss           |
| MCP-023         | TC-EDGE-003       | very long server name handled with backend validation                |
| MCP-024         | TC-EDGE-004       | malformed server url surfaces invalid url toast                      |
| MCP-025         | TC-EDGE-005       | unreachable server url surfaces connection error                     |
| MCP-026         | TC-EDGE-006       | empty header key rows are stripped on save                           |
| MCP-027         | TC-EDGE-007       | header rows trim whitespace and drop empties                         |
| MCP-028         | TC-EDGE-008       | description maxLength enforced by counter                            |
| MCP-029         | TC-EDGE-009       | out-of-range timeout surfaces backend validation                     |
| MCP-016         | TC-EDGE-010       | concurrent edit handled by last-write or 409                         |
| MCP-032         | TC-EDGE-011       | pagination disables prev on the first page                           |
| MCP-033         | TC-EDGE-012       | pagination disables next on the last page                            |
| MCP-034         | TC-EDGE-013       | sort by date orders rows appropriately                               |
| MCP-035         | TC-EDGE-014       | sort by name cycles asc and desc                                     |
| MCP-036         | TC-EDGE-015       | sort by recently updated orders descending                           |
| MCP-037         | TC-EDGE-016       | whitespace-only search treated as empty                              |
| MCP-038         | TC-EDGE-017       | clear filters resets state                                           |
| MCP-039         | TC-EDGE-018       | dashed new server card appears as final tile                         |
| MCP-040         | TC-EDGE-019       | validate connection success reflected in ui                          |
| MCP-041         | TC-EDGE-020       | validate connection failure clears discovering state                 |
| MCP-044         | TC-EDGE-021       | tool list refreshes after server change                              |
| MCP-045         | TC-EDGE-022       | attach to agent updates agent tools list                             |
| MCP-046         | TC-EDGE-023       | detach from agent removes tools from agent                           |
| MCP-049         | TC-EDGE-024       | pending oauth connections not selectable                             |
| FS-17 / MCP-001 | TC-NAV-001        | unauthenticated visit redirects to login                             |
| MCP-002         | TC-NAV-002        | unauthenticated create page redirects to login                       |
| MCP-003         | TC-NAV-003        | unauthenticated edit deep link redirects to login                    |
| MCP-004         | TC-NAV-004        | unauthenticated tools deep link redirects to login                   |
| MCP-005         | TC-NAV-005        | expired token redirects to login and clears cookie                   |
| MCP-006         | TC-NAV-006        | member role delete surfaces forbidden toast                          |
| FS-18 / MCP-050 | TC-NAV-007        | reserved sub-routes redirect to mcp list                             |
| FS-18 / MCP-051 | TC-NAV-008        | invalid tools deep link redirects to list after 404                  |
| MCP-061         | TC-NAV-009        | cancel on create returns to list                                     |
| MCP-062         | TC-NAV-010        | browser back from edit returns to list                               |
| MCP-063         | TC-NAV-011        | reload on edit page rehydrates the form                              |
| MCP-064         | TC-NAV-012        | back arrow on tools page returns to list                             |
| MCP-065         | TC-NAV-013        | cross-link to attached agent navigates correctly                     |
| MCP-052         | TC-A11Y-001       | tab order through mcp form reaches every control                     |
| MCP-053         | TC-A11Y-002       | Enter in server name submits the form when valid                     |
| MCP-054         | TC-A11Y-003       | error toast does not steal focus from form                           |
| MCP-055         | TC-A11Y-004       | action menu trigger exposes accessible name                          |
| MCP-056         | TC-A11Y-005       | status pill exposes readable text                                    |
| MCP-057         | TC-A11Y-006       | switches expose accessible state                                     |
| MCP-058         | TC-A11Y-007       | timeout slider exposes value to screen readers                       |
| MCP-059         | TC-A11Y-008       | search input has accessible name                                     |
| MCP-060         | TC-A11Y-009       | card link is keyboard activatable                                    |
| MCP-FULL        | TC-FULL-001       | walks create validate attach detach delete of an mcp server end to end |
