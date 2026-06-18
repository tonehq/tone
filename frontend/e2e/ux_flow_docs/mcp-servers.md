# Feature Doc: MCP Servers

Feature documentation for the MCP Servers list + create/edit/detail pages. Used
by `/generate-tests mcp-servers` (or `--docs e2e/ux_flow_docs/mcp-servers.md`) to ensure
all user cases are covered.

An **MCP Server** (Model Context Protocol) is a per-organization registration
of an external tool server. Agents attach MCP servers so the LLM can call the
remote tools at runtime.

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

**As an** agent owner, **I want to** see all MCP servers my org has registered,
**so that** I know which external tool servers are available to attach.

**Acceptance criteria**:

- [ ] Page header shows "MCP Servers" (h1) + subtitle "Connect Model Context Protocol servers to extend your agents with external tools and resources."
- [ ] Primary CTA "Create MCP Server" appears in the header
- [ ] Filter toolbar: search placeholder "Search MCP servers… (e.g. name:clickup)" + sort dropdown (Newest / Oldest / Name A–Z / Name Z–A / Recently updated)
- [ ] List renders as a 3-column responsive card grid
- [ ] Each card shows: favicon (from server URL with fallback to a Server icon on sky-500), name, hostname, 2-line clamped description, transport-type badge (Streamable HTTP / SSE), status pill (Live with green ping / Paused), action menu (⋮ Edit / Delete)
- [ ] Loading state: card-grid skeletons
- [ ] A dashed "+ New MCP Server" card always appears at the end of the grid

### US-2: Create a new MCP server

**As an** agent owner, **I want to** register a new MCP server URL with auth
and timeout, **so that** my agents can later attach and discover its tools.

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

**As an** agent owner, **I want to** edit name, URL, headers, auth, or
timeout on an existing server, **so that** I can fix mistakes or rotate
credentials without recreating it.

**Acceptance criteria**:

- [ ] "Edit" from the card action menu navigates to `/mcp/edit/[id]`
- [ ] Form loads with all fields pre-populated from `GET /mcp-server/get_mcp_server`
- [ ] "Update server" calls `POST /mcp-server/upsert_mcp_server` with the existing id
- [ ] Reserved URL segments (`/mcp/create/tools`, `/mcp/edit/tools`) redirect to `/mcp`

### US-4: Inspect discovered tools

**As an** agent owner, **I want to** see which tools an MCP server exposes,
**so that** I know what capabilities the agent will gain when attached.

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

**As an** org admin, **I want to** delete a registration I no longer need,
**so that** it can't be attached to new agents by mistake.

**Acceptance criteria**:

- [ ] "Delete" from the card action menu calls `DELETE /mcp-server/delete_mcp_server`
- [ ] Card is removed from the list on success
- [ ] Deleting a server attached to agents is blocked by the backend (or detaches the binding, depending on backend rules); the response is surfaced via `handleApiError`

### US-6: OAuth flow without losing form state

**As an** agent owner, **I want to** start an OAuth flow from the MCP form and
return to the same form with my draft intact, **so that** I don't re-enter
everything.

**Acceptance criteria**:

- [ ] When the user triggers OAuth from the Auth section, the form snapshot is written to `sessionStorage` under key `mcp-form-oauth-draft`
- [ ] On return from OAuth, the form restores its prior fields and the new OAuth connection is selectable in the dropdown
- [ ] Successful save clears the draft

---

## User Workflow Steps

Step-by-step actions per major flow. Drives `test(...)` blocks in `e2e/dashboard/mcp.spec.ts`. Toast assertions use `page.locator('[data-sonner-toast]')`.

**WF-1: Browse MCP servers** (positive — US-1)

1. User authenticates via `loginViaUI(page)` then navigates to `/mcp` → expected: heading "MCP Servers", description visible, "Create MCP Server" primary button visible.
2. With `/mcp-server/list` returning two servers → expected: 3-column card grid renders, each card shows favicon, name, hostname, transport badge ("Streamable HTTP" / "SSE") and status pill ("Live" / "Paused"). A dashed "+ New MCP Server" card appears at the end of the grid.
3. User changes sort dropdown to "Name A–Z" → expected: list re-fetches with `sort_by: "name", sort_order: "asc"`.
4. User types `name:clickup` into the search bar → expected: list re-fetches with `search_query` reflecting the token.

**WF-2: Create a new MCP server** (positive — US-2)

1. User clicks "Create MCP Server" → expected: route navigates to `/mcp/create`, top bar shows "New MCP Server" + status pill "Active".
2. User fills "Server Name" = `clickup_mcp`, "Server URL" = `https://api.clickup.com/mcp` → expected: the rail preview hostname becomes `api.clickup.com`.
3. User picks transport "Streamable HTTP" (default), leaves timeout at 20 → expected: the chip row reads `SHTTP`, `20s timeout`, `None auth`, `0 headers`.
4. User toggles "Use Bearer Token" on and enters `sk-bearer-xxx` → expected: rail "Auth" becomes `Bearer`.
5. User clicks "Save" → expected: `POST /mcp-server/upsert_mcp_server` fires; on 200, toast title `MCP server created successfully`, redirected to `/mcp`.

**WF-3: Edit an existing MCP server** (positive — US-3)

1. User clicks ⋮ on a card → "Edit" → expected: route navigates to `/mcp/edit/[id]`; `GET /mcp-server/get_mcp_server?mcp_server_id=<id>` fires; form fields hydrate.
2. User edits the description, clicks "Save Changes" → expected: `POST /mcp-server/upsert_mcp_server` with `{ id, ...payload }`; on 200, toast title `MCP server updated successfully`, redirect to `/mcp`.

**WF-4: Discover tools** (positive — US-4)

1. User clicks a card → expected: route navigates to `/mcp/[id]/tools`; `GET /mcp-server/get_mcp_server` and `GET /mcp-server/discover_tools` both fire.
2. With tools returned → expected: table renders with columns Name, Method (`POST` badge), Params count chip, Required count chip; total badge in header shows the count.
3. User types `name:get_account` in the search bar → expected: client-side filter, only matching rows visible.
4. User clicks "Refresh" → expected: `discover_tools` re-fires.

**WF-5: Delete an MCP server** (positive — US-5)

1. User clicks ⋮ → "Delete" → expected: `DELETE /mcp-server/delete_mcp_server?mcp_server_id=<id>` fires; on 200, toast title `MCP server deleted successfully`; card removed and list refetched.

**WF-6: OAuth round-trip with sessionStorage draft** (positive — US-6)

1. User opens `/mcp/create`, fills in name + server URL + headers → expected: `sessionStorage["mcp-form-oauth-draft"]` is empty.
2. User clicks "Auto-discover" → expected: a snapshot of the current form values is written under `sessionStorage["mcp-form-oauth-draft"]`; the browser is redirected to the provider's authorize URL.
3. On return to `/mcp/create?mcp_oauth=success&connection_id=<new>` → expected: the form is restored from the draft, `oauth_connection_id` is pre-set to the new connection, `sessionStorage` key is cleared, and the query params are stripped via `history.replaceState`.
4. User clicks "Save" → expected: payload includes `oauth_connection_id`; success toast shown; draft remains cleared.

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
| Use Bearer Token       | checkbox  | no       | When ON, `bearer_token` text input appears; trim-non-empty → saved under `auth_config.bearer_token`                | (none — empty saved as null)                                               |
| Bearer Token           | password  | conditional | Required-feel when Bearer toggle is ON; empty just omits the field                                            | Backend: `Authentication failed. Please check your token or API key and try again.` |
| Use API Key            | checkbox  | no       | When ON, `api_key` text input appears; trim-non-empty → saved under `auth_config.api_key`                          | (none)                                                                     |
| OAuth connection       | select    | no       | Default `__none__` (sentinel); selected connections with `status=='pending'` are filtered out                      | (none)                                                                     |
| HTTP Headers           | repeater  | no       | Rows with empty `key` are stripped at save time; whitespace `.trim()`'d                                            | (none — silent strip)                                                      |
| is_active              | switch    | no       | Default ON; controls `is_active` field                                                                            | (none)                                                                     |

OAuth discovery extra guard: clicking "Auto-discover" with an empty `server_url` → inline toast `Enter the server URL first` (`showToast.error('Enter the server URL first')`).

### Tools page (`MCPToolsListPage.tsx`)

| Field   | Type  | Required | Validation                                                  | Error                |
| ------- | ----- | -------- | ----------------------------------------------------------- | -------------------- |
| Search  | token | no       | Single token of `field: 'name'`; client-side filter only    | (no validation)      |

---

## Success Scenarios

**PS-1: List renders 2 cards plus the dashed "+ New MCP Server" card** (US-1) — mock `POST **/mcp-server/list`:
```json
{
  "data": [
    {"id": "11111111-...", "name": "sales-mcp", "description": "Sales CRM tools", "server_url": "https://sales-mcp.acme.com", "transport_type": "streamable_http", "auth_config": {"token": "sk-..."}, "meta_data": {"timeout": 30}, "oauth_connection_id": null, "is_active": true, "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"},
    {"id": "22222222-...", "name": "clickup_mcp", "description": "ClickUp tasks", "server_url": "https://api.clickup.com/mcp", "transport_type": "sse", "auth_config": null, "meta_data": {"timeout": 20}, "oauth_connection_id": "oauth-1", "is_active": false, "created_at": "2026-05-27T11:00:00+00:00", "updated_at": "2026-05-27T11:00:00+00:00"}
  ],
  "pagination": {"page": 1, "page_size": 20, "total": 2, "total_pages": 1}
}
```
Expected UI: 2 cards (one Live, one Paused), badges "Streamable HTTP" + "SSE" visible, dashed "+ New MCP Server" tile at the end.

**PS-2: Empty list shows the no-servers empty state** (US-1) — mock returns `{"data": [], "pagination": {...total: 0}}` → expected: `MCPEmptyState` rendered with "Create MCP Server" CTA. Toolbar is hidden.

**PS-3: Empty list with active filters shows the no-matches state** (US-1) — list returns `total: 0` but `hasActiveFilters` is true → expected: text `No MCP servers match your filters` + "Clear filters" link.

**PS-4: Create server success** (US-2) — `POST **/mcp-server/upsert_mcp_server` returns 200:
```json
{"id":"new-srv-1","name":"clickup_mcp","description":"","server_url":"https://api.clickup.com/mcp","transport_type":"streamable_http","auth_config":{"bearer_token":"sk-..."},"meta_data":{"timeout":20,"http_headers":{}},"oauth_connection_id":null,"is_active":true,"created_at":"2026-06-17T10:00:00+00:00","updated_at":"2026-06-17T10:00:00+00:00"}
```
Expected: toast title `MCP server created successfully`; route changes to `/mcp`.

**PS-5: Edit server success** (US-3) — `GET /mcp-server/get_mcp_server` hydrates the form; `POST /mcp-server/upsert_mcp_server` with `{id, ...}` returns 200 → toast `MCP server updated successfully`; redirected to `/mcp`.

**PS-6: Discover tools success** (US-4) — `GET **/mcp-server/discover_tools?mcp_server_id=...` returns 200:
```json
{"server_name":"sales-mcp","server_url":"https://sales-mcp.acme.com/mcp","transport_type":"streamable_http","tools":[{"name":"get_account","description":"Look up an account","parameters":{"type":"object","properties":{"id":{"type":"string"}}},"required":["id"]},{"name":"list_deals","description":"List open deals","parameters":{"type":"object","properties":{}},"required":[]}],"tool_count":2}
```
Expected: table has 2 rows, total badge shows `2`, param chips show `1 param` / `0` (em-dash), required chips show `1 required` / `0`.

**PS-7: Delete server success** (US-5) — `DELETE /mcp-server/delete_mcp_server?mcp_server_id=<id>` returns `{"message":"MCP server deleted successfully"}` → toast title `MCP server deleted successfully`; list refetches; card disappears.

**PS-8: OAuth draft round-trip** (US-6) — sessionStorage write/read assertions:
- Before clicking Auto-discover: `await page.evaluate(() => sessionStorage.getItem('mcp-form-oauth-draft'))` returns `null`.
- After clicking Auto-discover (mocked `discoverMcpOAuth` returns a `https://provider.example/authorize?...` URL): sessionStorage contains a JSON snapshot of the form state.
- Re-navigating to `/mcp/create?mcp_oauth=success&connection_id=conn-new`: the form fields are restored; `oauth_connection_id` equals `conn-new`; sessionStorage cleared; URL query params stripped (`page.url()` equals `http://localhost:3000/mcp/create`).

**PS-9: Reserved segment redirect** — visiting `/mcp/create/tools` or `/mcp/edit/tools` → redirects to `/mcp` (per US-3 acceptance criteria).

---

## Failure Scenarios

**FS-1: Create — missing name (RHF inline)** — leave Server Name blank, click Save → expected: inline error text below the field reads `Server name is required`; no network call.

**FS-2: Create — missing server URL (RHF inline)** — fill name only, click Save → expected: inline error `Server URL is required`; no network call.

**FS-3: Create — server-side duplicate name (409)** — mock `POST **/mcp-server/upsert_mcp_server` returns 409:
```json
{"detail":"An MCP server with name 'sales-mcp' already exists in this organization"}
```
Expected: toast title is that exact detail string; user remains on `/mcp/create` with the form state intact.

**FS-4: Create — invalid URL (400)** — mock returns `{"detail":"Invalid server URL. Please check the URL and try again."}` → expected: toast with that detail string.

**FS-5: Create — auth failed (400)** — mock returns `{"detail":"Authentication failed. Please check your token or API key and try again."}` → expected: toast with that detail.

**FS-6: Create — invalid transport_type (400)** — mock returns `{"detail":"Invalid transport_type 'websocket'. Must be one of: sse, streamable_http"}` (only reachable by API-level mutation; the form constrains transport_type) → toast.

**FS-7: Edit — 404 on load** — mock `GET /mcp-server/get_mcp_server` returns 404 `{"detail":"MCP server not found"}` → expected: toast `MCP server not found`; form shows default values (per `useForm` defaults).

**FS-8: Edit — 404 on save** — mock upsert returns 404 → expected: toast `MCP server not found`; user remains on `/mcp/edit/[id]`.

**FS-9: Delete — 404** — mock `DELETE` returns 404 `{"detail":"MCP server not found"}` → expected: toast with detail; card remains (the row was removed optimistically by `fl.refresh()`, but server state proves the row stays — assertion is the toast title).

**FS-10: Discover tools — connection refused (400)** — mock `GET /mcp-server/discover_tools` returns 400:
```json
{"detail":"Failed to connect to MCP server: connection refused"}
```
Expected: toast title is that detail; tools table shows the `No tools available` empty state (NOT `No tools match your search`, since `hasFilter` is false).

**FS-11: Discover tools — server not found (404)** — mock returns 404 `{"detail":"MCP server not found"}` → expected: toast with that detail; tools table empty; the header subtitle reads `Could not load this MCP server. It may have been deleted or you may not have access.` only if BOTH `getMcpServer` AND `discoverMcpTools` failed.

**FS-12: Auto-discover OAuth — empty server URL** — click Auto-discover with the URL field empty → expected: toast title `Enter the server URL first`; no sessionStorage write; no redirect.

**FS-13: Auto-discover OAuth — backend error** — `discoverMcpOAuth` throws → expected: sessionStorage key `mcp-form-oauth-draft` is removed; toast comes from `handleApiError` (server `detail` or default).

**FS-14: OAuth round-trip with corrupted draft** — manually set `sessionStorage['mcp-form-oauth-draft'] = '{not valid json'`, navigate to `/mcp/create?mcp_oauth=success&connection_id=conn-new` → expected: catch block runs; only `oauth_connection_id` is set on the form; no crash; sessionStorage cleared.

**FS-15: List — 401 unauthorized** — `POST /mcp-server/list` returns 401 `{"detail":"Could not validate credentials"}` → expected: no infinite spinner; empty state shown.

**FS-16: List — 422 validation** — returns `{"detail":[...]}` → expected: empty state, no crash.

**FS-17: Unauthenticated access** — no `tone_access_token` cookie → `/mcp` triggers `src/middleware.ts` redirect to `/auth/login?redirect=%2Fmcp`.

**FS-18: Reserved sub-route guard** — `/mcp/create/tools` and `/mcp/edit/tools` redirect to `/mcp` (no API call); `/mcp/[invalid-uuid]/tools` also redirects after `getMcpServer` returns 404 via the `useEffect` in `MCPToolsListPage`.

**FS-19: Validation toast for upsert — 422 missing fields** — returns:
```json
{"detail":[{"loc":["body","name"],"msg":"field required","type":"value_error.missing"}]}
```
Expected: `handleApiError` toast (detail is array, not string) — title is the default `Something went wrong. Please try again.`

**FS-20: Network failure** — `route.abort('failed')` on save → expected: toast with default `Something went wrong. Please try again.`; user stays on the form.

---

## Expected Toast Messages

Sonner toast titles + descriptions from `MCPListPage.tsx`, `MCPFormPage.tsx`, `MCPToolsListPage.tsx`, `src/utils/toast.tsx`, `src/utils/helpers.ts`.

| Trigger                                                    | Toast title                                          | Toast description                                                | Variant |
| ---------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------- | ------- |
| Create success                                              | `MCP server created successfully`                    | (none)                                                           | success |
| Update success                                              | `MCP server updated successfully`                    | (none)                                                           | success |
| Delete success                                              | `MCP server deleted successfully`                    | (none)                                                           | success |
| Save server form error (any API failure)                    | (server `detail` string OR `Something went wrong. Please try again.`) | (none)                                          | error   |
| Auto-discover OAuth — empty URL guard                       | `Enter the server URL first`                         | (none)                                                           | error   |
| Auto-discover OAuth — API throws                            | (server `detail` string OR `Something went wrong. Please try again.`) | (none)                                          | error   |
| Discover tools — failure                                    | (server `detail` string OR default)                  | (none)                                                           | error   |
| Get MCP server (load on tools page) — failure               | (server `detail` string OR default)                  | (none)                                                           | error   |
| List — failure                                              | (none — list silently empty)                         | (none)                                                           | —       |

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

### Example — `POST /mcp-server/list`

Request body:
```json
{"search": "sales", "is_active": true, "sort": "-updated_at", "page": 1, "page_size": 20}
```
Success (200):
```json
{
  "data": [
    {"id":"11111111-...","name":"sales-mcp","description":"Sales CRM tools","server_url":"https://sales-mcp.acme.com","transport_type":"streamable_http","auth_config":{"token":"sk-..."},"meta_data":{"timeout":30},"oauth_connection_id":null,"is_active":true,"created_at":"2026-05-27T10:00:00+00:00","updated_at":"2026-05-27T10:00:00+00:00"}
  ],
  "pagination": {"page":1,"page_size":20,"total":1,"total_pages":1}
}
```
Empty: `{"data": [], "pagination": {"page":1,"page_size":20,"total":0,"total_pages":0}}`. Error: `401 {"detail":"Could not validate credentials"}`.

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
Update request — same shape plus `"id":"<existing-uuid>"`.

Success (200):
```json
{"id":"11111111-...","name":"sales-mcp","description":"Sales CRM tools","server_url":"https://sales-mcp.acme.com/mcp","transport_type":"streamable_http","auth_config":{"bearer_token":"sk-..."},"meta_data":{"timeout":30,"http_headers":{"X-Custom":"abc"}},"oauth_connection_id":null,"is_active":true,"created_at":"2026-05-27T10:00:00+00:00","updated_at":"2026-05-27T10:00:00+00:00"}
```
Errors:
- `400 {"detail":"name is required when creating a new MCP server"}`
- `400 {"detail":"server_url is required when creating a new MCP server"}`
- `400 {"detail":"Invalid transport_type 'websocket'. Must be one of: sse, streamable_http"}`
- `400 {"detail":"Invalid server URL. Please check the URL and try again."}`
- `400 {"detail":"Authentication failed. Please check your token or API key and try again."}`
- `404 {"detail":"MCP server not found"}` (on update)
- `409 {"detail":"An MCP server with name 'sales-mcp' already exists in this organization"}`

### Example — `GET /mcp-server/get_mcp_server`

Success (200) returns the same `McpServer` shape as create. Error: `404 {"detail":"MCP server not found"}`.

### Example — `GET /mcp-server/discover_tools`

Success (200):
```json
{
  "server_name":"sales-mcp",
  "server_url":"https://sales-mcp.acme.com/mcp",
  "transport_type":"streamable_http",
  "tools":[
    {"name":"get_account","description":"Look up an account","parameters":{"type":"object","properties":{"id":{"type":"string"}}},"required":["id"]},
    {"name":"list_deals","description":"List open deals","parameters":{"type":"object","properties":{}},"required":[]}
  ],
  "tool_count":2
}
```
Errors: `400 {"detail":"Failed to connect to MCP server: connection refused"}` · `404 {"detail":"MCP server not found"}`.

### Example — `DELETE /mcp-server/delete_mcp_server`

Success (200): `{"message":"MCP server deleted successfully"}`. Error: `404 {"detail":"MCP server not found"}`.

### Example — `POST /mcp-server/validate_mcp_server`

Request body:
```json
{"server_url":"https://sales-mcp.acme.com/mcp","transport_type":"streamable_http","auth_config":{"token":"sk-..."}}
```
Success (200): `{"tools":[...],"tool_count":2}`. Errors: `400 {"detail":"server_url is required"}` · `400 {"detail":"Invalid server URL. Please check the URL and try again."}` · `400 {"detail":"Authentication failed. Please check your token or API key and try again."}`.

---

## Edge Cases

- [ ] Unauthenticated access → middleware redirect
- [ ] Favicon load failure → fallback to Server icon on sky-500 background
- [ ] Description missing → italic placeholder "No description provided."
- [ ] Reserved segments `create/tools` and `edit/tools` → redirect to `/mcp`
- [ ] Invalid `[id]` on `/mcp/[id]/tools` → redirect to `/mcp` in `useEffect`
- [ ] Discover tools call fails → error toast, table remains empty (no false "no tools" message)
- [ ] OAuth flow mid-form → `sessionStorage` key `mcp-form-oauth-draft` survives the round-trip
- [ ] Timeout slider value clamped to `[1, 60]` seconds
- [ ] Filtering with no matches vs. no servers at all → two distinct empty states with distinct CTAs
- [ ] Inactive server (`is_active=false`) → status pill reads "Paused"
- [ ] Headers builder: empty key or empty value rows are stripped on submit
- [ ] Long server URL → hostname is shown on the card; full URL appears in the form
- [ ] Bulk-delete partial failure — MCP currently has no bulk-delete UI (single-row delete only). If added in future, the partial-failure surfacing pattern should match the KB doc.
- [ ] Discovery polling — there is NO polling for `discover_tools`. It is only called on mount and on explicit "Refresh" click; assertion must check exactly 2 calls after one manual refresh.
- [ ] sessionStorage key collision — only `mcp-form-oauth-draft` is used. Other features must NOT write to this key. Verify by inspecting `sessionStorage.length` before and after an OAuth round-trip.
- [ ] Reserved URL segments — `/mcp/create/tools` and `/mcp/edit/tools` redirect to `/mcp`; `/mcp/[bad-id]/tools` redirects only AFTER `getMcpServer` returns 404 (allow up to one network round-trip in the assertion).
- [ ] Auto-discover OAuth — clicking with empty URL surfaces an inline toast; clicking with a malformed URL surfaces a backend toast (`Invalid server URL...`); the in-flight `discovering` state must clear in both branches.
- [ ] `is_active` flip timing — toggling the Active switch on the form is purely client-side; the badge on the card only updates after `POST upsert_mcp_server` returns 200 and the list refetches.
- [ ] Sequence guard on tools page — `fetchSeqRef.current` increments on every `loadTools` invocation; a late response from a previous request is dropped. Assertion: rapidly click "Refresh" twice and confirm only the final response renders.
- [ ] Header builder strip-on-save — rows with empty `key` are silently dropped at save time; verify a header with only a value field does NOT appear in the saved `meta_data.http_headers`.
- [ ] Pending OAuth connections — connections with `public_metadata.status === 'pending'` are filtered OUT of the dropdown; assertion: mock `getOAuthConnections` with one `pending` connection and verify it is not selectable.

---

## Business Rules

- Two transport types are supported: `streamable_http` and `sse`. The form enforces one or the other.
- Auth options are mutually compatible — a server can have headers + bearer + api-key + OAuth at the same time; backend chooses precedence at runtime.
- An `oauth_connection_id` on an MCP server cross-references `oauth_connections` (see `oauth-integrations.md`). Disconnecting that OAuth connection invalidates the MCP server's auth.
- Card hover styling (`-y-0.5`, brighter border, soft glow) is purely visual; cards remain clickable on focus.
- The frontend never sees the discovered tools schema until `discover_tools` is explicitly called — there is no auto-discovery on list view.

---

## Accessibility Requirements

- [ ] All card actions are keyboard reachable; the card itself is a real `<a>` link to the tools view
- [ ] Action menu trigger has an accessible label (e.g. `aria-label="Server actions"`)
- [ ] Slider exposes value as text (e.g. "Timeout: 20 seconds") for screen readers
- [ ] Switches (Active / Bearer / API key) have visible labels and announce state
- [ ] Status pill includes text ("Live" / "Paused"), not just color
- [ ] Modals/forms trap focus and restore it on close/cancel (Radix/shadcn default)
- [ ] Search inputs have associated labels

---

## Appended Scenarios (gap-fill, ID prefix `MCP-`)

These rows extend the PS/FS coverage with auth/error-state/network/a11y/list-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `mcp.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-001 | Visit `/mcp` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fmcp` | `unauthenticated visit redirects to login` |
| MCP-002 | Visit `/mcp/create` without auth | Middleware 307 → `/auth/login?redirect=%2Fmcp%2Fcreate` | `unauthenticated create page redirects to login` |
| MCP-003 | Visit `/mcp/edit/<id>` without auth | Middleware 307 → `/auth/login?redirect=%2Fmcp%2Fedit%2F<id>` | `unauthenticated edit deep link redirects to login` |
| MCP-004 | Visit `/mcp/<id>/tools` without auth | Middleware 307 → `/auth/login?redirect=%2Fmcp%2F<id>%2Ftools` | `unauthenticated tools deep link redirects to login` |
| MCP-005 | Visit `/mcp` with an expired token | Middleware 307 → `/auth/login?redirect=%2Fmcp`; expired cookie cleared | `expired token redirects to login and clears cookie` |
| MCP-006 | Member role attempts delete from action menu | Backend 403; toast `Admin or Owner role required`; card remains | `member role delete surfaces forbidden toast` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-007 | `POST /mcp-server/list` returns 400 (malformed filter) | Empty grid state; no toast spam (list silently empty); no crash | `list 400 renders empty grid without spam` |
| MCP-008 | Token expires between page load and save → 401 on upsert | Toast `Invalid token` / `Could not validate credentials`; form stays open with state preserved | `save 401 surfaces error toast without redirect` |
| MCP-009 | Delete a server already removed → 404 | Toast `MCP server not found`; refetch removes the card | `delete 404 surfaces not-found toast` |
| MCP-010 | Upsert duplicate name → 409 | Toast `An MCP server with name '<name>' already exists in this organization`; form stays open | `upsert 409 surfaces duplicate-name toast` |
| MCP-011 | Upsert 500 server error | Toast `Internal Server Error` OR default; form stays open with state intact | `upsert 500 surfaces server error toast` |
| MCP-012 | Discover tools — 401 mid-flow | Toast surfaces detail; tools table empty | `discover tools 401 surfaces error toast` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-013 | Offline / network failure during Save | Toast `Something went wrong. Please try again.`; form stays open with state intact | `save network failure preserves form data` |
| MCP-014 | Slow `POST /mcp-server/upsert_mcp_server` (>3s) | Save button disabled with "Saving…" / "Updating…" label the whole time | `slow save disables button with saving label` |
| MCP-015 | Slow `GET /mcp-server/get_mcp_server` on edit hydrate (>3s) | Form fields blank until hydrated; Save remains disabled until hydration completes | `slow edit hydration keeps save disabled` |
| MCP-016 | Concurrent edit — same server updated by another user mid-form | Save submits last-write-wins OR backend returns 409; toast reflects backend response | `concurrent edit handled by last-write or 409` |
| MCP-017 | Double-click Save during a pending request | Only one upsert fires; second click ignored while `saving` is true | `double-click on save does not double-submit` |
| MCP-018 | Rapid Refresh clicks on tools page | `fetchSeqRef` increments; only the final response renders; no flicker | `rapid refresh tools resolves to the latest response` |

### Input edge cases (MCP form)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-019 | Whitespace-only Server Name | RHF inline error `Server name is required`; no network call | `whitespace-only server name is rejected` |
| MCP-020 | Whitespace-only Server URL | RHF inline error `Server URL is required`; no network call | `whitespace-only server url is rejected` |
| MCP-021 | Server URL with leading/trailing whitespace | Trimmed before submit; payload contains the clean URL | `server url trims surrounding whitespace before submit` |
| MCP-022 | Special chars + emoji + unicode in Server Name (`__e2e__ 🚀 <script>`) | Accepted; round-trips into list card; no XSS execution in name display | `server name accepts unicode and html-ish input without xss` |
| MCP-023 | Server Name > 500 characters | Either accepted or backend 400/422; form stays open; toast surfaces detail | `very long server name handled with backend validation` |
| MCP-024 | Server URL malformed (`not-a-url`) | Backend 400 `Invalid server URL. Please check the URL and try again.`; toast surfaces detail | `malformed server url surfaces invalid url toast` |
| MCP-025 | Server URL unreachable (`https://localhost:9`) | Discover-tools 400 `Failed to connect to MCP server: connection refused`; toast surfaces detail | `unreachable server url surfaces connection error` |
| MCP-026 | HTTP Headers — empty key row | Stripped silently at save time; saved `meta_data.http_headers` excludes it | `empty header key rows are stripped on save` |
| MCP-027 | HTTP Headers — whitespace key + value | Trimmed before submit; empty-after-trim rows dropped | `header rows trim whitespace and drop empties` |
| MCP-028 | Description > 1000 characters | `maxLength` blocks; counter shows `1000/1000`; submit truncates at 1000 | `description maxLength enforced by counter` |
| MCP-029 | Timeout slider out-of-range value via DevTools mutation | Backend 400 clamps to [1, 60]; toast surfaces detail | `out-of-range timeout surfaces backend validation` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-030 | Empty list — no servers, no filters | `MCPEmptyState` rendered with "Create MCP Server" CTA; toolbar hidden | `empty list renders the no-servers empty state` |
| MCP-031 | Empty list under active filters | "No MCP servers match your filters" + "Clear filters" link | `filtered list with no matches renders no-results state` |
| MCP-032 | Pagination — first page | Prev disabled (or no pagination control if all fit) | `pagination disables prev on the first page` |
| MCP-033 | Pagination — last page | Next disabled, Prev enabled | `pagination disables next on the last page` |
| MCP-034 | Sort by Newest / Oldest | `POST /mcp-server/list` fires with `sort: '-created_at'` or `sort: 'created_at'` | `sort by date orders rows appropriately` |
| MCP-035 | Sort by Name A–Z / Z–A | `POST /mcp-server/list` fires with `sort_by: 'name'` asc/desc | `sort by name cycles asc and desc` |
| MCP-036 | Sort by Recently updated | `POST /mcp-server/list` fires with `sort: '-updated_at'` | `sort by recently updated orders descending` |
| MCP-037 | Token search with whitespace-only value | Sent as empty; list reverts to default | `whitespace-only search treated as empty` |
| MCP-038 | "Clear filters" link | Resets all toolbar filters and refetches | `clear filters resets state` |
| MCP-039 | Dashed "+ New MCP Server" card always appears at end | Even with one server, the dashed card is the final tile in the grid | `dashed new server card appears as final tile` |

### MCP-server-specific

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-040 | Validate-connection (auto-discover) success | Auto-discover triggers `validate_mcp_server` OR `discoverMcpOAuth`; success shown in UI | `validate connection success reflected in ui` |
| MCP-041 | Validate-connection failure with malformed URL | Backend 400 `Invalid server URL`; toast surfaces detail; `discovering` state clears | `validate connection failure clears discovering state` |
| MCP-042 | Validate-connection with empty URL | Inline toast `Enter the server URL first`; no network call; no sessionStorage write | `validate with empty url surfaces inline toast` |
| MCP-043 | Refresh tools button on detail page | Calls `GET /mcp-server/discover_tools`; table refreshed | `refresh tools button re-fetches tool list` |
| MCP-044 | Tool list refreshed after server change | Edit server URL → Save → revisit `/mcp/<id>/tools` → assert `discover_tools` re-fires | `tool list refreshes after server change` |
| MCP-045 | Attach MCP server to an agent | `POST /mcp-server/attach_mcp_server_to_agents` with agent_ids + selected_tools; agent's tools list updates | `attach to agent updates agent tools list` |
| MCP-046 | Detach MCP server from an agent | `DELETE /mcp-server/detach_mcp_server_from_agents` with agent_ids; agent's tools list removes them | `detach from agent removes tools from agent` |
| MCP-047 | OAuth round-trip with sessionStorage draft | Draft written, query params stripped on return, draft cleared after save | `oauth round trip restores form and clears draft` |
| MCP-048 | OAuth round-trip with corrupted draft | Catch block runs; only `oauth_connection_id` set; no crash; sessionStorage cleared | `corrupted draft handled without crash` |
| MCP-049 | Pending OAuth connections filtered out of dropdown | Connections with `public_metadata.status === 'pending'` not selectable | `pending oauth connections not selectable` |
| MCP-050 | Reserved sub-route guard | `/mcp/create/tools` and `/mcp/edit/tools` redirect to `/mcp`; no API call fires | `reserved sub-routes redirect to mcp list` |
| MCP-051 | Invalid `[id]` on tools page redirects after 404 | `getMcpServer` 404 → `useEffect` redirects to `/mcp` | `invalid tools deep link redirects to list after 404` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-052 | Tab order through the form | Name → Description → Active toggle → Server URL → Transport radio → Timeout → Headers → Auth toggles → OAuth select → Cancel → Save | `tab order through mcp form reaches every control` |
| MCP-053 | Submit form via Enter in Server Name | Triggers Save when valid | `Enter in server name submits the form when valid` |
| MCP-054 | Modal-like form retains focus when error toast appears | Focus stays on Save button; toast announced via aria-live | `error toast does not steal focus from form` |
| MCP-055 | Action menu trigger has accessible name (`aria-label="Server actions"`) | Screen readers announce the menu trigger | `action menu trigger exposes accessible name` |
| MCP-056 | Status pill includes text ("Live" / "Paused"), not only color | Accessible readers announce the active/paused state | `status pill exposes readable text` |
| MCP-057 | Switches announce their state | Active / Bearer / API key switches expose `aria-checked` and visible labels | `switches expose accessible state` |
| MCP-058 | Slider exposes value as text ("Timeout: 20 seconds") | Screen readers announce the value on focus | `timeout slider exposes value to screen readers` |
| MCP-059 | Search input has associated label or aria-label | Token search input accessible name available | `search input has accessible name` |
| MCP-060 | Card itself is a real `<a>` link to the tools view | Tab focuses card; Enter activates navigation | `card link is keyboard activatable` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-061 | Cancel on create returns to `/mcp` | URL changes to `/mcp`; form state discarded | `cancel on create returns to list` |
| MCP-062 | Browser back from edit page | Returns to `/mcp` with list state preserved | `browser back from edit returns to list` |
| MCP-063 | Reload `/mcp/edit/<id>` | Re-fetches the server and re-hydrates the form | `reload on edit page rehydrates the form` |
| MCP-064 | Back arrow on tools page returns to `/mcp` | URL changes; list state preserved | `back arrow on tools page returns to list` |
| MCP-065 | Cross-link from tools page to attached agents | If supported, clicking an attached agent navigates to the agent edit page | `cross-link to attached agent navigates correctly` |

### Full lifecycle (`MCP-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MCP-FULL | Authenticate via `loginViaUI` → visit `/mcp` → assert headings + Create CTA + dashed card → click Create MCP Server → fill Server Name `__e2e__ clickup_mcp`, Server URL `https://api.clickup.com/mcp`, leave Streamable HTTP default + timeout 20 → click Save → assert toast `MCP server created successfully` and redirect to `/mcp` → assert new card visible → click card → assert `/mcp/<id>/tools` route, header + transport badge + status badge → click Refresh tools → assert `discover_tools` re-fires → click back arrow → action menu → Edit → change description to `__e2e__ updated` → Save → assert toast `MCP server updated successfully` and redirect to `/mcp` → seed an `__e2e__` agent via API → attach the MCP server to the agent via API → revisit the agent's tools tab → assert tools list now includes the MCP tools → detach via API → assert tools removed → return to `/mcp` → action menu → Delete → assert toast `MCP server deleted successfully` and card removed → cleanup any residual data (agent, MCP server) via API in the same `try/finally` block | All endpoints fire with expected payloads; attach/detach round-trips reflect in the agent; cleanup runs in the same test body even if assertions fail | `walks create validate attach detach delete of an mcp server end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| MCP-001..006 | FS-17 (auth gating) | Adds per-route + expired-token + member-delete cases |
| MCP-007..012 | FS-3..FS-11 | Standardises 400/401/403/404/409/500 paths across endpoints |
| MCP-013..018 | (new) | Network resilience + concurrent + double-submit + rapid refresh |
| MCP-019..029 | FS-1, FS-2, FS-4..FS-6 | Adds whitespace, special-char, length, URL-format, headers edge cases |
| MCP-030..039 | PS-2, PS-3 | Promotes pagination/sort/empty-state/dashed card to scenarios |
| MCP-040..051 | PS-6..PS-9, FS-10..FS-18 | Promotes MCP-specific validate/discover/attach/detach/OAuth/reserved to scenarios |
| MCP-052..060 | Accessibility section | Promotes a11y bullets to scenarios |
| MCP-061..065 | Navigation table | Adds reload + back/forward + cross-feature links |
| MCP-FULL | (new) | Single-test sweep of create → validate → attach → delete |
